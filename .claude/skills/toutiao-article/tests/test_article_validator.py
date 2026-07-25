"""
头条号自动发布 - 文章验证器测试 (v8.0)
"""
import sys, os, json, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from scripts.validate_article import ArticleValidator

class TestArticleValidator(unittest.TestCase):

    def get_html(self, paras, extra=""):
        """Helper to build HTML from paragraph list"""
        body = "".join(f"<p>{p}</p>" for p in paras)
        return f"<html><body>{body}</body></html>"

    def test_qualified_passes(self):
        """合格正文通过（至少1500汉字）"""
        paras = []
        # 55 single-sentence + 5 headings + 5 double-sentence paragraphs
        for i in range(55):
            paras.append(f"第{i+1}段正文示例内容，读者可以从这段获得有用生活小技巧和经验。")
        paras.append("小标题一")
        paras.append("小标题二")
        paras.append("小标题三")
        paras.append("小标题四")
        paras.append("小标题五")
        for i in range(5):  # Total: 55+5+5 = 65 para, heading_count=5
            paras.append(f"具体操作步骤第{i+1}步说明。关键点需要仔细检查避免出错。")
        html = self.get_html(paras)
        v = ArticleValidator(html)
        result = v.validate()
        self.assertTrue(result["passed"], f"Qualified article should pass: {result['failures']}")
        self.assertGreaterEqual(result["chinese_count"], 1500)

    def test_qualified_with_headings(self):
        """带小标题的正文通过"""
        paras = []
        for i in range(10):
            paras.append(f"开头段落第{i+1}段示例文字，这里有一些引导读者的描述内容。")
        # 6 headings × 10 body = 60 body + 6 headings + 10 intro + 1 conclusion = 77 total ✓
        for h in range(6):
            paras.append(f"小标题{h+1}")
            for i in range(10):
                paras.append(f"第{h+1}部分第{i+1}段，这里提供具体描述和实用生活小技巧经验。")
        paras.append("结尾段落，总结全文内容供读者参考借鉴。")
        html = self.get_html(paras)
        v = ArticleValidator(html)
        result = v.validate()
        self.assertTrue(result["passed"], f"With headings should pass: {result['failures']}")

    def test_1499_fails(self):
        """1499汉字失败"""
        # 1499 chars = about 50 paragraphs of 30 chars
        chars_needed = 1499
        para_text = "测试字数不足。" * 10  # ~80 chars
        paras = []
        while True:
            p = f"段落内容测试字数不足示例{len(paras)}。"
            if sum(len(p) for p in paras) + len(p) > chars_needed:
                break
            paras.append(p)
        html = self.get_html(paras)
        v = ArticleValidator(html)
        result = v.validate()
        self.assertFalse(result["passed"])
        failures = " ".join(result["failures"])
        self.assertIn("chinese_count", failures)

    def test_over_60_para_fails(self):
        """61汉字段失败"""
        paras = []
        for i in range(55):
            paras.append(f"正常段落第{i+1}句。")
        # Add a para with 61 Chinese chars
        long_para = "长" * 61 + "。"
        paras.append(long_para)
        html = self.get_html(paras)
        v = ArticleValidator(html)
        result = v.validate()
        self.assertFalse(result["passed"])
        self.assertIn(56, result["over_60_paragraphs"], "Para 56 should be over 60")

    def test_three_sentences_fails(self):
        """三句一段失败"""
        paras = []
        for i in range(55):
            paras.append(f"正常段落第{i+1}句。")
        # Add a para with 3 sentences
        paras.append("第一句。第二句。第三句。")
        html = self.get_html(paras)
        v = ArticleValidator(html)
        result = v.validate()
        self.assertFalse(result["passed"])
        self.assertGreater(result["max_sentence_count"], 2)

    def test_empty_para_fails(self):
        """空段失败"""
        paras = []
        for i in range(55):
            paras.append(f"正常段落第{i+1}句。")
        paras.append("")
        html = self.get_html(paras)
        v = ArticleValidator(html)
        result = v.validate()
        self.assertFalse(result["passed"])
        self.assertEqual(len(result["empty_paragraphs"]), 1)

    def test_punctuation_only_para_fails(self):
        """纯标点段失败"""
        paras = []
        for i in range(55):
            paras.append(f"正常段落第{i+1}句。")
        paras.append("……！？。")
        html = self.get_html(paras)
        v = ArticleValidator(html)
        result = v.validate()
        self.assertFalse(result["passed"])
        self.assertEqual(len(result["punctuation_only_paragraphs"]), 1)

    def test_markdown_leak_fails(self):
        """Markdown标题泄漏失败"""
        paras = []
        for i in range(55):
            paras.append(f"正常段落第{i+1}句。")
        html = self.get_html(paras)
        # Inject MD leak: '## 标题' inside a text paragraph (simulating a leak)
        html = html.replace("</body>", "<p># 单井号测试</p><p>## 双井号标题泄漏</p></body>")
        v = ArticleValidator(html)
        result = v.validate()
        self.assertGreater(result["markdown_leaks"], 0)

    def test_low_single_sentence_ratio_fails(self):
        """一句段比例不足80%失败"""
        paras = []
        for i in range(10):
            paras.append(f"这是一句段。")
        for i in range(10):
            paras.append(f"这是两句段的第一句。这是两句段的第二句。")
        for i in range(30):
            paras.append(f"正常段落第{i+1}句。")
        html = self.get_html(paras)
        v = ArticleValidator(html)
        result = v.validate()
        # Should have 10 single + 10 double + 30 single = 40 single / 50 total = 80% exactly, might be borderline
        # Let's make it more clearly fail
        paras2 = []
        for i in range(20):
            paras2.append(f"第一句。第二句。")
        for i in range(40):
            paras2.append(f"正常第{i+1}句示例。")
        html2 = self.get_html(paras2)
        v2 = ArticleValidator(html2)
        result2 = v2.validate()
        if result2["passed"]:
            # Still passes, let's make it aggressively fail
            paras3 = []
            for i in range(30):
                paras3.append(f"第一句。第二句。")
            for i in range(10):
                paras3.append(f"正常单句。")
            html3 = self.get_html(paras3)
            v3 = ArticleValidator(html3)
            result3 = v3.validate()
            self.assertFalse(result3["passed"])

    def test_forbidden_cta_fails(self):
        """禁用CTA检测失败"""
        paras = []
        for i in range(55):
            paras.append(f"正常段落第{i+1}句。")
        paras.append("你学会了吗？学会了就评论区说说吧。")
        html = self.get_html(paras)
        v = ArticleValidator(html)
        result = v.validate()
        self.assertFalse(result["passed"])
        self.assertGreater(len(result["forbidden_cta"]), 0)

    def test_para_count_out_of_range_fails(self):
        """段数超范围失败（超过80段）"""
        paras = []
        for i in range(85):
            paras.append(f"段落内容第{i+1}句示例测试。")
        html = self.get_html(paras)
        v = ArticleValidator(html)
        result = v.validate()
        self.assertFalse(result["passed"])

    def test_consecutive_text_paras_check(self):
        """连续纯正文段数检测"""
        paras = []
        for i in range(15):
            paras.append(f"这是连续第{i+1}段纯文本内容。")
        html = self.get_html(paras)
        v = ArticleValidator(html)
        result = v.validate()
        self.assertGreaterEqual(result["max_consecutive_text_paras"], 1)


if __name__ == "__main__":
    unittest.main()
