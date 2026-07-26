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


def build_valid_html() -> str:
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
        for _ in range(7):
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
        result = validate_html(build_valid_html(), title="洗衣凝珠一次放几颗七天实测结果差别很明显")
        self.assertTrue(result.pass_gate, result.failures)
        self.assertEqual(result.metrics["contentParagraphs"], 49)
        self.assertEqual(result.metrics["sectionCount"], 6)

    def test_bare_text_is_rejected(self) -> None:
        result = validate_html(build_valid_html() + "\n裸文本测试", title="洗衣凝珠一次放几颗七天实测结果差别很明显")
        self.assertFalse(result.pass_gate)
        self.assertIn("存在段落节点之外的裸文本", result.failures)

    def test_too_few_sections_is_rejected(self) -> None:
        """少于3个小节熔断"""
        html = build_valid_html()
        for i in range(4):  # 保留前2节，删掉4节 → 只剩2节 < 3
            html = html.replace(
                f'<p data-bjh-role="section-title" data-bjh-section="{i+1}">'
                f'<strong>第{i+1}组家庭观察结果</strong></p>\n',
                "",
            )
        result = validate_html(html, title="洗衣凝珠一次放几颗七天实测结果差别很明显")
        self.assertFalse(result.pass_gate)
        self.assertTrue(any(item.startswith("小节数") for item in result.failures))

    def test_too_short_content_is_rejected(self) -> None:
        """汉字数不足2000熔断"""
        html = "<p data-bjh-role='section-title'><strong>标题</strong></p>" * 4
        html += "<p data-bjh-role='section-body'>这是一个短段内容</p>" * 10
        result = validate_html(html, title="测试标题")
        self.assertFalse(result.pass_gate)
        self.assertTrue(any("汉字" in item for item in result.failures))


if __name__ == "__main__":
    unittest.main()
