"""
头条号自动发布 - 文章验证模块 (v8.0)
输入完整HTML，输出JSON验证结果。
阈值来自 config/thresholds.yaml，不硬编码。
"""
import re, json, sys
from html.parser import HTMLParser
from scripts.lib.config_loader import get_thresholds

class ArticleValidator:
    CJK_RE = re.compile(r'[一-鿿㐀-䶿豈-﫿]')
    SENTENCE_END_RE = re.compile(r'[。！？.!?]')
    FORBIDDEN_CTA = [
        "评论区说说", "来评论区说说", "你学会了吗", "你觉得呢",
        "评论区见", "转发给需要的人",
        "不妨试试", "要不你也试试", "下次试试看", "你也行动起来吧",
        "关注我", "求点赞", "求关注", "求转发",
    ]
    MARKDOWN_LEAK_RE = re.compile(r'^#{1,6}\s', re.MULTILINE)

    def __init__(self, html: str):
        self.html = html
        self.plain_text = self._extract_text(html)
        self.paragraphs = self._extract_paragraphs(html)
        self.t = get_thresholds()["article"]

    def _extract_text(self, html: str) -> str:
        """Strip HTML tags to get plain text"""
        tag_re = re.compile(r'<[^>]+>')
        return tag_re.sub('', html).strip()

    def _extract_paragraphs(self, html: str):
        """Extract all <p> tag contents"""
        class Parser(HTMLParser):
            def __init__(self):
                super().__init__()
                self.paras = []
                self.in_p = False
                self.current = ""
            def handle_starttag(self, tag, attrs):
                if tag == 'p':
                    self.in_p = True
                    self.current = ""
            def handle_endtag(self, tag):
                if tag == 'p':
                    self.in_p = False
                    self.paras.append(self.current.strip())
                    self.current = ""
            def handle_data(self, data):
                if self.in_p:
                    self.current += data
        p = Parser()
        p.feed(html)
        return p.paras

    def validate(self):
        failures = []

        # === 汉字计数 ===
        chinese_chars = self.CJK_RE.findall(self.plain_text)
        chinese_count = len(chinese_chars)

        # === 段落 ===
        all_p = self.paragraphs
        para_count = len(all_p)
        empty_paras = [i+1 for i, p in enumerate(all_p) if not p.strip()]
        punct_only_paras = [
            i+1 for i, p in enumerate(all_p)
            if p.strip() and not self.CJK_RE.search(p)
        ]
        over_60_paras = [
            i+1 for i, p in enumerate(all_p)
            if len(self.CJK_RE.findall(p)) > self.t["per_para_chinese_max"]
        ]

        # === 句数检查 ===
        max_sentences = 0
        single_sentence_count = 0
        non_heading_paras = 0
        for p in all_p:
            if not p.strip() or not self.CJK_RE.search(p):
                continue
            # Check if this is a heading/small title (short, no sentence end)
            p_text = p.strip()
            is_heading = (len(p_text) < self.t["heading_char_threshold"] and not self.SENTENCE_END_RE.search(p_text))
            if is_heading:
                continue
            non_heading_paras += 1
            sentences = len(self.SENTENCE_END_RE.findall(p_text))
            sentences = max(sentences, 1)
            if sentences > max_sentences:
                max_sentences = sentences
            if sentences <= 1:
                single_sentence_count += 1

        single_sentence_ratio = single_sentence_count / max(non_heading_paras, 1)

        # === Markdown标题泄漏（在段落文本和原始HTML中检测） ===
        # 检测段落文本中的markdown标题模式
        md_leaks = self.MARKDOWN_LEAK_RE.findall(self.plain_text)
        # 同时在原始HTML中检测非标签的markdown标题模式
        html_md_leaks = re.findall(r'(?<!<)>?#{1,6}\s+\S', self.html)
        md_leaks.extend(html_md_leaks)

        # === 禁用CTA ===
        found_cta = [c for c in self.FORBIDDEN_CTA if c in self.plain_text]

        # === 小标题检测（<h2> <h3> <strong>段落等） ===
        heading_count = self._count_headings()

        # === 逗号数检测 ===
        comma_overage = []
        for i, p in enumerate(all_p):
            if self.CJK_RE.search(p):
                commas = p.count('，')
                if commas > self.t["max_commas_per_para"]:
                    comma_overage.append(i+1)

        # === 连续纯正文段检测 ===
        max_consecutive = self._max_consecutive_text_paras()

        # === 构建结果 ===
        passed = True
        checks = {}
        failures = []

        checks["chinese_count"] = chinese_count
        if chinese_count < self.t["chinese_min"]:
            checks["chinese_count_fail"] = True
            failures.append(f"chinese_count={chinese_count} < {self.t['chinese_min']}")

        checks["paragraph_count"] = para_count
        if para_count < self.t["para_count_min"] or para_count > self.t["para_count_max"]:
            checks["paragraph_count_fail"] = True
            failures.append(f"paragraph_count={para_count} not in [{self.t['para_count_min']},{self.t['para_count_max']}]")

        checks["empty_paragraphs"] = empty_paras
        if empty_paras:
            checks["empty_paragraphs_fail"] = True
            failures.append(f"empty_paragraphs={empty_paras}")
        else:
            checks["empty_paragraphs_fail"] = False

        checks["punctuation_only_paragraphs"] = punct_only_paras
        if punct_only_paras:
            checks["punctuation_only_paras_fail"] = True
            failures.append(f"punctuation_only_paragraphs={punct_only_paras}")
        else:
            checks["punctuation_only_paras_fail"] = False

        checks["over_60_paragraphs"] = over_60_paras
        if over_60_paras:
            checks["over_60_paras_fail"] = True
            failures.append(f"over_60_paragraphs={over_60_paras}")

        checks["max_sentence_count"] = max_sentences
        if max_sentences > self.t["max_sentences_per_para"]:
            checks["max_sentence_fail"] = True
            failures.append(f"max_sentences={max_sentences} > {self.t['max_sentences_per_para']}")

        checks["single_sentence_ratio"] = round(single_sentence_ratio, 4)
        if single_sentence_ratio < self.t["single_sentence_ratio_min"]:
            checks["single_sentence_ratio_fail"] = True
            failures.append(f"single_sentence_ratio={single_sentence_ratio:.2%} < 80%")

        checks["forbidden_cta"] = found_cta
        if found_cta:
            checks["forbidden_cta_fail"] = True
            failures.append(f"forbidden_cta={found_cta}")

        checks["heading_count"] = heading_count
        if heading_count < self.t["heading_count_min"] or heading_count > self.t["heading_count_max"]:
            checks["heading_count_fail"] = True
            failures.append(f"heading_count={heading_count} not in [{self.t['heading_count_min']},{self.t['heading_count_max']}]")

        checks["markdown_leaks"] = len(md_leaks)
        if md_leaks:
            checks["markdown_leaks_fail"] = True
            failures.append(f"markdown_leaks={md_leaks}")

        checks["comma_overage_paras"] = comma_overage
        if comma_overage:
            checks["comma_overage_fail"] = True
            failures.append(f"comma_overage_paras={comma_overage}")

        checks["max_consecutive_text_paras"] = max_consecutive

        passed = not failures

        return {
            "chinese_count": chinese_count,
            "paragraph_count": para_count,
            "empty_paragraphs": empty_paras,
            "punctuation_only_paragraphs": punct_only_paras,
            "markdown_leaks": len(md_leaks),
            "over_60_paragraphs": over_60_paras,
            "max_sentence_count": max_sentences,
            "single_sentence_ratio": round(single_sentence_ratio, 4),
            "forbidden_cta": found_cta,
            "heading_count": heading_count,
            "comma_overage_paras": comma_overage,
            "max_consecutive_text_paras": max_consecutive,
            "passed": passed,
            "failures": failures,
        }

    def _count_headings(self):
        # Count paragraphs that look like small titles: short, no sentence end
        count = 0
        for p in self.paragraphs:
            p = p.strip()
            if not p or not self.CJK_RE.search(p):
                continue
            # Lowercase detection for <strong> wrapped short lines
            if re.search(r'<strong>[^<]{2,30}</strong>', self.html):
                count += 1
            # Short paragraphs (<30 chars, no sentence end) are headings
            if len(p) < 30 and not self.SENTENCE_END_RE.search(p):
                count += 1
            # Explicit h2/h3 tags
        count += len(re.findall(r'</?h[23]>', self.html, re.IGNORECASE))
        return count

    def _max_consecutive_text_paras(self):
        max_run = run = 0
        for p in self.paragraphs:
            if not p.strip() or not self.CJK_RE.search(p):
                run = 0
                continue
            is_heading = (len(p.strip()) < self.t["heading_char_threshold"] and not self.SENTENCE_END_RE.search(p.strip()))
            if is_heading:
                run = 0
                continue
            run += 1
            max_run = max(max_run, run)
        return max_run


def main():
    if len(sys.argv) < 2:
        html = sys.stdin.read()
    else:
        with open(sys.argv[1], "r", encoding="utf-8") as f:
            html = f.read()

    v = ArticleValidator(html)
    result = v.validate()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
