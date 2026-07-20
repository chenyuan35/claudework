#!/usr/bin/env python3
"""bake_wechat_html.py — 谋生与人性 v6.5 多主题排版 + 行内标记 + 节分隔符

用法:
  # 默认主题 (warm-life / 生活感悟)
  python bake_wechat_html.py article.txt CDN1 CDN2 CDN3 [CDN4...]

  # 指定主题
  python bake_wechat_html.py article.txt CDN1 CDN2 CDN3 --theme clean-analysis

  # 列出可用主题
  python bake_wechat_html.py --list-themes

行内标记（写作时可直接嵌入段落）：
  **文本**    strong加粗（重点结论，一段最多1次）
  ==文本==    strong加粗（高价值结论，取代黄底）
  ++文本++    strong加粗（重要概念，取代蓝底）
  ~~文本~~    划线效果（反讽/否定）
  !!文本!!    红色强调（警告/反面案例）

节分隔符：
  单独一行 === 或 --- 或 *** → 渲染为 ··· 分隔 spacer

容器语法（独立段落）：
  【对话】      speaker: text → 对话气泡样式

输出: article_final.html

铁律: 仅 <p>+<img>+<span>；禁止 h2/section/blockquote/彩色盒子
v6.5 — 行内标记（==黄底 ++蓝底 !!红字 ~~划线）+ 节分隔符 + 对话容器
"""

import argparse, json, re, sys
from pathlib import Path


# ─── 主题定义 ────────────────────────────────────────────────
# 每个主题 = {P, H, Q, SP, IMG} = 不同 CSS style
# 改主题时必须同步改 SKILL.md §6.8.0 常量表

THEMES = {
    # 生活感悟（默认）
    'warm-life': {
        'P': 'font-size:16px;line-height:1.8;color:#3f3f3f;margin:0 0 14px;letter-spacing:0.3px;text-align:justify;',
        'P_ALT': 'font-size:16.1px;line-height:1.8;color:#3f3f3f;margin:0 0 14px;letter-spacing:0.3px;text-align:justify;',
    },
    # 冷静分析
    'clean-analysis': {
        'P': 'font-size:15.5px;line-height:1.8;color:#3a3f4b;margin:0 0 14px;letter-spacing:0.3px;text-align:justify;',
        'P_ALT': 'font-size:15.6px;line-height:1.8;color:#3a3f4b;margin:0 0 14px;letter-spacing:0.3px;text-align:justify;',
    },
    # 叙事人文
    'story-telling': {
        'P': 'font-size:16px;line-height:1.8;color:#3d3833;margin:0 0 14px;letter-spacing:0.4px;text-align:justify;',
        'P_ALT': 'font-size:16.1px;line-height:1.8;color:#3d3833;margin:0 0 14px;letter-spacing:0.4px;text-align:justify;',
    },
}

# ─── 行内标记渲染 ────────────────────────────────────────────

INLINE_MARKERS = [
    # (pattern, replacement) — 按序应用，注意先后
    # **bold** → <strong>（标准粗体，一段最多1次）
    (r'\*\*([^*]+)\*\*', r'<strong>\1</strong>'),
    # ==text== → <strong>（高价值结论，取消黄底改纯粗体）
    (r'==([^=]+)==', r'<strong>\1</strong>'),
    # ++text++ → <strong>（重要概念，取消蓝底改纯粗体）
    (r'\+\+([^+]+)\+\+', r'<strong>\1</strong>'),
    # !!text!! → 红色强调
    (r'!!([^!]+)!!', r'<span style="color:#c0392b;font-weight:700;">\1</span>'),
    # ~~text~~ → 划线
    (r'~~([^~]+)~~', r'<span style="text-decoration:line-through;color:#999;">\1</span>'),
]


def apply_inline_markers(text):
    """在 HTML 转义后的文本上应用行内标记。"""
    result = text
    for pattern, replacement in INLINE_MARKERS:
        result = re.sub(pattern, replacement, result)
    return result


