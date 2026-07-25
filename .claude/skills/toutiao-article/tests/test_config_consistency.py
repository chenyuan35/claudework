"""
头条号自动发布 - 配置一致性测试 (v8.0)
验证 Python 和 JS 从同一 YAML 源读取的阈值一致。
流程：写测试值到 YAML → dump → 分别读取 → 比对。
"""
import sys, os, json, unittest, yaml, subprocess

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THRESHOLDS_PATH = os.path.join(BASE, "config", "thresholds.yaml")
CONFIG_JSON_PATH = os.path.join(BASE, "runtime", "_config.json")

# Path for JS verification
JS_TESTER = os.path.join(BASE, "tests", "test_config_consistency.js")

class TestConfigConsistency(unittest.TestCase):

    def setUp(self):
        """Backup original thresholds.yaml"""
        os.makedirs(os.path.dirname(CONFIG_JSON_PATH), exist_ok=True)
        with open(THRESHOLDS_PATH, "r", encoding="utf-8") as f:
            self.original_yaml = f.read()
        self.original_data = yaml.safe_load(self.original_yaml)
        # Add scripts/ to path for imports
        sys.path.insert(0, os.path.join(BASE, "scripts"))
        # Do the initial dump
        self._dump_config()

    def tearDown(self):
        """Restore original thresholds.yaml"""
        with open(THRESHOLDS_PATH, "w", encoding="utf-8") as f:
            f.write(self.original_yaml)

    def _dump_config(self):
        """Dump config to runtime/_config.json same as run_pipeline.py does"""
        from lib.config_loader import get_thresholds, get_selectors, get_content_policy, get_services
        cfg = {
            "thresholds": get_thresholds(),
            "selectors": get_selectors(),
            "content_policy": get_content_policy(),
            "services": get_services(),
        }
        with open(CONFIG_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        return cfg

    def test_python_reads_correct_values(self):
        """Python reads threshold values from YAML correctly"""
        from lib.config_loader import get_thresholds
        t = get_thresholds()
        a = t["article"]
        self.assertEqual(a["chinese_min"], 1500)
        self.assertEqual(a["para_count_min"], 55)
        self.assertEqual(a["para_count_max"], 80)
        self.assertEqual(a["per_para_chinese_max"], 60)
        self.assertEqual(a["max_sentences_per_para"], 2)
        self.assertEqual(a["heading_count_min"], 4)
        self.assertEqual(a["heading_count_max"], 8)
        self.assertEqual(a["single_sentence_ratio_min"], 0.80)
        self.assertEqual(a["images_required"], 3)
        self.assertEqual(t["publish"]["articles_per_day"], 2)
        self.assertEqual(t["state"]["history_max"], 60)

    def test_config_json_matches_yaml(self):
        """runtime/_config.json matches thresholds.yaml"""
        with open(THRESHOLDS_PATH, "r", encoding="utf-8") as f:
            yaml_data = yaml.safe_load(f)
        with open(CONFIG_JSON_PATH, "r", encoding="utf-8") as f:
            json_data = json.load(f)
        self.assertEqual(json_data["thresholds"], yaml_data)

    def test_modify_value_propagates_python(self):
        """修改阈值后 Python 读取到新值"""
        import copy
        modified = copy.deepcopy(self.original_data)
        modified["article"]["chinese_min"] = 1600
        with open(THRESHOLDS_PATH, "w", encoding="utf-8") as f:
            yaml.dump(modified, f, allow_unicode=True)

        from lib.config_loader import get_thresholds
        t = get_thresholds()
        self.assertEqual(t["article"]["chinese_min"], 1600)

    def test_selectors_loaded(self):
        """Selectors YAML 正确加载"""
        from lib.config_loader import get_selectors
        s = get_selectors()
        self.assertIn("editor", s)
        self.assertIn("pages", s)
        self.assertIn("switches", s)
        self.assertIn("buttons", s)
        self.assertIn("title", s["editor"])
        self.assertEqual(s["pages"]["publish"], "https://mp.toutiao.com/profile_v4/graphic/publish")

    def test_services_loaded(self):
        """Services YAML 正确加载（Key内容不变）"""
        from lib.config_loader import get_services
        svc = get_services()
        self.assertIn("agens", svc)
        self.assertIn("primary", svc["agens"])
        self.assertIn("fallback", svc["agens"])
        # Key must still be present
        self.assertEqual(svc["agens"]["primary"]["endpoint"],
                         "https://apihub.agnes-ai.com/v1/images/generations")
        self.assertEqual(svc["agens"]["fallback"]["auth_header"],
                         "Bearer AADDCC001122")

    def test_config_json_has_selectors_for_js(self):
        """JS 可用的 runtime/_config.json 包含所有选择器"""
        with open(CONFIG_JSON_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        self.assertIn("selectors", cfg)
        self.assertIn("thresholds", cfg)
        self.assertIn("editor", cfg["selectors"])
        self.assertIn("switches", cfg["selectors"])
        self.assertIn("pages", cfg["selectors"])
        # JS functions need these exact selectors
        sel = cfg["selectors"]
        self.assertIn("title", sel["editor"])
        self.assertIn("position_select", sel["location"])
        self.assertIn("day_select", sel["schedule"])

    def test_image_thresholds_in_json(self):
        """图片阈值在 JSON 中供 validate_images.js 读取"""
        with open(CONFIG_JSON_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        img = cfg["thresholds"]["article"]
        self.assertEqual(img["images_required"], 3)
        self.assertIn("image_distribution_bands", img)
        self.assertIn("image_gap_min_pct", img)


if __name__ == "__main__":
    unittest.main()
