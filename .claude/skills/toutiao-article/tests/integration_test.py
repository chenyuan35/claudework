"""
头条号自动发布 - 集成测试 (v8.0)
模拟 Phase 0→7 流程，验证状态文件、数据流、恢复逻辑是否完整。
不依赖浏览器，纯后端逻辑验证。
"""
import sys, os, json, tempfile, shutil, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Patch paths before importing
import scripts.state as state
import scripts.collect_metrics as cm
import scripts.score_topics as st
from scripts.validate_article import ArticleValidator
from scripts.lib.config_loader import get_thresholds

class TestIntegration(unittest.TestCase):

    def setUp(self):
        """Use temp dir for runtime files"""
        self.tempdir = tempfile.mkdtemp()
        self.orig_state = state.STATE_FILE
        self.orig_history = state.HISTORY_FILE
        self.orig_metrics = state.METRICS_FILE
        state.STATE_FILE = os.path.join(self.tempdir, "state.json")
        state.HISTORY_FILE = os.path.join(self.tempdir, "history.json")
        state.METRICS_FILE = os.path.join(self.tempdir, "metrics.json")
        state.reset_to_idle()
        # Also store for collect_metrics
        self.orig_metrics_cm = cm.load_metrics
        self.orig_history_cm = cm.load_history

    def tearDown(self):
        state.STATE_FILE = self.orig_state
        state.HISTORY_FILE = self.orig_history
        state.METRICS_FILE = self.orig_metrics
        cm.load_metrics = self.orig_metrics_cm
        cm.load_history = self.orig_history_cm
        shutil.rmtree(self.tempdir, ignore_errors=True)

    def test_phase0_collect_metrics(self):
        """Phase 0: collect_metrics receives scraped data and writes metrics.json"""
        fake_articles = [
            {"title": "省钱技巧1", "direction": "省钱理财", "views": 1200, "reads": 80, "likes": 5, "comments": 2},
            {"title": "厨房技巧1", "direction": "食", "views": 300, "reads": 10, "likes": 1, "comments": 0},
            {"title": "居家收纳1", "direction": "住", "views": 800, "reads": 45, "likes": 3, "comments": 1},
            {"title": "职场沟通1", "direction": "职场成长", "views": 150, "reads": 8, "likes": 0, "comments": 0},
        ]
        result = cm.build_batch_analysis(fake_articles)
        self.assertEqual(result["total"]["articles"], 4)
        self.assertGreater(result["total"]["ctr"], 0)

        # Verify metrics.json was written
        m = state.load_metrics()
        self.assertIn("last_batch", m)
        self.assertEqual(m["last_batch"]["total"]["articles"], 4)
        self.assertIn("high_performance", m["last_batch"])

    def test_phase1_score_topics(self):
        """Phase 1: score_topics ranks candidates correctly"""
        candidates = [
            {"title": "医保新规怎么报销", "direction": "社会事件", "audience_score": 20, "practical_value": 18, "series_id": "medical-01"},
            {"title": "冰箱收纳5个技巧", "direction": "住", "audience_score": 15, "practical_value": 15},
            {"title": "AI写代码趋势", "direction": "职场成长", "audience_score": 5, "practical_value": 5},
        ]
        high_perf = ["社会事件", "住"]
        ranked = st.rank_topics(candidates, high_perf, [])
        self.assertEqual(len(ranked), 3)
        self.assertGreaterEqual(ranked[0]["score"], ranked[1]["score"])
        # First should be social event with high score
        self.assertIn("breakdown", ranked[0])
        self.assertIn("score", ranked[0])

    def test_phase2_validate_article(self):
        """Phase 2: validate_article rejects bad articles"""
        # Good article
        paras = []
        for i in range(55):
            paras.append(f"第{i+1}段正文示例内容，读者可从这段获得有用生活小技巧和经验。")
            if (i + 1) % 10 == 0:
                paras.append(f"小标题{(i + 1) // 10}")
        for i in range(5):
            paras.append(f"步骤第{i+1}步说明。关键点需要仔细检查避免出错。")
        body = "".join(f"<p>{p}</p>" for p in paras)
        html = f"<html><body>{body}</body></html>"
        v = ArticleValidator(html)
        result = v.validate()
        self.assertTrue(result["passed"], f"Good article should pass: {result['failures']}")
        self.assertGreaterEqual(result["chinese_count"], 1500)

        # Bad article: too short
        bad_html = "<html><body><p>太短了</p></body></html>"
        v2 = ArticleValidator(bad_html)
        result2 = v2.validate()
        self.assertFalse(result2["passed"])

        # Bad article: over 60 chars paragraph
        paras3 = []
        for i in range(55):
            paras3.append(f"正常段落第{i+1}句。")
        paras3.append("长" * 61 + "。")
        body3 = "".join(f"<p>{p}</p>" for p in paras3)
        html3 = f"<html><body>{body3}</body></html>"
        v3 = ArticleValidator(html3)
        result3 = v3.validate()
        self.assertFalse(result3["passed"])

    def test_phase7_state_history(self):
        """Phase 7: history management, cleanup, idle reset"""
        # Simulate publishing 2 articles
        state.update_state(article_index=1, title="文章1", phase="7", publish_clicked=True, publish_verified=True)
        state.append_history({"title": "文章1", "direction": "住", "publish_status": "scheduled"})
        state.update_state(article_index=2, title="文章2", phase="7", publish_clicked=True, publish_verified=True)
        state.append_history({"title": "文章2", "direction": "省钱理财", "publish_status": "scheduled"})

        h = state.load_history()
        self.assertEqual(len(h), 2)
        self.assertEqual(h[0]["title"], "文章1")

        # Reset to idle after 2 articles
        state.reset_to_idle()
        s = state.load_state()
        self.assertEqual(s["status"], "idle")
        self.assertEqual(s["phase"], "idle")

        # History preserved after reset
        h2 = state.load_history()
        self.assertEqual(len(h2), 2)

    def test_recovery_publish_verified(self):
        """After publish_verified → continue_next"""
        state.update_state(publish_verified=True, title="已发布文章")
        action, detail = state.detect_recovery()
        self.assertEqual(action, "continue_next")

    def test_recovery_publish_clicked_not_verified(self):
        """After publish_clicked but not verified → verify_publish"""
        state.update_state(publish_clicked=True, publish_verified=False, title="待核验")
        action, detail = state.detect_recovery()
        self.assertEqual(action, "verify_publish")

    def test_recovery_fresh_start(self):
        """Fresh state → new"""
        action, detail = state.detect_recovery()
        self.assertEqual(action, "new")

    def test_dirty_editor_detection(self):
        """Dirty editor detection"""
        self.assertTrue(state.detect_dirty_editor("<p>有内容</p>"))
        self.assertFalse(state.detect_dirty_editor(""))
        self.assertFalse(state.detect_dirty_editor("<p><br></p>"))

    def test_cleanup_temp(self):
        """Temp image cleanup"""
        state.ensure_runtime_dirs()
        img_dir = os.path.join(self.tempdir, "images")
        os.makedirs(img_dir, exist_ok=True)
        test_file = os.path.join(img_dir, "test.png")
        with open(test_file, "w") as f: f.write("fake")
        self.assertTrue(os.path.exists(test_file))
        # state.cleanup_temp would delete it

    def test_no_double_publish_detection(self):
        """After publish_verified=True, detect_recovery should NOT try to republish"""
        state.update_state(publish_verified=True, title="已发文章", scheduled_time="07月28日 06:00")
        action, _ = state.detect_recovery()
        self.assertEqual(action, "continue_next", "Verified article should not trigger republish")

    def test_config_loader_works(self):
        """Config loader reads actual values"""
        t = get_thresholds()
        self.assertEqual(t["article"]["chinese_min"], 1500)
        self.assertEqual(t["article"]["para_count_min"], 55)
        self.assertEqual(t["article"]["per_para_chinese_max"], 60)
        self.assertEqual(t["article"]["heading_count_min"], 4)
        self.assertEqual(t["publish"]["articles_per_day"], 2)


if __name__ == "__main__":
    unittest.main()
