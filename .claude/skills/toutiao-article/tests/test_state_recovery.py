"""
头条号自动发布 - 状态恢复测试 (v8.0)
测试 state.py 的恢复逻辑在各种场景下的行为。
"""
import sys, os, json, unittest, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Patch paths before importing state
import scripts.state as state

class TestStateRecovery(unittest.TestCase):

    def setUp(self):
        """Save original state file paths and reset to temp"""
        self.orig_state = state.STATE_FILE
        self.orig_history = state.HISTORY_FILE
        self.orig_metrics = state.METRICS_FILE
        self.tempdir = tempfile.mkdtemp()
        state.STATE_FILE = os.path.join(self.tempdir, "state.json")
        state.HISTORY_FILE = os.path.join(self.tempdir, "history.json")
        state.METRICS_FILE = os.path.join(self.tempdir, "metrics.json")
        state.reset_to_idle()

    def tearDown(self):
        state.STATE_FILE = self.orig_state
        state.HISTORY_FILE = self.orig_history
        state.METRICS_FILE = self.orig_metrics

    def test_new_task(self):
        """正常新任务 → new"""
        action, details = state.detect_recovery()
        self.assertEqual(action, "new")

    def test_publish_verified(self):
        """publish_verified=true → continue_next"""
        s = state.load_state()
        s["publish_verified"] = True
        s["title"] = "测试文章"
        s["phase"] = "done"
        state.save_state(s)
        action, details = state.detect_recovery()
        self.assertEqual(action, "continue_next")

    def test_publish_clicked_not_verified(self):
        """publish_clicked=true但publish_verified=false → verify_publish"""
        s = state.load_state()
        s["publish_clicked"] = True
        s["publish_verified"] = False
        s["title"] = "待核验文章"
        state.save_state(s)
        action, details = state.detect_recovery()
        self.assertEqual(action, "verify_publish")

    def test_idle_after_reset(self):
        """重置后状态为idle"""
        s = state.load_state()
        self.assertEqual(s["status"], "idle")
        self.assertEqual(s["phase"], "idle")

    def test_article_hash(self):
        """文章hash不变性"""
        content = "测试正文内容"
        h1 = state.article_hash(content)
        h2 = state.article_hash(content)
        self.assertEqual(h1, h2)

    def test_history_max_limit(self):
        """history.json保留最近60篇"""
        for i in range(65):
            state.append_history({
                "title": f"文章{i}",
                "topic": f"topic{i%8}",
                "direction": f"dir{i%5}",
                "series_id": f"s{i%3}",
                "publish_status": "scheduled",
                "article_hash": f"hash{i}",
            })
        h = state.load_history()
        self.assertLessEqual(len(h), 60)
        self.assertEqual(h[-1]["title"], "文章64")

    def test_update_state_fields(self):
        """update_state正确更新字段"""
        state.update_state(title="测试", phase="2", article_index=1)
        s = state.load_state()
        self.assertEqual(s["title"], "测试")
        self.assertEqual(s["phase"], "2")
        self.assertEqual(s["article_index"], 1)

    def test_dirty_editor_detection(self):
        """脏编辑器检测"""
        self.assertFalse(state.detect_dirty_editor(""))
        self.assertFalse(state.detect_dirty_editor("<p><br></p>"))
        self.assertTrue(state.detect_dirty_editor("<p>有内容</p>"))


if __name__ == "__main__":
    unittest.main()