def html_escape(t):
    return t.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def bake(text, cdn_urls, theme='warm-life'):
    """将源文本烘焙为微信兼容 HTML。"""
    s = THEMES.get(theme, THEMES['warm-life'])

    # 替换图片占位符
    body = text
    for k, url in cdn_urls.items():
        body = body.replace(f'[插图：{k}.jpg 插入此处]', f'@@IMG:{k}@@')
        body = body.replace(f'[插图：{k} 插入此处]', f'@@IMG:{k}@@')

    parts = []
    para_idx = 0  # counter for style alternation (prevents WeChat editor merging)
    for raw in [x.strip() for x in body.split('\n\n') if x.strip()]:
        m = re.match(r'@@IMG:(inline\d+)@@', raw)
        if m:
            k = m.group(1)
            url = cdn_urls.get(k, '')
            if not url:
                parts.append(f'<p style="color:#999;font-size:14px;text-align:center;">[图片 {k}]</p>')
                continue
            parts.append(
                f'<p style="margin:14px 0;text-align:center;">'
                f'<img src="{url}" style="width:100%;display:block;border-radius:2px;"></p>'
            )
            continue
        if raw.startswith('【金句】'):
            t = raw.replace('【金句】', '', 1).strip()
            t = html_escape(t)
            t = apply_inline_markers(t)
            parts.append(f'<p style="font-size:16px;line-height:1.8;color:#2c2c2c;font-weight:700;margin:18px 0 14px;text-align:justify;">{t}</p>')
            continue
        if re.match(r'^[一二三四五六七八九十]+、', raw):
            t = html_escape(raw)
            # subheading: p + strong instead of h2 (h2 gets stripped by editor)
            parts.append(f'<p style="font-size:18px;line-height:1.6;color:#222;font-weight:700;margin:28px 0 14px;"><strong>{t}</strong></p>')
            continue
        # 节分隔符 — 不输出任何内容（正文无点号/分隔段）
        if re.match(r'^[=\-*]{3,}$', raw):
            continue
        # 对话容器
        if raw.startswith('【对话】'):
            lines = raw.splitlines()
            for line in lines:
                line = line.strip()
                if not line or line == '【对话】':
                    continue
                if '：' in line:
                    speaker, _, content = line.partition('：')
                    cs = html_escape(content.strip())
                    parts.append(
                        f'<p style="margin:0.4em 16px;padding:6px 12px;font-size:15px;line-height:1.7;'
                        f'color:#3f3f3f;background:#f5f5f0;border-radius:6px;">'
                        f'<span style="font-weight:700;color:#8b6914;">{speaker}：</span>{cs}</p>'
                    )
            continue
        # 普通段落 - alternate P/P_ALT to prevent WeChat editor merging
        t = html_escape(raw)
        t = apply_inline_markers(t)
        if para_idx % 2 == 0:
            style = s.get('P', '')
        else:
            style = s.get('P_ALT', s.get('P', ''))
        parts.append(f'<p style="{style}">{t}</p>')
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
    parser.add_argument('cdn', nargs='*', help='CDN URL（最多 3 个，可省略做本地预览）')
    parser.add_argument('--theme', '-t', default='warm-life', choices=list(THEMES.keys()),
                        help=f'排版主题（默认 warm-life）')
    parser.add_argument('--list-themes', action='store_true', help='列出可用主题')
    parser.add_argument('--output', '-o', default='article_final.html', help='输出路径')
    parser.add_argument('--dry-run', action='store_true', help='只打印统计，不写文件')

    args = parser.parse_args()

    if args.list_themes:
        print('可用主题:')
        for k, v in THEMES.items():
            print(f'  {k:20s} {v["name"]}')
        return

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
    theme = meta.get('theme', args.theme)
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
    html = bake(body, cdn, theme)

    if args.dry_run:
        blocks = html.count('<p ')
        imgs = html.count('<img ')
        spans = html.count('<span')
        print(f'主题: {theme} ({THEMES[theme]["name"]})')
        print(f'标题: {title[:50]}' if title else '标题: (首行)')
        print(f'blocks: {blocks}')
        print(f'spans(行内标记): {spans}')
        print(f'imgs: {imgs}')
        print(f'大小: {len(html)} bytes')
        return

    Path(args.output).write_text(html, encoding='utf-8')
    block_count = html.count('<p ') + html.count('<h2 ')
    print(f'OK blocks={block_count} imgs={html.count("<img ")} spans={html.count("<span")} -> {args.output}')


if __name__ == '__main__':
    main()
