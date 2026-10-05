#!/usr/bin/env python3
"""auto_gen_images.py — 从正文小节提取具体场景并生成本篇专属配图

用法:
  python auto_gen_images.py wechat_article_midlife_couple.txt
  python auto_gen_images.py wechat_article_midlife_couple.txt --style "warm daily life"

流程:
  1. 读文章 → 查找 [插图：inlineN.jpg 插入此处] 标记
  2. 对每个标记，锁定所在小节并选择最具象的场景段落
  3. 组装含章节、人物、地点、动作的 prompt → 调 Agnes 生图
  4. 四张图写入指定暂存目录，并生成文章指纹清单
"""

import hashlib, json, os, re, sys, requests
from datetime import datetime
from pathlib import Path

# Agnes API（硬编码，不从 env 读）
API_KEY = 'sk-37fc8R90O1p5YQy7py4vQpmbWywfsnqg3qLJxxJg2cO8y3Ui'
BASE_URL = 'https://apihub.agnes-ai.com/v1'
MODEL = 'agnes-image-2.1-flash'
LOG_PATH = None
SHOT_TYPES = {
    1: 'wide environmental documentary shot',
    2: 'medium interaction documentary shot',
    3: 'close observational documentary shot with visible human action',
}



def clean_text(value):
    value = re.sub(r'【金句】', '', value)
    value = re.sub(r'\[插图：[^\]]+\]', '', value)
    value = re.sub(r'^=+$', '', value, flags=re.MULTILINE)
    return re.sub(r'\s+', ' ', value).strip()


def split_ratio_blocks(text):
    """按 bake_wechat_html.py 的正文句子块口径生成带小节归属的文本块。"""
    lines = text.replace('\r\n', '\n').replace('\r', '\n').splitlines()
    title = clean_text(lines[0]) if lines else ''
    current_section = title
    blocks = []
    for line_number, raw in enumerate(lines):
        line = raw.strip()
        if not line or line_number == 0:
            continue
        if re.match(r'^[一二三四五六七八九十]+、', line):
            current_section = clean_text(line)
            continue
        if re.match(r'^[=\-*]{3,}$', line) or re.match(r'^\[插图：inline\d+(?:\.jpg)? 插入此处\]$', line):
            continue
        sentences = [
            clean_text(item) for item in re.findall(r'.+?(?:[。！？][\'\"]?|$)', line)
            if clean_text(item)
        ]
        for sentence in sentences:
            if re.search(r'[一-鿿豈-﫿]', sentence):
                blocks.append({'section_title': current_section, 'text': sentence})
    if len(blocks) < 3:
        raise ValueError(f'正文有效句子块不足 3 个，当前 {len(blocks)} 个')
    return blocks


def extract_ratio_contexts(text):
    """以正文 25%/50%/75% 为锚点，在上下 5% 内落到最近的有效句子块。"""
    blocks = split_ratio_blocks(text)
    contexts = []
    total = len(blocks)
    for ratio in (0.25, 0.50, 0.75):
        anchor_index = min(max(round(total * ratio) - 1, 0), total - 1)
        radius = max(1, round(total * 0.05))
        candidates = range(max(0, anchor_index - radius), min(total, anchor_index + radius + 1))
        target_index = next(
            (i for i in sorted(candidates, key=lambda i: abs(i - anchor_index))
             if len(re.findall(r'[一-鿿]', blocks[i]['text'])) >= 18),
            anchor_index,
        )
        target = blocks[target_index]
        nearby = []
        for index in range(max(0, target_index - 1), min(total, target_index + 2)):
            item = blocks[index]
            if item['section_title'] == target['section_title']:
                nearby.append(item['text'])
        scene = ' '.join(nearby).strip()
        if len(scene) > 260:
            scene = scene[:260].rstrip('，。；：') + '。'
        contexts.append({
            'ratio': ratio,
            'actual_ratio': (target_index + 1) / total,
            'block_index': target_index,
            'block_total': total,
            'section_title': target['section_title'],
            'scene': scene,
        })
    return contexts


def build_prompt(context, image_index, style=""):
    """正文场景是主约束；统一风格只控制质感，不替换人物与情境。"""
    visual_style = style or (
        'restrained realistic editorial photography, natural available light, '
        'authentic contemporary Chinese environment, documentary color'
    )
    shot = SHOT_TYPES[image_index]
    return (
        f'{visual_style}, {shot}. Illustrate this exact article section: '
        f'"{context["section_title"]}". Concrete scene: {context["scene"]}. '
        'Show the stated people, place, action and relevant objects. Infer age only from the '
        'roles and facts in this scene; do not default to middle-aged subjects. One coherent '
        'moment, natural expressions, no posed stock-photo look, no text, no letters, no '
        'watermark, no logo; any screens, signs or papers must be blank or out of focus, high detail.'
    )


