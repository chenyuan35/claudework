#!/usr/bin/env python3
"""bake_wechat_html.py — 极简排版 v8.0

用法:
  python bake_wechat_html.py article.txt --cdn URL1 --cdn URL2 --cdn URL3
  python bake_wechat_html.py article.txt --cdn URL1 --cdn URL2 --cdn URL3 --auto-position

排版规范：
  正文 18px/2行高/黑色/左对齐/段距24px
  小标题 22px/蓝色/居中/上下32px，格式" 一、标题 "
  禁止大段文字、密集排版、连续空行、额外装饰

行内标记（写作时可直接嵌入段落）：
  **文本** / ==文本== / ++文本++  →  加粗
  !!文本!!                           →  红色强调
  ~~文本~~                           →  划线效果

输出: article_final.html

铁律: 仅 <div>+<p>+<img>；禁止 h2/section/blockquote/彩色盒子
v8.0 — 极简排版：18px/2行高/黑色左对齐, 小标题22px蓝居中
"""

import argparse, json, re, sys
from pathlib import Path


# ─── 行内标记渲染 ────────────────────────────────────────────

INLINE_MARKERS = [
    (r'\*\*([^*]+)\*\*', r'<strong>\1</strong>'),
    (r'==([^=]+)==', r'<strong>\1</strong>'),
    (r'\+\+([^+]+)\+\+', r'<strong>\1</strong>'),
    (r'!!([^!]+)!!', r'<span style="color:#c0392b;font-weight:700;">\1</span>'),
    (r'~~([^~]+)~~', r'<span style="text-decoration:line-through;color:#999;">\1</span>'),
]


def apply_inline_markers(text):
    result = text
    for pattern, replacement in INLINE_MARKERS:
        result = re.sub(pattern, replacement, result)
    return result


def html_escape(t):
    return t.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def split_blocks(body):
    """将正文拆分成句子级 block：每个完整句子一个 <div>。

    保护块（图片占位、子标题、分隔符）保持整行；
    正文按 。！？ 拆成句子。
    """
    body = body.replace('\r\n', '\n').replace('\r', '\n')
    blocks = []
    for line in body.splitlines():
        line = line.strip()
        if not line:
            continue
        if re.match(r'^@@IMG:inline\d+@@$', line) or \
           re.match(r'^[一二三四五六七八九十]+、', line) or \
           re.match(r'^[=\-*]{3,}$', line):
            blocks.append(line)
            continue
        blocks.extend(
            x.strip() for x in
            re.findall(r'.+?(?:[。！？][\'"]?|$)', line)
            if x.strip()
        )
    return blocks


def bake(text, cdn_urls, auto_position=False):
    """将源文本烘焙为微信兼容 HTML。

    统一排版规范：
      正文 18px/2行高/黑色/左对齐/段距24px
      小标题 22px/蓝色/居中/上下32px，格式" 一、标题 "
      禁止大段文字、密集排版、连续空行、额外装饰
    """

    # 替换图片占位符
    body = text
    for k, url in cdn_urls.items():
        body = body.replace(f'[插图：{k}.jpg 插入此处]', f'@@IMG:{k}@@')
        body = body.replace(f'[插图：{k} 插入此处]', f'@@IMG:{k}@@')

    blocks = split_blocks(body)

    # ─── 自动算图位置（基于 split_blocks 的句子级 block 统计）───
    if auto_position and cdn_urls:
        blocks = [b for b in blocks if not re.fullmatch(r'@@IMG:inline\d+@@', b)]

        text_pos = [
            i for i, b in enumerate(blocks)
            if not re.match(r'^[一二三四五六七八九十]+、', b)
            and not re.match(r'^[=\-*]{3,}$', b)
        ]

        total = len(text_pos)
        inserts = [
            (round(total * 0.82), 'inline3'),
            (round(total * 0.55), 'inline2'),
            (round(total * 0.25), 'inline1'),
        ]

        for target, key in inserts:
            if cdn_urls.get(key) and total:
                pos = text_pos[min(max(target - 1, 0), total - 1)] + 1
                blocks.insert(pos, f'@@IMG:{key}@@')
                text_pos = [i if i < pos else i + 1 for i in text_pos]

    parts = []
    para_idx = 0
    for raw in blocks:
        m = re.match(r'@@IMG:(inline\d+)@@', raw)
        if m:
            k = m.group(1)
            url = cdn_urls.get(k, '')
            if url:
                parts.append(
                    f'<p id="i{para_idx}" style="margin:28px 0;text-align:center;">'
                    f'<img src="{url}" style="width:100%;display:block;border-radius:2px;"></p>'
                )
                para_idx += 1
            continue
        if re.match(r'^[一二三四五六七八九十]+、', raw):
            # 小标题：22px 蓝色居中，格式 " 一、标题 "
            t = html_escape(raw.strip())
            parts.append(f'<p id="h{para_idx}" style="font-size:22px;font-weight:700;color:#1677ff;text-align:center;margin:32px 0;">{t}</p>')
            para_idx += 1
            continue
        if re.match(r'^[=\-*]{3,}$', raw):
            # 节分隔符—跳过，间距由小标题上下 margin 控制
            continue
        # 正文段落：18px/2行高/段距24px，交替 margin 写法防 ProseMirror 合并
        t = html_escape(raw)
        t = apply_inline_markers(t)
        parts.append(f'<p id="p{para_idx}" style="font-size:18px;line-height:2;margin:0 0 24px;">{t}</p>')
        para_idx += 1

    return '\n'.join(parts)


