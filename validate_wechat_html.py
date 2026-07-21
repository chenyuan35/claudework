#!/usr/bin/env python3
"""validate_wechat_html.py — 强制发布门禁

在插入微信编辑器前检查 article_final.html。
全部检查通过才允许进入上传/封面/保存阶段。

用法：
  python validate_wechat_html.py article_final.html [--img-count 3] [--min-chars 2400] [--max-chars 3000]

退出码：
  0 = 全部通过
  1 = 至少一项失败
"""

import re, sys, argparse
from pathlib import Path


def validate(html_path, expected_imgs=3, min_chars=2400, max_chars=3000):
    """检查 HTML，返回 (pass, [(check_name, ok, detail), ...])"""
    html = Path(html_path).read_text('utf-8')
    checks = []

    # 1. Markdown 残留计数必须为 0
    md_patterns = [
        ('**', r'\*\*[^*]+\*\*'),
        ('==', r'==[^=]+=='),
        ('!!', r'!![^!]+!!'),
        ('~~', r'~~[^~]+~~'),
        ('###', r'^###? '),
        ('```', r'```'),
        ('[',   r'\[.+?\]\(.+?\)'),
    ]
    md_found = {}
    for name, pat in md_patterns:
        hits = re.findall(pat, html, re.MULTILINE)
        if hits:
            md_found[name] = len(hits)
    checks.append(('markdown残留', len(md_found) == 0,
                   f'发现 {md_found}' if md_found else '无'))

    # 2. inline 占位符数量必须为 0
    placeholder_hits = re.findall(r'\[插图：[^\]]*\]', html)
    checks.append(('inline占位符', len(placeholder_hits) == 0,
                   f'发现 {len(placeholder_hits)} 个占位符: {placeholder_hits[:3]}' if placeholder_hits else '无'))

    # 3. 空段数量
    empty_ps = re.findall(r'<p[^>]*>(?:\s|&nbsp;)*</p>', html)
    checks.append(('空段(p&nbsp;p)', True,
                   f'{len(empty_ps)} 个空段（spacer 正常）'))

    # 4. 超过 150 汉字的段落数量必须为 0
    # 提取所有 <p> <h2> <div> 之间的纯文本
    blocks = re.findall(r'<p[^>]*>(.*?)</p>|<h2[^>]*>(.*?)</h2>|<div[^>]*>(.*?)</div>', html)
    over150 = 0
    long_paras = []
    for match in blocks:
        text = next((t for t in match if t), '')
        cn = len(re.findall(r'[一-鿿]', text))
        if cn > 150:
            over150 += 1
            long_paras.append(f'{cn}字: {text[:40]}...')
    checks.append(('超150汉字段落', over150 == 0,
                   f'{over150} 段超150字: {long_paras[:3]}' if over150 > 0 else '无'))

    # 5. 正文图片数量必须等于计划数量
    imgs = re.findall(r'<img[^>]+src\s*=\s*"[^"]+"[^>]*>', html)
    actual_imgs = len(imgs)
    checks.append(('正文图片数', actual_imgs == expected_imgs,
                   f'实际 {actual_imgs} / 预期 {expected_imgs}'))

    # 6. 小标题数量必须在 4—7 个
    subheading_pattern = r'[一二三四五六七八九十]+、'
    subheadings = re.findall(subheading_pattern, html)
    sh_count = len(subheadings)
    checks.append(('小标题数(4-7)', 4 <= sh_count <= 7,
                   f'{sh_count} 个小标题'))

    # 7. 正文有效汉字数
    all_text = re.sub(r'<[^>]+>', '', html)
    total_cn = len(re.findall(r'[一-鿿]', all_text))
    checks.append(('有效汉字数', min_chars <= total_cn <= max_chars,
                   f'{total_cn} 汉字（目标 {min_chars}-{max_chars}）'))

    # 8. 禁止 h2 以外的块级标签
    for tag in ['section', 'blockquote', 'table', 'hr', 'h1', 'h3', 'h4', 'h5', 'h6']:
        if re.search(f'<{tag}[\\s>]', html, re.IGNORECASE):
            checks.append((f'禁止标签<{tag}>', False, f'发现 <{tag}> 标签'))
            break
    else:
        checks.append(('禁止块级标签', True, '无'))

    # 汇总
    failures = [c for c in checks if not c[1]]
    all_pass = len(failures) == 0

    return all_pass, checks


def main():
    parser = argparse.ArgumentParser(description='公众号 HTML 发布门禁')
    parser.add_argument('html', help='article_final.html 路径')
    parser.add_argument('--img-count', type=int, default=3, help='预期图片数')
    parser.add_argument('--min-chars', type=int, default=2400, help='最少汉字数')
    parser.add_argument('--max-chars', type=int, default=3000, help='最多汉字数')
    args = parser.parse_args()

    passed, checks = validate(args.html, args.img_count, args.min_chars, args.max_chars)

    print('=' * 60)
    print('  WeChat HTML Gate Check:', args.html)
    print('=' * 60)
    for name, ok, detail in checks:
        icon = 'PASS' if ok else 'FAIL'
        print(f'  [{icon:4s}] {name:20s} | {detail}')
    print('=' * 60)
    if passed:
        print('  结果: ALL PASS -- can enter editor')
    else:
        fails = sum(1 for c in checks if not c[1])
        print(f'  结果: {fails} FAIL(s) -- BLOCKED from editor')
    print('=' * 60)
    return 0 if passed else 1


if __name__ == '__main__':
    sys.exit(main())
