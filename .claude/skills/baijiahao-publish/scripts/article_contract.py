from __future__ import annotations

from dataclasses import dataclass, field
from html.parser import HTMLParser
from statistics import stdev, mean
from pathlib import Path
import re
from typing import Iterable

CJK_RE = re.compile(r"[一-鿿豈-﫿]")
BANNED_PHRASES = ("你应该", "你必须", "你一定", "建议你")
COMMENT_BAIT_RE = re.compile(r"评论区|留言区|欢迎留言|留言告诉|评论告诉")

# AI 味过渡词——机器最爱用、真人几乎不用
AI_TRANSITIONS = [
    "值得注意的是", "不可否认", "众所周知", "综上所述",
    "不可忽视的是", "换句话说", "从某种程度上说",
    "毋庸置疑", "言归正传", "毫不夸张地说",
    "从这个角度来看", "值得一提的是",
    "需要指出的是", "需要说明的是",
    "不可否认的是", "众所周知的是",
]

# 情绪标签——机器给读者"贴标签"，真人直接讲感受
AI_EMOTIONAL_LABELS = re.compile(
    r"令人[震惊心痛担忧欣慰感动遗憾恐惧不安欣喜赞叹唏嘘]"
    r"的是|让人[震惊心痛担忧欣慰感动]的是"
    r"|使人[震惊心痛担忧]的是"
)

# 典型排比句式（机器常用结构）
AI_PARALLEL_PATTERNS = re.compile(
    r"不仅[^，。]*更[^，。]|"
    r"既[^，。]*又[^，。]|"
    r"无论[^，。]*都[^，。]|"
    r"不但[^，。]*而且[^，。]"
)

MIN_TOTAL_CJK = 2000
MIN_SECTIONS = 3  # 至少要有 3 个小节（不是强制 6），低于这个太敷衍
MAX_SECTIONS = 10  # 超过太多可能是凑内容


@dataclass
class Paragraph:
    role: str
    section: str | None
    attrs: dict[str, str]
    text_parts: list[str] = field(default_factory=list)
    strong_count: int = 0
    image_count: int = 0

    @property
    def text(self) -> str:
        return "".join(self.text_parts)

    @property
    def cjk_len(self) -> int:
        return len(CJK_RE.findall(self.text))

    @property
    def char_len(self) -> int:
        return len(self.text)


@dataclass
class ArticleValidation:
    pass_gate: bool
    failures: list[str]
    warnings: list[str]
    metrics: dict[str, object]

    def as_dict(self) -> dict[str, object]:
        return {
            "pass": self.pass_gate,
            "failures": self.failures,
            "warnings": self.warnings,
            "metrics": self.metrics,
        }


class ArticleParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.paragraphs: list[Paragraph] = []
        self.outside_text: list[str] = []
        self.errors: list[str] = []
        self.current: Paragraph | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        attr_map = {key: value or "" for key, value in attrs}
        if tag == "p":
            if self.current is not None:
                self.errors.append("段落节点发生嵌套")
                return
            self.current = Paragraph(
                role=attr_map.get("data-bjh-role", ""),
                section=attr_map.get("data-bjh-section") or None,
                attrs=attr_map,
            )
            return
        if self.current is None:
            return
        if tag == "strong":
            self.current.strong_count += 1
        if tag == "img":
            self.current.image_count += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "p" and self.current is not None:
            self.paragraphs.append(self.current)
            self.current = None

    def handle_data(self, data: str) -> None:
        if self.current is None:
            if data.strip():
                self.outside_text.append(data.strip())
            return
        self.current.text_parts.append(data)

    def close(self) -> None:
        super().close()
        if self.current is not None:
            self.errors.append("存在未闭合的段落节点")


def cjk_count(text: str) -> int:
    return len(CJK_RE.findall(text))


