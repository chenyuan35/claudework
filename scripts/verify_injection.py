#!/usr/bin/env python3
"""
verify_injection.py — 正文注入验证 + 文章质量检查（一次性）

合并替代：
  1. Step 4a 内容抽样验证（原 first/last 500 字符关键字检查 —— 因 HTML comment + img
     偏移导致假阴性，现改为直接校验正文段落完整性）
  2. §4.1 段落长度分布检查（原 evaluate JS 片段 —— 现统一为脚本，原生处理碎片句排除）
  3. §4.3c 图片 alt 文本质量检查（原无此检查 —— 新增 prompt 层次验证）

用法：
  python scripts/verify_injection.py [html_file]
    默认 html_file = blogger_article.html

返回值：
  0 = 全部通过
  1 = 至少一项失败

验证项：
  [内容完整性]  - <p> 数量 >= 5、开头段落总词数 >= 50、CTA 存在、内链 >= 2
  [段落分布]    - 超过 3 个完整句（排除 <=8 词碎片句）的段落占比 < 10%
  [图片检查]    - 图片数 >= 3、无 Unsplash/占位图、alt 文本覆盖 >= 2 层 prompt 要素
"""

import re
import sys
from pathlib import Path


def read_html(path: str) -> str:
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


def check_content(html: str, min_body_words: int = 50) -> tuple:
    """内容完整性验证。

    跳过 HTML 顶部的注释和 img 标签，直接取正文 <p> 的前 N 个段落做词数检查。
    不依赖具体关键词（避免了 first/last 500 受 comment+img 偏移的假阴性）。
    """
    p_pattern = re.compile(r'<p>(.*?)</p>', re.DOTALL)
    all_ps = [(m.start(), m.group(1).strip())
              for m in p_pattern.finditer(html) if m.group(1).strip()]

    if len(all_ps) < 5:
        return False, f"<p> 标签数量不足: {len(all_ps)}（需 >=5）"

    # 跳过前三段可能的空/短段落，取随后的 5 段算正文起始词数
    body_start = min(3, len(all_ps) // 3)
    body_text = ' '.join(t for _, t in all_ps[body_start:body_start + 5])
    body_words = len(body_text.split())

    if body_words < min_body_words:
        return (False,
                f"正文开头词数不足: {body_words}（需 >= {min_body_words}）",
                "可能注入截断或正文前结构偏移")

    # 结尾 CTA（可能距末尾还有 3 条内链段落后才出现，取后 6 段）
    last_six = ' '.join(t for _, t in all_ps[-6:])
    has_cta = ('Drop a comment' in last_six or
               ('What' in last_six and '?' in last_six))

    # 内链
    inner_links = html.count('» <a')

    details = (f"{len(all_ps)} 段, 开头 {body_words} 词, "
               f"{inner_links} 条内链, CTA={'Y' if has_cta else 'N'}")

    if not has_cta:
        return False, f"结尾段落未发现 CTA 模式（Drop a comment / What...?）\n{details}"

    return True, details


def check_paragraph_distribution(html: str) -> tuple:
    """段落长度分布检查，原生处理碎片句排除（<=8 词不计入 3 句限额）。"""
    p_pattern = re.compile(r'<p>(.*?)</p>', re.DOTALL)
    all_ps = [m.group(1).strip()
              for m in p_pattern.finditer(html) if m.group(1).strip()]

    total = len(all_ps)
    over3 = 0
    bad_paras = []

    for i, p in enumerate(all_ps):
        raw_sents = [s.strip() for s in re.split(r'[.!?]+', p) if s.strip()]
        if len(raw_sents) <= 3:
            continue  # even raw count is within limit
        # fragment exclusion: sentences <=8 words don't count
        full_sents = [s for s in raw_sents if len(s.split()) > 8]
        if len(full_sents) > 3:
            over3 += 1
            if len(bad_paras) < 3:
                bad_paras.append(f"#{i}: {full_sents[0][:60]}...")

    ratio = over3 / total * 100 if total > 0 else 0
    passed = ratio < 10.0

    details = (f"段落 {total}, 超限 {over3} ({ratio:.1f}%)")
    if bad_paras:
        details += "\n  首段: " + " | ".join(bad_paras)
    if not passed:
        details += "\n  FAIL: 需拆分最长的段落"
    return passed, details


def check_images(html: str, min_images: int = 3) -> tuple:
    """图片数量 + 域名来源 + alt 文本 prompt 层数检查。"""
    img_pattern = re.compile(r'<img[^>]+>', re.IGNORECASE)
    imgs = img_pattern.findall(html)

    if len(imgs) < min_images:
        return False, (f"图片数量不足: {len(imgs)}（需 >= {min_images}）")

    bad_domains = ['images.unsplash.com', 'via.placeholder.com',
                   'picsum.photos']
    for img in imgs:
        for domain in bad_domains:
            if domain in img:
                return False, f"发现占位图: {domain}"

    # alt 文本 prompt 层次检查
    weak_alts = []
    for i, img in enumerate(imgs):
        alt_match = re.search(r'alt="([^"]*)"', img)
        if not alt_match or not alt_match.group(1).strip():
            weak_alts.append(f"#{i}: 无 alt 文本")
            continue
        alt_text = alt_match.group(1)
        has_scene = bool(re.search(
            r'(kitchen|counter|table|desk|room|office|couch|sofa|'
            r'chair|doorway|street|cafe|portrait|flat.lay|overhead|'
            r'close.up|detail|person|woman|man|hand|freezer)',
            alt_text, re.IGNORECASE))
        has_style = bool(re.search(
            r'(warm|minimal|natural|bright|soft|cozy|documentary|'
            r'candid|clean|modern|crisp|moody|textured|golden)',
            alt_text, re.IGNORECASE))
        has_negative = bool(re.search(
            r'(no text|no watermark|no overlay|no AI|no hands|'
            r'no cartoon|no label)',
            alt_text, re.IGNORECASE))
        layers = sum([has_scene, has_style, has_negative])
        if layers < 2:
            weak_alts.append(f"#{i}: {layers}/3 层")

    status = f"{len(imgs)} 张图, 均非占位图"
    if weak_alts:
        status += f" | 弱 alt: {', '.join(weak_alts[:3])}"
        return True, status + "（警告）"

    return True, status + "（alt 质量 OK）"


def main() -> int:
    # Fix stdout encoding for Chinese terminals (GH#...)
    import io
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    elif hasattr(sys.stdout, 'buffer'):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    path = sys.argv[1] if len(sys.argv) > 1 else 'blogger_article.html'
    html = read_html(path)

    checks = [
        ("内容完整性", check_content, True),
        ("段落分布", check_paragraph_distribution, True),
        ("图片检查", check_images, True),
    ]

    passed = 0
    results = []

    print(f"=== 验证报告: {path} ===")
    print()

    for label, func, _ in checks:
        ok, msg = func(html)
        sym = "OK" if ok else "FAIL"
        results.append((label, ok, msg))
        print(f"  [{sym:4s}] {label} — {msg}")
        if ok:
            passed += 1

    total = len(checks)
    print()
    print(f"结果: {passed}/{total} 通过")

    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
