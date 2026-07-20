#!/usr/bin/env python3
"""auto_gen_images.py — 自动从文章小节提取场景 + 生成配图

用法:
  python auto_gen_images.py wechat_article_midlife_couple.txt
  python auto_gen_images.py wechat_article_midlife_couple.txt --style "warm daily life"

流程:
  1. 读文章 → 查找 [插图：inlineN.jpg 插入此处] 标记
  2. 对每个标记，往上看最近的段落文本（含小标题）
  3. 组装为英文 prompt → 调 Agnes 生图
  4. 保存为 inlineN.jpg
"""

import os, re, sys, requests
from pathlib import Path

# Agnes API（硬编码，不从 env 读）
API_KEY = 'sk-37fc8R90O1p5YQy7py4vQpmbWywfsnqg3qLJxxJg2cO8y3Ui'
BASE_URL = 'https://apihub.agnes-ai.com/v1'
MODEL = 'agnes-image-2.1-flash'


def extract_prompt_context(text, marker_pos, lookback_chars=300):
    """从 marker 位置往前找文本，提取场景上下文。"""
    # 从 marker 往前找最近的非空段落
    before = text[max(0, marker_pos - lookback_chars):marker_pos]
    # 取最后一个完整的句子群
    paragraphs = [p.strip() for p in before.split('\n\n') if p.strip()]
    if paragraphs:
        context = paragraphs[-1]  # 最近的一段
        if len(context) < 15 and len(paragraphs) > 1:
            context = paragraphs[-2] + ' ' + paragraphs[-1]
    else:
        context = before.strip()

    # 清理标记
    context = re.sub(r'【金句】', '', context)
    context = re.sub(r'\[插图：[^\]]+\]', '', context)
    context = context.strip()
    # 截断
    if len(context) > 200:
        context = context[:200] + '。'
    return context


def chinese_to_english_prompt(chinese_text, style=""):
    """将中文场景文本转为英文 prompt。"""
    # 提取关键词
    # 简单地包裹中文文本在英文场景描述中
    base_style = "warm realistic photography style, everyday life scene, middle-aged Chinese people, natural lighting, soft warm tones, cinematic composition"
    if style:
        base_style = style

    # 限制中文文本长度
    if len(chinese_text) > 120:
        chinese_text = chinese_text[:120]

    prompt = f"{base_style}, scene depicting: {chinese_text}, no text, no watermark, no logo, high quality, 4k"
    return prompt


def generate_image(prompt, output_path, size='1080x1080'):
    """调用 Agnes API 生图。"""
    from openai import OpenAI
    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
    resp = client.images.generate(model=MODEL, prompt=prompt, n=1, size=size)
    url = resp.data[0].url
    r = requests.get(url)
    Path(output_path).write_bytes(r.content)
    print(f'  Saved: {output_path} ({len(r.content)} bytes)')
    return url


def main():
    import argparse
    parser = argparse.ArgumentParser(description='自动配图生成')
    parser.add_argument('article', nargs='?', help='文章文件')
    parser.add_argument('--style', default='', help='覆盖视觉风格描述')
    parser.add_argument('--dry-run', action='store_true', help='只打印 prompt 不生成')
    args = parser.parse_args()

    # 找文章文件
    if args.article:
        path = Path(args.article)
    else:
        candidates = sorted(Path.cwd().glob('wechat_article_*.txt'))
        path = candidates[-1] if candidates else None
    if not path or not path.exists():
        print('❌ 未找到文章文件')
        sys.exit(1)

    text = path.read_text(encoding='utf-8')

    # 查找所有配图标记
    markers = list(re.finditer(r'\[插图：(inline\d+\.jpg) 插入此处\]', text))
    if not markers:
        # 也匹配无后缀格式
        markers = list(re.finditer(r'\[插图：(inline\d+) 插入此处\]', text))
        if markers:
            # 补全 .jpg
            for m in markers:
                pass  # 后面统一处理

    if not markers:
        print('❌ 未找到 [插图：inlineN.jpg 插入此处] 标记')
        sys.exit(1)

    print(f'找到 {len(markers)} 个配图标记:')

    for m in markers:
        fname = m.group(1)
        if not fname.endswith('.jpg'):
            fname += '.jpg'
        pos = m.start()

        # 提取上下文
        ctx = extract_prompt_context(text, pos)
        prompt = chinese_to_english_prompt(ctx, args.style)
        print(f'\n  [{fname}]')
        print(f'  上下文: {ctx[:80]}...')
        print(f'  Prompt: {prompt[:120]}...')

        if args.dry_run:
            continue

        # 生成
        try:
            generate_image(prompt, fname)
        except Exception as e:
            print(f'  ❌ 失败: {e}')

    print('\n✅ 完成')


if __name__ == '__main__':
    main()