def validate_html(
    html: str,
    title: str | None = None,
    keywords: list[str] | None = None,
) -> ArticleValidation:
    parser = ArticleParser()
    parser.feed(html)
    parser.close()
    failures = list(parser.errors)
    warnings: list[str] = []

    if parser.outside_text:
        failures.append("存在段落节点之外的裸文本")

    paragraphs = parser.paragraphs
    section_titles = [p for p in paragraphs if p.role == "section-title"]
    content_paragraphs = [p for p in paragraphs if p.role in ("intro", "section-body", "outro")]
    total_cjk = sum(cjk_count(p.text) for p in content_paragraphs)

    # ── 质量门（熔断级）──
    if total_cjk < MIN_TOTAL_CJK:
        failures.append(f"正文汉字：{total_cjk}<{MIN_TOTAL_CJK}")

    if not MIN_SECTIONS <= len(section_titles) <= MAX_SECTIONS:
        failures.append(f"小节数：{len(section_titles)}，期望{MIN_SECTIONS}-{MAX_SECTIONS}个")

    # 每个小节标题必须加粗（配图需要）
    for st in section_titles:
        if st.strong_count < 1:
            failures.append(f"小节{st.section or '?'}：标题未加粗（配图需要）")

    # 注入前不得含图
    for p in paragraphs:
        if p.image_count:
            failures.append(f"节点X：注入前正文不得包含图片")

    # 🔴 2026-07-26 正文段落内禁止加粗：只有 data-bjh-role="section-title" 能用 <strong>
    for p in paragraphs:
        if p.role != "section-title" and p.strong_count > 0:
            failures.append(
                f"正文段落（role={p.role}）含{ p.strong_count }处<strong>加粗，"
                f"只有小节标题才能加粗"
            )

    # 权威口吻
    full_text = "".join(p.text for p in content_paragraphs)
    for phrase in BANNED_PHRASES:
        if phrase in full_text:
            failures.append(f"权威口吻：含“{phrase}”")

    # 评论区引导
    if COMMENT_BAIT_RE.search(full_text):
        failures.append("引导话术：含评论或留言引导")

    # ── AI 味检测（警告级，不熔断）──
    # 1. 段落长度异常均匀 → 机器排版
    body_paras = [p for p in paragraphs if p.role == "section-body"]
    body_lengths = [p.char_len for p in body_paras]
    if len(body_lengths) >= 5:
        avg = mean(body_lengths)
        sd = stdev(body_lengths)
        # 标准差 < 平均值的 30% → 太均匀，像机器
        if sd < avg * 0.25 and avg > 0:
            warnings.append(
                f"AI 味：段落长度过于均匀（标准差{sd:.0f}，均值{avg:.0f}）"
            )

    # 2. 各小节段落数完全一致 → 模板痕迹
    section_counts = {}
    for p in body_paras:
        section_counts.setdefault(p.section, 0)
        section_counts[p.section] += 1
    if len(set(section_counts.values())) == 1 and len(section_counts) >= 3:
        unique_val = list(section_counts.values())[0]
        warnings.append(
            f"AI 味：所有小节段落数完全一致（{unique_val}段/节）——真人写作不会这么整齐"
        )

    # 3. AI 过渡词
    found_transitions = []
    for t in AI_TRANSITIONS:
        if t in full_text:
            found_transitions.append(t)
    if found_transitions:
        warnings.append(f"AI 味：检测到{len(found_transitions)}个机器常用过渡词（{', '.join(found_transitions)}）")

    # 4. 情绪标签
    matched_labels = AI_EMOTIONAL_LABELS.findall(full_text)
    if matched_labels:
        warnings.append(f"AI 味：检测到{len(matched_labels)}处情绪标签式表达（“令人XX的是”），真人写感情靠细节不靠贴标签")

    # 5. 排比句式密集
    parallel_count = len(AI_PARALLEL_PATTERNS.findall(full_text))
    if parallel_count >= 3:
        warnings.append(f"AI 味：检测到{parallel_count}处排比句式（“不仅…更…”类），机器最喜欢用这种结构")

    # ── 指标上报 ──
    metrics: dict[str, object] = {
        "hanCount": total_cjk,
        "contentParagraphs": len(content_paragraphs),
        "sectionCount": len(section_titles),
        "sectionParasVariance": (
            round(sd, 1)
            if body_lengths and len(body_lengths) >= 5
            else None
        ),
        "aiTransitionWords": len(found_transitions),
        "aiEmotionalLabels": len(matched_labels),
        "aiParallelStructures": parallel_count,
    }

    return ArticleValidation(not failures, failures, warnings, metrics)


def validate_file(
    path: Path,
    title: str | None = None,
    keywords: list[str] | None = None,
) -> ArticleValidation:
    return validate_html(path.read_text(encoding="utf-8"), title=title, keywords=keywords)


def format_failures(failures: Iterable[str]) -> str:
    return "；".join(failures)
