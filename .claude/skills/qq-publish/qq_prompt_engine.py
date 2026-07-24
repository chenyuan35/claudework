#!/usr/bin/env python3
"""
qq_prompt_engine.py — 正文→scene_prompt 自动提取引擎
=====================================================
输入：3 个区块的 textSample（来自 SOP-IMG-01）
输出：3 条互不重复的 prompt + 去重审计报告

去重逻辑：
  1. 每次生成的 3 条 prompt 写入 .qq_prompt_history.json（保留最近 2 轮 = 6 条）
  2. 新 prompt 与历史逐一比对 SHA256
  3. 命中历史 → 随机变换 B风格/C光线/D氛围 重新生成，最多 3 次重试
  4. 3 次重试仍命中 → 使用强制变异模板
"""

import json, hashlib, random, os, re, sys
from pathlib import Path

HISTORY_FILE = Path(__file__).resolve().parent / '.qq_prompt_history.json'
HISTORY_MAX = 6  # 2轮 × 3图

# 风格组合（同 §6.2 提示词元素表）
STYLES = [
    'anime style, cel shaded',
    'photorealistic, hyper-detailed',
    'cinematic, film grain, anamorphic',
]
LIGHTS = [
    'dramatic neon backlight, blue and purple',
    'soft ambient light from monitor glow',
    'harsh contrast, shadows and highlights',
    'warm golden hour light from window',
]
MOODS = [
    'tense, competitive, high stakes atmosphere',
    'melancholic, reflective, quiet mood',
    'energetic, excited, vibrant vibe',
    'mysterious, suspenseful, player vs system',
]
QUALITY = '4K, highly detailed, masterpiece, sharp focus'


def load_history():
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE) as f:
                return json.load(f)
        except:
            pass
    return []


def save_history(history):
    # Keep only last HISTORY_MAX entries
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history[-HISTORY_MAX:], f, ensure_ascii=False, indent=2)


def extract_entities(text):
    """从正文提取 3 个核心描述短语。取前 3 个完整句子的关键名词短语。"""
    text = text.replace('\n', '')
    # Split by sentence endings
    parts = re.split(r'[。！？]', text)
    parts = [p.strip() for p in parts if len(p.strip()) > 8]

    if not parts:
        parts = [text[:50]]

    # Take first 3 sentences, extract meaningful ngrams
    samples = []
    for p in parts[:3]:
        # Extract gaming-related terms
        terms = re.findall(r'[一-鿿]{2,6}', p)
        samples.append(''.join(terms[:6]))

    entities = {
        'entities': [s for s in samples if s],
        'actions': samples[:2] if len(samples) >= 2 else samples,
        'emotions': samples[:2] if len(samples) >= 2 else ['深刻体验'],
    }
    # Fallback if everything fails
    if not entities['entities']:
        entities['entities'] = ['精彩游戏瞬间']
        entities['actions'] = ['精彩游戏瞬间']
    return entities


def build_prompt(entities, index, prev_style=None, prev_light=None, prev_mood=None):
    """组装一条 prompt，确保与上一张图的 B/C/D 至少 2 项不同。"""
    # Random style/light/mood with diversity constraint
    style = random.choice(STYLES)
    light = random.choice(LIGHTS)
    mood = random.choice(MOODS)

    if prev_style and prev_light and prev_mood:
        # Ensure at least 2 of 3 differ from previous
        for _ in range(10):
            diffs = (0 if style == prev_style else 1) + \
                    (0 if light == prev_light else 1) + \
                    (0 if mood == prev_mood else 1)
            if diffs >= 2:
                break
            style = random.choice(STYLES)
            light = random.choice(LIGHTS)
            mood = random.choice(MOODS)

    entity_part = '，'.join(entities['entities'][:3])
    action_part = '，'.join(entities['actions'][:2])
    emotion_part = '，'.join(entities['emotions'][:2])

    prompt = f"{entity_part}，{action_part}，{emotion_part}，{style}，{light}，{mood}，{QUALITY}"
    return prompt, style, light, mood


def sha256(s):
    return hashlib.sha256(s.encode('utf-8')).hexdigest()[:16]


def generate_unique_prompts(sections):
    """sections: [textSample1, textSample2, textSample3]"""
    history = load_history()
    prompts = []
    prev_style, prev_light, prev_mood = None, None, None

    for i, text in enumerate(sections[:3]):
        entities = extract_entities(text)

        # Try to build unique prompt (not in history)
        for attempt in range(5):
            prompt, style, light, mood = build_prompt(entities, i, prev_style, prev_light, prev_mood)
            h = sha256(prompt)
            if h not in history:
                break
            # Force different elements
            style = random.choice([s for s in STYLES if s != style] or STYLES)
            light = random.choice([l for l in LIGHTS if l != light] or LIGHTS)
            mood = random.choice([m for m in MOODS if m != mood] or MOODS)
            prompt = f"{'，'.join(entities['entities'][:3])}，{'，'.join(entities['actions'][:2])}，{'，'.join(entities['emotions'][:2])}，{style}，{light}，{mood}，{QUALITY}"
            h = sha256(prompt)
            if h not in history:
                break

        prompts.append(prompt)
        prev_style, prev_light, prev_mood = style, light, mood

    # Update history
    new_hashes = [sha256(p) for p in prompts]
    history.extend(new_hashes)
    save_history(history)

    return prompts


def main():
    if len(sys.argv) < 2:
        print('用法: python qq_prompt_engine.py "section1 text" "section2 text" "section3 text"')
        sys.exit(1)

    sections = sys.argv[1:4]
    if len(sections) < 3:
        print('需要 3 个区块正文，当前 {} 个'.format(len(sections)))
        sys.exit(1)

    prompts = generate_unique_prompts(sections)

    # Audit
    audit = {
        'prompts': prompts,
        'sha256': [sha256(p) for p in prompts],
        'allDifferent': len(set(sha256(p) for p in prompts)) == 3,
        'historyMatch': [sha256(p) for p in prompts if sha256(p) in load_history()],
    }

    print(json.dumps(audit, ensure_ascii=False, indent=2))

    # Also print just the prompts for piping
    for p in prompts:
        print(p)


if __name__ == '__main__':
    main()
