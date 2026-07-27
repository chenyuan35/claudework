from __future__ import annotations

from pathlib import Path
import sys
import unittest

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from article_contract import validate_html  # noqa: E402


def content_text(index: int) -> str:
    dialogue = "我妈问：“这次记录可靠吗？”" if index == 1 else ""
    return (
        f"我家第{index}次记录时把第一项变化写进表格，"
        f"又把第二项结果逐条核对，{dialogue}"
        "我连续观察以后发现前后数据保持一致，整个过程也能重新复核清楚。"
    )


def build_valid_html(body_per_section: int = 8) -> str:
    """生成恰好 6 节、汉字 ≥2000 的合法文章。"""
    lines = []
    index = 1
    for _ in range(4):
        lines.append(f'<p data-bjh-role="intro">{content_text(index)}</p>')
        index += 1
    for section in range(1, 7):
        lines.append(
            f'<p data-bjh-role="section-title" data-bjh-section="{section}">'
            f'<strong>第{section}组家庭观察结果</strong></p>'
        )
        # 各节段落数略有差异，避免 AI 味「整齐」警告
        count = body_per_section + (section % 3)
        for _ in range(count):
            lines.append(
                f'<p data-bjh-role="section-body" data-bjh-section="{section}">'
                f'{content_text(index)}</p>'
            )
            index += 1
    for _ in range(3):
        lines.append(f'<p data-bjh-role="outro">{content_text(index)}</p>')
        index += 1
    return "\n".join(lines)


class ArticleContractTests(unittest.TestCase):
    def test_valid_contract_passes(self) -> None:
        result = validate_html(
            build_valid_html(),
            title="洗衣凝珠一次放几颗七天实测结果差别很明显",
        )
        self.assertTrue(result.pass_gate, result.failures)
        self.assertGreaterEqual(result.metrics["hanCount"], 2000)
        self.assertEqual(result.metrics["sectionCount"], 6)

    def test_bare_text_is_rejected(self) -> None:
        result = validate_html(
            build_valid_html() + "\n裸文本测试",
            title="洗衣凝珠一次放几颗七天实测结果差别很明显",
        )
        self.assertFalse(result.pass_gate)
        self.assertIn("存在段落节点之外的裸文本", result.failures)

    def test_wrong_section_count_is_rejected(self) -> None:
        """小节数必须恰好 6"""
        html = build_valid_html()
        # 删掉第 6 节标题与其后 body，留下 5 节
        html = html.replace(
            '<p data-bjh-role="section-title" data-bjh-section="6">'
            "<strong>第6组家庭观察结果</strong></p>\n",
            "",
        )
        result = validate_html(html, title="洗衣凝珠一次放几颗七天实测结果差别很明显")
        self.assertFalse(result.pass_gate)
        self.assertTrue(any(item.startswith("小节数") for item in result.failures))

    def test_too_short_content_is_rejected(self) -> None:
        """汉字数不足2000熔断"""
        html = "<p data-bjh-role='section-title'><strong>标题</strong></p>" * 6
        html += "<p data-bjh-role='section-body'>这是一个短段内容</p>" * 10
        result = validate_html(html, title="测试标题")
        self.assertFalse(result.pass_gate)
        self.assertTrue(any("汉字" in item for item in result.failures))

    def test_body_strong_is_rejected(self) -> None:
        html = build_valid_html()
        html = html.replace(
            'data-bjh-role="section-body" data-bjh-section="1">',
            'data-bjh-role="section-body" data-bjh-section="1"><strong>加粗</strong>',
            1,
        )
        result = validate_html(html, title="洗衣凝珠一次放几颗七天实测结果差别很明显")
        self.assertFalse(result.pass_gate)
        self.assertTrue(any("加粗" in item for item in result.failures))

    def test_severe_ai_transitions_fail(self) -> None:
        html = build_valid_html()
        # 注入 3 个 AI 过渡词
        poison = (
            '<p data-bjh-role="section-body" data-bjh-section="1">'
            "值得注意的是，不可否认，众所周知，这三项都很关键。</p>\n"
        )
        html = poison + html
        result = validate_html(html, title="洗衣凝珠一次放几颗七天实测结果差别很明显")
        self.assertFalse(result.pass_gate)
        self.assertTrue(any("AI 味过重" in item for item in result.failures))


if __name__ == "__main__":
    unittest.main()
