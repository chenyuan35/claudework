"""头条号 v8 主管道接线回归测试。"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import scripts.run_pipeline as pipeline
import scripts.state as state
from scripts.score_topics import score_topic


class TestPipelineWiring(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        self.originals = {
            "state": state.STATE_FILE,
            "history": state.HISTORY_FILE,
            "metrics": state.METRICS_FILE,
            "images": state.TEMP_IMAGES_DIR,
            "pipeline_base": pipeline.BASE,
            "article_context": pipeline.ARTICLE_CONTEXT_FILE,
        }
        state.STATE_FILE = os.path.join(self.tempdir, "runtime", "state.json")
        state.HISTORY_FILE = os.path.join(self.tempdir, "runtime", "history.json")
        state.METRICS_FILE = os.path.join(self.tempdir, "runtime", "metrics.json")
        state.TEMP_IMAGES_DIR = os.path.join(self.tempdir, "runtime", "images")
        pipeline.BASE = self.tempdir
        pipeline.ARTICLE_CONTEXT_FILE = os.path.join(self.tempdir, "runtime", "_article_context.json")
        state.reset_to_idle()

    def tearDown(self):
        state.STATE_FILE = self.originals["state"]
        state.HISTORY_FILE = self.originals["history"]
        state.METRICS_FILE = self.originals["metrics"]
        state.TEMP_IMAGES_DIR = self.originals["images"]
        pipeline.BASE = self.originals["pipeline_base"]
        pipeline.ARTICLE_CONTEXT_FILE = self.originals["article_context"]
        shutil.rmtree(self.tempdir, ignore_errors=True)

    def assert_javascript_parses(self, code_file):
        with open(code_file, "r", encoding="utf-8") as f:
            code = f.read()
        result = subprocess.run(
            ["node", "--check"], input=code, text=True,
            capture_output=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_phase3_embeds_real_html_and_title(self):
        html = "<p>真实正文内容。</p>"
        title = "真实标题"
        result = pipeline.phase3_writer({"html": html, "title": title})
        self.assertEqual(result["action"], "browser_write")
        with open(result["code_file"], "r", encoding="utf-8") as f:
            code = f.read()
        self.assertIn(html, code)
        self.assertIn(title, code)
        self.assertNotIn("替换为正文HTML", code)
        self.assertIn("EDITOR_LOCAL_DIFF", code)
        self.assertIn("localChinese", code)
        self.assert_javascript_parses(result["code_file"])
        with open(os.path.join(self.tempdir, "runtime", "_browser_task.json"), "r", encoding="utf-8") as f:
            task = json.load(f)
        self.assertEqual(task["action"], "browser_write")

    @patch("scripts.run_pipeline.article_dir")
    @patch("scripts.run_pipeline.generate_one_image")
    def test_phase4_uses_saved_context_and_generates_validation(self, generate_one, article_dir):
        img_dir = os.path.join(self.tempdir, "runtime", "images", "abc")
        os.makedirs(img_dir, exist_ok=True)
        article_dir.return_value = img_dir
        generated = []
        for i in range(1, 4):
            path = os.path.join(img_dir, f"article_img{i}.png")
            with open(path, "wb") as f:
                f.write(b"test-image-file")
            generated.append({"ok": True, "path": path})
        generate_one.side_effect = generated
        pipeline._save_article_context({
            "title": "文章标题",
            "html": "<h2>小标题</h2><p>正文场景内容。</p>" * 12,
        }, replace=True)
        result = pipeline.phase4_images()
        self.assertTrue(result["all_ok"])
        self.assertEqual(generate_one.call_count, 3)
        with open(result["code_file"], "r", encoding="utf-8") as f:
            code = f.read()
        self.assertIn("paragraphIntegrityOk", code)
        self.assertIn("restoreValidatedBody", code)
        self.assertIn("NO_SAFE_SENTENCE_ANCHOR", code)
        self.assertIn("browser_run_code_unsafe_only", json.dumps(result))
        self.assert_javascript_parses(result["code_file"])

    def test_phase5_and_phase6_generated_code_parses(self):
        pipeline._save_article_context({"title": "真实标题"}, replace=True)
        state.update_state(title="真实标题", scheduled_time="2026-07-27 06:00")
        phase5 = pipeline._generate_phase5_code("07月27日", "6", "真实标题")
        phase6 = pipeline.phase6_verify()["code_file"]
        self.assert_javascript_parses(phase5)
        self.assert_javascript_parses(phase6)

    def test_phase7_increments_once_and_resets_after_two(self):
        for index in (1, 2):
            title = f"文章{index}"
            pipeline._save_article_context({
                "title": title,
                "direction": "住",
                "series_id": "series",
                "hook_id": index,
                "scheduled_time": f"2026-07-27 {index * 6:02d}:00",
                "article_hash": f"hash{index}",
            }, replace=True)
            state.update_state(publish_verified=True, title=title,
                               scheduled_time=f"2026-07-27 {index * 6:02d}:00",
                               article_hash=f"hash{index}")
            result = pipeline.phase7_cleanup({})
            self.assertEqual(result["article_index"], index)
        self.assertEqual(result["action"], "daily_done")
        self.assertEqual(state.load_state()["article_index"], 0)
        self.assertEqual(len(state.load_history()), 2)

    def test_phase7_is_idempotent(self):
        pipeline._save_article_context({
            "title": "同一文章", "scheduled_time": "2026-07-27 06:00",
            "article_hash": "samehash",
        }, replace=True)
        state.update_state(publish_verified=True, title="同一文章",
                           scheduled_time="2026-07-27 06:00", article_hash="samehash")
        first = pipeline.phase7_cleanup({})
        self.assertEqual(first["article_index"], 1)
        pipeline._save_article_context({
            "title": "同一文章", "scheduled_time": "2026-07-27 06:00",
            "article_hash": "samehash",
        }, replace=True)
        state.update_state(publish_verified=True, title="同一文章",
                           scheduled_time="2026-07-27 06:00", article_hash="samehash")
        second = pipeline.phase7_cleanup({})
        self.assertEqual(second["action"], "already_recorded")
        self.assertEqual(len(state.load_history()), 1)
        self.assertEqual(state.load_metrics()["articles_total"], 1)

    def test_phase7_recovers_after_history_only_commit(self):
        state.append_history({
            "title": "崩溃文章", "scheduled_time": "2026-07-27 06:00",
            "article_hash": "crashhash", "operation_key": "crashhash",
            "article_index_after": 1,
        })
        pipeline._save_article_context({
            "title": "崩溃文章", "scheduled_time": "2026-07-27 06:00",
            "article_hash": "crashhash",
        }, replace=True)
        state.update_state(publish_verified=True, title="崩溃文章",
                           article_hash="crashhash", article_index=0)
        result = pipeline.phase7_cleanup({})
        self.assertEqual(result["article_index"], 1)
        self.assertEqual(state.load_metrics()["articles_total"], 1)
        self.assertEqual(len(state.load_history()), 1)

    def test_schedule_scans_past_fully_occupied_days(self):
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        day_after = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")
        third_day = datetime.now() + timedelta(days=3)
        for day in (tomorrow, day_after):
            for slot in ("06:00", "18:00"):
                state.append_history({"title": f"{day}-{slot}", "scheduled_time": f"{day} {slot}"})
        day_str, hour, iso_date = pipeline._allocate_schedule()
        self.assertEqual(iso_date, third_day.strftime("%Y-%m-%d"))
        self.assertEqual(hour, "6")
        self.assertEqual(day_str, third_day.strftime("%m月%d日"))

    def test_hook_dedup_excludes_last_hook(self):
        state.append_history({"title": "上一篇", "hook_id": 2})
        candidates = [
            {"title": "重复钩子", "hook_id": 2, "direction": "住", "audience_score": 25,
             "practical_value": 20, "series_id": "s", "timeliness_score": 10, "source_score": 5},
            {"title": "新钩子", "hook_id": 3, "direction": "住", "audience_score": 25,
             "practical_value": 20, "series_id": "s", "timeliness_score": 10, "source_score": 5},
        ]
        result = pipeline.phase1_score({"candidates": candidates})
        self.assertEqual([item["title"] for item in result["ranked"]], ["新钩子"])
        self.assertEqual(result["excluded_hook_id"], 2)

    def test_hot_bonus_requires_account_direction(self):
        base = {"audience_score": 10, "practical_value": 10,
                "timeliness_score": 5, "source_score": 3, "hot_score": 100,
                "hot_age_days": 1}
        aligned = score_topic({**base, "direction": "住"}, [], [])
        unrelated = score_topic({**base, "direction": "娱乐八卦"}, [], [])
        no_freshness = score_topic({**base, "direction": "住", "hot_age_days": None}, [], [])
        self.assertGreater(aligned["breakdown"]["account_aligned_hot_bonus"], 0)
        self.assertEqual(unrelated["breakdown"]["account_aligned_hot_bonus"], 0)
        self.assertEqual(no_freshness["breakdown"]["account_aligned_hot_bonus"], 0)


if __name__ == "__main__":
    unittest.main()
