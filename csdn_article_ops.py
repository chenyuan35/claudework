"""
csdn_article_ops.py — CSDN 文章固定操作模块

固定接口：
- build_article_summary(article_html) → str
- extract_main_theme(article_html) → dict
- build_scene_prompt(theme) → str
- generate_article_image(article_html, output_path) → dict
- run_csdn_article_image_pipeline(article_html) → dict

每次调用独立，仅读取本次传入的 article_html。
禁止全局变量、禁止读取旧文件、禁止临场决策。
"""
import hashlib
import os
import re
import shutil
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_GEN_PATH = os.path.join(_HERE, '.claude', 'skills', 'agnes-image', 'scripts')
if os.path.isdir(_GEN_PATH) and _GEN_PATH not in sys.path:
    sys.path.insert(0, _GEN_PATH)

from generate import generate, download


# ═══════════════════════════════════════════════════════════════
# 摘要模块
# ═══════════════════════════════════════════════════════════════

def _extract_body_text(html: str) -> list:
    """提取正文为段落列表，每个段落保留结构"""
    text = re.sub(r'<pre>.*?</pre>', '', html, flags=re.DOTALL)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL)
    text = re.sub(r'</(h\d|p|div|li|tr)>', '\n', text)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'[ \t]+', ' ', text)
    return [l.strip() for l in text.split('\n') if l.strip()]


def _get_h3_texts(html: str) -> list:
    return [re.sub(r'<[^>]+>', '', h) for h in re.findall(r'<h3[^>]*>(.*?)</h3>', html, re.DOTALL)]


def build_article_summary(article_html: str) -> str:
    """
    仅读取本次正文，自动生成 200-300 字摘要。
    算法：导语 + 各 H3 核心句 + 结论句，去重（含前缀去重）。
    内部最多重算 3 次，仍异常时用确定性压缩。
    """
    for attempt in range(3):
        try:
            h3s = _get_h3_texts(article_html)
            lines = _extract_body_text(article_html)

            # 导语：第一段非 H3 长文本
            lead = ''
            for line in lines:
                if len(line) > 50 and not any(h in line for h in h3s):
                    lead = line
                    break

            # 各 H3 核心内容 - 取 H3 后第一个长句
            full_text = '\n'.join(lines)
            body_parts = []
            for h3 in h3s:
                idx = full_text.find(h3)
                if idx < 0:
                    continue
                after = full_text[idx + len(h3):]
                for nh in h3s:
                    if nh == h3:
                        continue
                    p2 = after.find(nh)
                    if 0 < p2 < len(after):
                        after = after[:p2]
                        break
                segs = [s.strip() for s in after.split('。') if len(s.strip()) > 30]
                if segs:
                    body_parts.append(segs[0] + '。')

            # 结论：最后一段非 H3 长文本
            conclusion = ''
            for line in reversed(lines):
                if len(line) > 40 and not any(h in line for h in h3s):
                    conclusion = line
                    break

            # 组合 + 前缀去重
            candidates = [lead] + body_parts[:3] + ([conclusion] if conclusion else [])
            unique = []
            for c in candidates:
                # 前缀去重：如果 c 的前 20 字已经在 unique 中出现过就跳过
                prefix = c[:20]
                if any(u.startswith(prefix) or prefix in u for u in unique):
                    continue
                if c not in unique:
                    unique.append(c)

            summary = '。'.join(unique)
            summary = re.sub(r'[。]{2,}', '。', summary)

            # 长度控制
            if len(summary) > 297:
                summary = summary[:297] + '...'
            elif len(summary) < 200:
                fallback = h3s[0]
                for h in h3s[1:]:
                    if len(fallback + '。' + h) < 280:
                        fallback += '。' + h
                summary = (fallback + '。' + lead)[:297]

            if 200 <= len(summary) <= 305:
                return summary
        except Exception:
            if attempt == 2:
                raise

    return (h3s[0] + '。本文详细分析了相关话题，涵盖多角度观点和数据对比。')[:297]


# ═══════════════════════════════════════════════════════════════
# 主题提取模块
# ═══════════════════════════════════════════════════════════════

