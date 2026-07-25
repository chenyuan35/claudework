"""
_csdn_gen_img.py — CSDN 封面+正文图生成

读取 _csdn_prompt_analysis.json，调用 agnes-image API 生成封面和正文两张图。
保存为 _csdn_cover.jpg 和 _csdn_body.jpg。

依赖：agnes-image 技能（.claude/skills/agnes-image/scripts/generate.py）
"""
import json
import os
import sys
import shutil

# 定位 agnes-image 脚本
_HERE = os.path.dirname(os.path.abspath(__file__))
_GEN_PATH = os.path.join(_HERE, '.claude', 'skills', 'agnes-image', 'scripts')
if os.path.isdir(_GEN_PATH) and _GEN_PATH not in sys.path:
    sys.path.insert(0, _GEN_PATH)

from generate import generate, download


def build_prompt(data: dict, mode: str) -> str:
    """根据分析字段构建生图 prompt"""
    if mode == 'cover':
        parts = [
            data.get('core_topic', ''),
            f"style: {data.get('style', '')}",
            f"color palette: {data.get('palette', '')}",
            f"composition: {data.get('composition', '')}",
            f"mood: {data.get('mood', '')}",
        ]
    else:
        parts = [
            data.get('paragraph_context', ''),
            f"concept: {data.get('concept_type', '')}",
            f"composition: {data.get('composition', '')}",
            f"style: {data.get('style', '')}",
            f"color palette: {data.get('palette', '')}",
            f"mood: {data.get('mood', '')}",
        ]
    return '. '.join(p for p in parts if p)


def generate_image(prompt: str, model: str, size: str, outfile: str):
    """生成一张图片，agnes 主流程 + sese-ai 回退"""
    try:
        url = generate(prompt, model=model, size=size, provider='agnes')
        download(url, outfile)
    except Exception as e:
        print(f"  ⚠️ Agnes 失败 ({e}), 回退 sese-ai...")
        from generate import generate as sese_gen
        path = sese_gen(prompt, model=model, size=size, provider='sese')
        shutil.copy(path, outfile)
        os.unlink(path)


def main():
    import argparse
    ap = argparse.ArgumentParser(description='CSDN 封面+正文图生成')
    ap.add_argument('--analysis', '-a', default='_csdn_prompt_analysis.json')
    args = ap.parse_args()

    with open(args.analysis, encoding='utf-8') as f:
        analysis = json.load(f)

    settings = analysis.get('image_settings', {})
    model = settings.get('model', 'agnes-image-2.1-flash')
    w = settings.get('width', 1024)
    h = settings.get('height', 1024)
    size = f"{w}x{h}"

    for mode, outfile in [('cover', '_csdn_cover.jpg'), ('body', '_csdn_body.jpg')]:
        data = analysis.get(mode, {})
        prompt = build_prompt(data, mode)
        print(f"生成 {mode} 图...")
        generate_image(prompt, model, size, outfile)
        print(f"  -> {outfile}")


if __name__ == '__main__':
    main()