def parse_frontmatter(text):
    """解析 YAML 风格 frontmatter（---\nkey: value\n---）。"""
    m = re.match(r'^---\s*\n(.*?)\n---\s*\n(.*)', text, re.DOTALL)
    if not m:
        return {}, text
    meta = {}
    for line in m.group(1).splitlines():
        if ':' in line:
            k, v = line.split(':', 1)
            meta[k.strip()] = v.strip().strip('"').strip("'")
    return meta, m.group(2)


def main():
    parser = argparse.ArgumentParser(description='公众号文章烘焙器')
    parser.add_argument('input', nargs='?', help='源文件（wechat_article_xxx.txt）')
    parser.add_argument('--cdn', action='append', default=[], help='CDN URL（可传多次 --cdn URL）')
    parser.add_argument('--output', '-o', default='article_final.html', help='输出路径')
    parser.add_argument('--dry-run', action='store_true', help='只打印统计，不写文件')
    parser.add_argument('--auto-position', action='store_true',
                        help='自动算图：按25%/55%/82%均匀分布3张图片，忽略原文[插图]标记位置')

    args = parser.parse_args()

    # 输入
    if args.input:
        src = Path(args.input)
    else:
        candidates = sorted(Path.cwd().glob('wechat_article_*.txt'))
        src = candidates[-1] if candidates else None
        if not src:
            print('❌ 未找到输入文件')
            sys.exit(1)

    text = src.read_text(encoding='utf-8')

    # 尝试解析 frontmatter
    meta, body = parse_frontmatter(text)
    title = meta.get('title', '')

    # 标题单独取（首行不是 frontmatter 时）
    if not title:
        first_line = body.splitlines()[0] if body.splitlines() else ''
        if 4 <= len(first_line) <= 60:
            title = first_line
            body_lines = body.splitlines()
            if body_lines:
                body_lines = body_lines[1:]
            body = '\n'.join(body_lines).lstrip('\n')

    # 处理 CDN URL（不限数量）
    cdn = {}
    for i, url in enumerate(args.cdn):
        cdn[f'inline{i+1}'] = url

    # 烘焙
    html = bake(body, cdn, auto_position=args.auto_position)

    if args.dry_run:
        blocks = html.count('<div ') + html.count('<p ')
        imgs = html.count('<img ')
        spans = html.count('<span')
        print(f'标题: {title[:50]}' if title else '标题: (首行)')
        print(f'blocks: {blocks}')
        print(f'spans(行内标记): {spans}')
        print(f'imgs: {imgs}')
        print(f'大小: {len(html)} bytes')
        print(f'自动算图: {"是" if args.auto_position else "否"}')
        return

    Path(args.output).write_text(html, encoding='utf-8')
    block_count = html.count('<div ') + html.count('<p ')
    print(f'OK blocks={block_count} imgs={html.count("<img ")} spans={html.count("<span")} -> {args.output}')


if __name__ == '__main__':
    main()