def extract_main_theme(article_html: str) -> dict:
    """仅读取本次正文。返回 {title, subject, action, scene, objects, emotion, visual_style}"""
    h3s = _get_h3_texts(article_html)
    title = h3s[0] if h3s else ''
    text_clean = re.sub(r'<[^>]+>', ' ', article_html)
    text_clean = re.sub(r'\s+', ' ', text_clean)

    # 识别英文专名
    entities = []
    for m in re.finditer(r'\b[A-Z][a-zA-Z.]*(?:\s+[A-Z][a-zA-Z.]*){0,2}\b', text_clean[:800]):
        w = m.group().strip()
        if 3 < len(w) < 40 and w not in entities:
            entities.append(w)

    # 情绪
    emotion = '冷静专业'
    if any(kw in text_clean for kw in ['联名', '联合', '联盟', '公开信']):
        emotion = '兴奋惊喜'
    if any(kw in text_clean for kw in ['制裁', '限制', '风险', '禁止']):
        emotion = '危机警示'

    # 场景
    scene = 'AI 大模型产业'
    if '开源' in text_clean:
        scene = '开源 AI 生态与政策博弈'
    elif '芯片' in text_clean:
        scene = 'AI 芯片与算力基础设施'

    return {
        'title': title,
        'subject': entities[0] if entities else '科技公司',
        'action': '联合声明' if '联名' in text_clean else '发布报告',
        'scene': scene,
        'objects': entities[:5],
        'emotion': emotion,
        'visual_style': '科技插画风格'
    }


def build_scene_prompt(theme: dict) -> str:
    """固定顺序组装 prompt"""
    obj_str = ', '.join(theme['objects'][:3]) if theme['objects'] else 'technology elements'
    parts = [
        f"{theme['subject']} {theme['action']}",
        f"in {theme['scene']}",
        f"with {obj_str}",
        f"mood: {theme['emotion']}",
        f"style: {theme['visual_style']}",
        'cinematic composition, deep depth of field',
        'no text, no watermark, no logo, no typography'
    ]
    return ', '.join(p for p in parts if p)


# ═══════════════════════════════════════════════════════════════
# 图片生成模块
# ═══════════════════════════════════════════════════════════════

def generate_article_image(article_html: str, output_path: str = None) -> dict:
    """
    自动执行：extract_main_theme → build_scene_prompt → Agens 生图 → 验证。
    返回 {status, image_path, prompt_hash, image_hash, theme, width, height, file_size}
    """
    if output_path is None:
        output_path = '_csdn_body_image.jpg'

    # 删除旧文件确保新生成
    for old in [output_path]:
        if os.path.isfile(old):
            os.unlink(old)

    # 1-2. 主题 + prompt
    theme = extract_main_theme(article_html)
    prompt = build_scene_prompt(theme)
    prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()[:16]

    # 3. 生图
    try:
        url = generate(prompt, model='agnes-image-2.1-flash', size='1024x1024', provider='agnes')
        download(url, output_path)
    except Exception as e:
        print(f'  Agnes 失败: {e}, 回退 sese-ai...')
        from generate import generate as sese_gen
        path = sese_gen(prompt, model='agnes-image-2.1-flash', size='1024x1024', provider='sese')
        shutil.copy(path, output_path)
        os.unlink(path)

    # 4. 验证
    if not os.path.isfile(output_path):
        return {'status': 'FAIL', 'error': '图片文件未生成'}

    file_size = os.path.getsize(output_path)
    if file_size < 1000:
        os.unlink(output_path)
        return {'status': 'FAIL', 'error': f'图片过小: {file_size}'}

    with open(output_path, 'rb') as f:
        image_hash = hashlib.sha256(f.read()).hexdigest()[:16]

    from PIL import Image as PILImage
    try:
        img = PILImage.open(output_path)
        w, h = img.size
    except Exception:
        w, h = 0, 0

    return {
        'status': 'PASS',
        'image_path': output_path,
        'prompt_hash': prompt_hash,
        'image_hash': image_hash,
        'theme': theme,
        'width': w,
        'height': h,
        'file_size': file_size
    }


# ═══════════════════════════════════════════════════════════════
# 唯一入口
# ═══════════════════════════════════════════════════════════════

def run_csdn_article_image_pipeline(article_html: str) -> dict:
    """
    唯一入口。全程无人值守。
    1. 清理旧临时文件
    2. 提取主题 → 生成 prompt → Agens 生图
    3. 返回报告（浏览器上传由 csdn_single_image_ops.js 处理）
    返回 {status, prompt_hash, image_hash, image_path, width, height, theme_subject}
    """
    import glob
    for pattern in ['_csdn_body_image.jpg', '_csdn_prompt_*.json', '_csdn_temp_*']:
        for f in glob.glob(pattern):
            try:
                os.unlink(f)
            except Exception:
                pass

    result = generate_article_image(article_html, '_csdn_body_image.jpg')
    if result['status'] != 'PASS':
        return result

    return {
        'status': 'PASS',
        'prompt_hash': result['prompt_hash'],
        'image_hash': result['image_hash'],
        'image_path': result['image_path'],
        'width': result.get('width', 0),
        'height': result.get('height', 0),
        'theme_subject': result['theme']['subject']
    }
