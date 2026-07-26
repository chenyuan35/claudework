from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "run_baijiahao_publish.py"
SPEC = importlib.util.spec_from_file_location("run_baijiahao_publish", SCRIPT_PATH)
PIPELINE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = PIPELINE
SPEC.loader.exec_module(PIPELINE)


class PipelineTests(unittest.TestCase):
    def test_stage_order_is_fixed(self) -> None:
        names = [stage.name for stage in PIPELINE.stages(Path("inject.js"), "测试标题")]
        self.assertEqual(
            names,
            [
                # 运营前段（reasoning）
                "check_dashboard",
                "find_trending",
                "select_topic",
                "write_article",
                # Python 自动
                "validate_article",
                "generate_inject",
                # 浏览器发布
                "prepare_home",
                "open_editor",
                "inject_content",
                "insert_images",
                "set_cover",
                "publish_gate",
                "schedule_publish",
                "verify_submission",
            ],
        )

    def test_browser_stages_use_playwright_tools(self) -> None:
        pipeline = PIPELINE.stages(Path("inject.js"), "测试标题")
        for stage in pipeline:
            if stage.type != "browser":
                continue
            for operation in stage.operations:
                self.assertTrue(operation["tool"].startswith("mcp__playwright__browser_"))

    def test_reasoning_stages_have_prompt(self) -> None:
        pipeline = PIPELINE.stages(Path("inject.js"), "测试标题")
        for stage in pipeline:
            if stage.type != "reasoning":
                continue
            self.assertTrue(stage.reasoning_prompt)

    def test_python_stages_have_empty_expected_status(self) -> None:
        pipeline = PIPELINE.stages(Path("inject.js"), "测试标题")
        for stage in pipeline:
            if stage.type != "python":
                continue
            self.assertEqual(stage.expected_status, "")

    def test_complete_rejects_out_of_order_stage(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            article = root / "article.html"
            article.write_text("test", encoding="utf-8")
            state_file = root / "pipeline_state.json"
            task_file = root / "_task.json"
            task_file.write_text(
                json.dumps({
                    "stage": "check_dashboard",
                    "expectedStatus": "dashboard_read",
                    "taskToken": "aaaabbbbccccddddeeeeffff00001111",
                }),
                encoding="utf-8",
            )
            state = {
                "status": "waiting_external",
                "stageIndex": 0,
                "stage": "check_dashboard",
                "article": str(article),
                "articleSha256": __import__("hashlib").sha256(article.read_bytes()).hexdigest(),
                "injectFile": str(root / "inject.js"),
                "title": "测试标题",
                "results": {},
                "failures": {},
            }
            state_file.write_text(json.dumps(state), encoding="utf-8")
            result_file = root / "result.json"
            result_file.write_text(
                json.dumps({"status": "trending_found"}),
                encoding="utf-8",
            )
            with (
                patch.object(PIPELINE, "STATE_FILE", state_file),
                patch.object(PIPELINE, "TASK_FILE", task_file),
            ):
                with self.assertRaisesRegex(RuntimeError, "BJH_STAGE_ORDER_ERROR"):
                    PIPELINE.complete("find_trending", result_file)

    def test_gate_result_must_pass(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "gate_not_passed"):
            PIPELINE.normalize_result(
                "publish_gate", "publish_gate_passed", {"pass": False},
            )

    def test_emit_task_completes_at_end(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state_file = root / "pipeline_state.json"
            task_file = root / "_task.json"
            state = {
                "status": "prepared",
                "stageIndex": 14,
                "stage": "verify_submission",
                "injectFile": str(root / "inject.js"),
                "title": "测试标题",
                "failures": {},
            }
            with (
                patch.object(PIPELINE, "STATE_FILE", state_file),
                patch.object(PIPELINE, "TASK_FILE", task_file),
            ):
                output = PIPELINE.emit_task(state)
            self.assertEqual(output["status"], "completed")
            self.assertFalse(task_file.exists())

    def test_emit_task_creates_reasoning_task(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state_file = root / "pipeline_state.json"
            task_file = root / "_task.json"
            state = {
                "status": "prepared",
                "stageIndex": 0,
                "injectFile": str(root / "inject.js"),
                "title": "",
                "failures": {},
                "results": {},
            }
            with (
                patch.object(PIPELINE, "STATE_FILE", state_file),
                patch.object(PIPELINE, "TASK_FILE", task_file),
            ):
                output = PIPELINE.emit_task(state)
            self.assertEqual(output["status"], "waiting_external")
            self.assertEqual(output["type"], "reasoning")
            self.assertTrue(task_file.exists())
            task = json.loads(task_file.read_text(encoding="utf-8"))
            self.assertEqual(task["type"], "reasoning")
            self.assertEqual(task["stage"], "check_dashboard")
            self.assertIn("prompt", task)
            self.assertIn("taskToken", task)
            self.assertEqual(len(task["taskToken"]), 32)

    def test_emit_task_creates_browser_task(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state_file = root / "pipeline_state.json"
            task_file = root / "_task.json"
            state = {
                "status": "prepared",
                "stageIndex": 6,
                "stage": "prepare_home",
                "injectFile": str(root / "inject.js"),
                "title": "测试标题",
                "failures": {},
                "results": {},
            }
            with (
                patch.object(PIPELINE, "STATE_FILE", state_file),
                patch.object(PIPELINE, "TASK_FILE", task_file),
            ):
                output = PIPELINE.emit_task(state)
            self.assertEqual(output["status"], "waiting_external")
            self.assertEqual(output["type"], "browser")
            task = json.loads(task_file.read_text(encoding="utf-8"))
            self.assertEqual(task["type"], "browser")
            self.assertIn("taskToken", task)
            self.assertEqual(len(task["taskToken"]), 32)
            self.assertTrue(task.get("operations"))

    def test_complete_verifies_task_token(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            article = root / "article.html"
            article.write_text("test", encoding="utf-8")
            state_file = root / "pipeline_state.json"
            task_file = root / "_task.json"
            state = {
                "status": "waiting_external",
                "stageIndex": 0,
                "stage": "check_dashboard",
                "article": str(article),
                "articleSha256": __import__("hashlib").sha256(article.read_bytes()).hexdigest(),
                "injectFile": str(root / "inject.js"),
                "title": "测试标题",
                "results": {},
                "failures": {},
            }
            state_file.write_text(json.dumps(state), encoding="utf-8")
            task_content = {
                "stage": "check_dashboard",
                "type": "reasoning",
                "expectedStatus": "dashboard_read",
                "taskToken": "0123456789abcdef0123456789abcdef",
            }
            task_file.write_text(json.dumps(task_content), encoding="utf-8")
            result_file = root / "result.json"
            result_file.write_text(
                json.dumps({"status": "dashboard_read", "taskToken": "wrong_token"}),
                encoding="utf-8",
            )
            with (
                patch.object(PIPELINE, "STATE_FILE", state_file),
                patch.object(PIPELINE, "TASK_FILE", task_file),
            ):
                with self.assertRaisesRegex(RuntimeError, "taskToken_mismatch"):
                    PIPELINE.complete("check_dashboard", result_file)

    def test_fail_counts_attempts_and_hard_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state_file = root / "pipeline_state.json"
            task_file = root / "_task.json"
            state = {
                "status": "waiting_external",
                "stageIndex": 0,
                "stage": "check_dashboard",
                "failures": {},
            }
            state_file.write_text(json.dumps(state), encoding="utf-8")
            with (
                patch.object(PIPELINE, "STATE_FILE", state_file),
                patch.object(PIPELINE, "TASK_FILE", task_file),
            ):
                first = PIPELINE.fail("check_dashboard", "first_error")
            self.assertEqual(first["status"], "failed")
            self.assertEqual(first["attempts"], 1)
            state["status"] = "waiting_external"
            state["failures"] = {"check_dashboard": 1}
            state_file.write_text(json.dumps(state), encoding="utf-8")
            with (
                patch.object(PIPELINE, "STATE_FILE", state_file),
                patch.object(PIPELINE, "TASK_FILE", task_file),
            ):
                second = PIPELINE.fail("check_dashboard", "second_error")
            self.assertEqual(second["status"], "hard_failed")
            self.assertEqual(second["attempts"], 2)

    def test_start_with_article_skips_to_validate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            article_path = root / "article.html"
            title = "测试标题"
            article_path.write_text(
                '<p data-bjh-role="intro">测试</p>',
                encoding="utf-8",
            )
            # start() writes STATE_FILE before calling emit_task
            state_file = root / "pipeline_state.json"
            task_file = root / "_task.json"
            with (
                patch.object(PIPELINE, "STATE_FILE", state_file),
                patch.object(PIPELINE, "TASK_FILE", task_file),
            ):
                PIPELINE.start(article_path, title)
            # State should exist and indicate validate_article stage
            self.assertTrue(state_file.exists())
            state = json.loads(state_file.read_text(encoding="utf-8"))
            self.assertEqual(state["stageIndex"], 4)


if __name__ == "__main__":
    unittest.main()