def generate_image(prompt, output_path, size='1080x1080'):
    """调用 Agnes API 生图。"""
    from openai import OpenAI
    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
    resp = client.images.generate(model=MODEL, prompt=prompt, n=1, size=size)
    url = resp.data[0].url
    r = requests.get(url, timeout=90)
    r.raise_for_status()
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(r.content)
    print(f'  Saved: {output_path} ({len(r.content)} bytes)')
    return url


def file_sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def log_line(message):
    if LOG_PATH is None:
        return
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with LOG_PATH.open('a', encoding='utf-8') as handle:
        handle.write(f'[{stamp}] {message}\n')


def main():
    import argparse
    parser = argparse.ArgumentParser(description='自动配图生成')
    parser.add_argument('article', nargs='?', help='文章文件')
    parser.add_argument('--style', default='', help='覆盖视觉风格描述')
    parser.add_argument('--dry-run', action='store_true', help='只打印 prompt 不生成')
    parser.add_argument('--out-dir', default='.', help='四张图和清单的输出目录')
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
    article_sha = hashlib.sha256(text.encode('utf-8')).hexdigest()
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    global LOG_PATH
    LOG_PATH = path.parent / 'logs' / 'wechat_img_gen.log'

    # 与 bake_wechat_html.py --auto-position 使用同一组句子块比例，不依赖人工插图标记。
    ratio_contexts = extract_ratio_contexts(text)
    print('以正文 25% / 50% / 75% 为锚点，在上下 5% 内提取 3 个配图场景:')
    log_line(f'START article={path.resolve()} sha256={article_sha} dry_run={args.dry_run}')
    manifest_images = []
    failures = []

    for image_index, context in enumerate(ratio_contexts, 1):
        fname = f'inline{image_index}.jpg'
        prompt = build_prompt(context, image_index, args.style)
        print(f'\n  [{fname}]')
        print(f'  锚点: {int(context["ratio"] * 100)}%，实际: {context["actual_ratio"]:.1%} '
              f'({context["block_index"] + 1}/{context["block_total"]})')
        print(f'  章节: {context["section_title"]}')
        print(f'  场景: {context["scene"]}')
        print(f'  Prompt: {prompt}')
        log_line(
            f'PLAN file={fname} section={context["section_title"]} '
            f'scene={context["scene"]} prompt={prompt}'
        )

        if args.dry_run:
            continue

        # 生成
        try:
            output_path = out_dir / fname
            generate_image(prompt, output_path)
            manifest_images.append({
                'file': fname,
                'role': f'inline{image_index}',
                'section_title': context['section_title'],
                'scene': context['scene'],
                'ratio': context['ratio'],
                'actual_ratio': context['actual_ratio'],
                'block_index': context['block_index'],
                'block_total': context['block_total'],
                'prompt': prompt,
                'sha256': file_sha256(output_path),
                'bytes': output_path.stat().st_size,
            })
        except Exception as e:
            print(f'  ❌ 失败: {e}')
            failures.append(f'{fname}: {e}')

    # 封面与正文图必须在同一次任务中完整产出，供状态机统一验收。
    title = text.splitlines()[0].strip()
    cover_context = ratio_contexts[0]
    cover_prompt = (
        'restrained realistic editorial cover photography for a Chinese WeChat article. '
        f'Article title: {title}. Central concrete scene: {cover_context["scene"]}. '
        'Show the people, setting, action and objects stated by the article. Infer ages only from '
        'the roles and facts; do not default to middle-aged subjects. Strong single focal moment, '
        'natural light, authentic contemporary Chinese environment, no text, no letters, no '
        'watermark, no logo; any screens, signs or papers must be blank or out of focus, high detail.'
    )
    print('\n  [cover.jpg]')
    print(f'  场景: {cover_context["scene"]}')
    print(f'  Prompt: {cover_prompt}')
    log_line(f'PLAN file=cover.jpg section=封面 scene={cover_context["scene"]} prompt={cover_prompt}')
    if not args.dry_run:
        try:
            cover_path = out_dir / 'cover.jpg'
            generate_image(cover_prompt, cover_path)
            manifest_images.append({
                'file': 'cover.jpg',
                'role': 'cover',
                'section_title': '封面',
                'scene': cover_context['scene'],
                'prompt': cover_prompt,
                'sha256': file_sha256(cover_path),
                'bytes': cover_path.stat().st_size,
            })
        except Exception as e:
            print(f'  ❌ 失败: {e}')
            failures.append(f'cover.jpg: {e}')

    if failures:
        for failure in failures:
            log_line(f'FAIL {failure}')
        print(f'\n❌ 生图失败 {len(failures)} 项')
        sys.exit(1)

    if not args.dry_run:
        manifest = {
            'version': 1,
            'article_file': str(path.resolve()),
            'article_sha256': article_sha,
            'generated_at': datetime.now().isoformat(),
            'images': manifest_images,
        }
        manifest_path = out_dir / 'image_manifest.json'
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
        log_line(f'PASS manifest={manifest_path} images={len(manifest_images)}')

    print('\n完成')


if __name__ == '__main__':
    main()
