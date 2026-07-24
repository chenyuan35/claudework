"""
agnes_image.py — Agnes AI 免费生图 (agnes-image-2.1-flash) + sese-ai 回退

特性：
  - 主：Agnes APIHub（OpenAI 兼容 /v1/images/generations）
  - 回退：sese-ai（api.sese-ai.com），Agnes 失败时自动切换
  - 纯云端合成，不吃本地配置（适合烂电脑/1vCPU 服务器）
  - 支持文生图，韩漫/webtoon 风格可用
  - 两个 key 都硬编码在脚本中（不从 env/settings 读取，避免被覆盖）

用法：
  python generate.py --prompt "a cute cat" --out cat.png
  python generate.py --prompt "..." --model agnes-image-2.0-flash --size 768x1024
  python generate.py --prompt-file prompts.txt --out-dir ./imgs   # 每行一条
  python generate.py --prompt "..." --out cat.png --provider sese  # 强制用 sese-ai
"""

import argparse
import base64
import json
import os
import subprocess
import sys
import tempfile

API_URL = "https://apihub.agnes-ai.com/v1/images/generations"
MODELS = ["agnes-image-2.1-flash", "agnes-image-2.0-flash", "agnes-video-v2.0"]

# sese-ai 配置
SESE_API_URL = "https://api.sese-ai.com/api/generate"
SESE_API_KEY = "AADDCC001122"
SESE_MODEL = "z-image"  # 稳定模型（wai/Pony-3/R-1.5/Turbo-3.5 空响应）


def get_api_key() -> str:
    # 硬编码 key，不从 env/settings 读取（env 会被覆盖）
    HARDCODED_KEY = "sk-37fc8R90O1p5YQy7py4vQpmbWywfsnqg3qLJxxJg2cO8y3Ui"
    if HARDCODED_KEY:
        return HARDCODED_KEY
    # 兼容旧路径（理论上不会走到）
    key = os.environ.get("AGNES_API_KEY", "")
    if not key:
        try:
            p = os.path.expanduser("~/.claude/settings.json")
            env = json.load(open(p, encoding="utf-8")).get("env", {})
            key = env.get("AGNES_API_KEY", "")
        except Exception:
            pass
    return key


def parse_size(size: str) -> tuple:
    """'1024x1024' -> (1024, 1024)"""
    parts = size.lower().split("x")
    return int(parts[0]), int(parts[1])


def generate_sese(prompt: str, size: str = "1024x1024", model: str = SESE_MODEL) -> bytes:
    """调用 sese-ai，返回图片二进制（PNG/JPG）"""
    width, height = parse_size(size)

    # 有效 aspect_ratio 枚举（z-image 必须严格匹配）
    VALID_RATIOS = ["1:1", "4:3", "3:4", "3:2", "2:3", "16:9", "9:16"]
    # 用 1:1 兜底（封面反正会被掘金裁剪）
    aspect_ratio = "1:1"
    ratio_val = width / height if height > 0 else 1.0
    # 找最接近的
    candidates = []
    for r in VALID_RATIOS:
        a, b = r.split(":")
        target = float(a) / float(b)
        diff = abs(ratio_val - target)
        candidates.append((diff, r))
    candidates.sort()
    aspect_ratio = candidates[0][1]

    payload = {
        "model": model,
        "prompt": prompt,
        "aspect_ratio": aspect_ratio,
        "quality": "1k",
    }
    try:
        import requests
        r = requests.post(SESE_API_URL, headers={
            "Authorization": f"Bearer {SESE_API_KEY}",
            "Content-Type": "application/json",
        }, json=payload, timeout=300)
        if r.status_code != 200:
            raise RuntimeError(f"sese-ai HTTP {r.status_code}: {r.text[:300]}")
        data = r.json()
        img_bytes = _extract_sese_img(data)
        if img_bytes:
            return img_bytes
        # z-image 有时因坐标系对齐报错，降级到 1:1 重试
        if aspect_ratio != "1:1":
            payload["aspect_ratio"] = "1:1"
            r2 = requests.post(SESE_API_URL, headers={
                "Authorization": f"Bearer {SESE_API_KEY}",
                "Content-Type": "application/json",
            }, json=payload, timeout=300)
            if r2.status_code == 200:
                img_b2 = _extract_sese_img(r2.json())
                if img_b2:
                    return img_b2
        raise RuntimeError(f"sese-ai 图片生成失败: {img}")
    except Exception:
        pass

    # curl 兜底
    tmp = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
    json.dump(payload, tmp, ensure_ascii=False)
    tmp.close()
    out = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
    out.close()
    subprocess.run([
        "curl", "-s", "--max-time", "300", "-k",
        "-H", f"Authorization: Bearer {SESE_API_KEY}",
        "-H", "Content-Type: application/json",
        "-d", f"@{tmp.name}",
        "-o", out.name,
        SESE_API_URL,
    ], capture_output=True, text=True, check=True)
    data = json.load(open(out.name, encoding="utf-8"))
    os.unlink(tmp.name)
    os.unlink(out.name)
    img_bytes = _extract_sese_img(data)
    if img_bytes:
        return img_bytes
    # 降级到 1:1
    if payload.get("aspect_ratio") != "1:1":
        payload["aspect_ratio"] = "1:1"
        out2 = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
        out2.close()
        tmp2 = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
        json.dump(payload, tmp2, ensure_ascii=False)
        tmp2.close()
        subprocess.run([
            "curl", "-s", "--max-time", "300", "-k",
            "-H", f"Authorization: Bearer {SESE_API_KEY}",
            "-H", "Content-Type: application/json",
            "-d", f"@{tmp2.name}",
            "-o", out2.name,
            SESE_API_URL,
        ], capture_output=True, text=True, check=False)
        d2 = json.load(open(out2.name, encoding="utf-8"))
        os.unlink(tmp2.name)
        os.unlink(out2.name)
        img_b2 = _extract_sese_img(d2)
        if img_b2:
            return img_b2
    raise RuntimeError(f"sese-ai 图片生成失败: {data}")


def _extract_sese_img(data: dict) -> bytes | None:
    """sese-ai 返回格式不统一：成功时 {ok, b64}，失败时 {images: [...]}"""
    # 格式1：顶层 b64
    if data.get("ok") and data.get("b64"):
        return base64.b64decode(data["b64"])
    # 格式2：images 数组内
    if data.get("images"):
        for img in data["images"]:
            b64 = img.get("b64") or img.get("image") or ""
            if img.get("ok") and b64:
                return base64.b64decode(b64)
    return None


def generate(prompt: str, model: str = "agnes-image-2.1-flash",
             size: str = "1024x1024", api_key: str = None, provider: str = "agnes") -> str:
    """
    返回图片 URL（agnes）或 保存到临时文件返回路径（sese）。
    provider: 'agnes' | 'sese'
    """
    if provider == "sese":
        # 如果 model 是 agnes 的，转成 sese 的默认模型
        if model in MODELS:
            sese_model = SESE_MODEL
        else:
            sese_model = model
        img_bytes = generate_sese(prompt, size, sese_model)
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
        tmp.write(img_bytes)
        tmp.close()
        return tmp.name

    # agnes 主流程
    api_key = api_key or get_api_key()
    if not api_key:
        raise SystemExit("缺少 AGNES_API_KEY")
    payload = {"model": model, "prompt": prompt, "n": 1, "size": size}

    try:
        import requests
        r = requests.post(API_URL, headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }, json=payload, timeout=120)
        if r.status_code != 200:
            raise RuntimeError(f"HTTP {r.status_code}: {r.text[:300]}")
        return r.json()["data"][0]["url"]
    except ImportError:
        pass

    tmp = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
    json.dump(payload, tmp, ensure_ascii=False)
    tmp.close()
    out = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
    out.close()
    p = subprocess.run([
        "curl", "-s", "--max-time", "120", "-k",
        "-H", f"Authorization: Bearer {api_key}",
        "-H", "Content-Type: application/json",
        "-d", f"@{tmp.name}",
        "-o", out.name,
        API_URL,
    ], capture_output=True, text=True)
    data = json.load(open(out.name, encoding="utf-8"))
    os.unlink(tmp.name)
    os.unlink(out.name)
    return data["data"][0]["url"]


def download(url: str, dest: str):
    try:
        import requests
        r = requests.get(url, timeout=60)
        open(dest, "wb").write(r.content)
        return
    except ImportError:
        pass
    import subprocess
    subprocess.run(["curl", "-s", "--max-time", "60", "-k", "-o", dest, url], check=True)


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="Agnes AI 免费生图（sese-ai 回退）")
    ap.add_argument("--prompt", "-t")
    ap.add_argument("--prompt-file", "-f")
    ap.add_argument("--model", "-m", default="agnes-image-2.1-flash", choices=MODELS + [SESE_MODEL, "wai"])
    ap.add_argument("--size", "-s", default="1024x1024", help="如 1024x1024 / 768x1024")
    ap.add_argument("--out", "-o", default="output.png")
    ap.add_argument("--out-dir")
    ap.add_argument("--provider", "-p", default="agnes", choices=["agnes", "sese"], help="强制指定提供商（默认 agnes，失败自动回退 sese）")
    ap.add_argument("--fallback", action=argparse.BooleanOptionalAction, default=True, help="Agnes 失败时自动回退到 sese-ai")
    args = ap.parse_args()

    if args.prompt_file:
        prompts = [l.strip() for l in open(args.prompt_file, encoding="utf-8") if l.strip()]
    elif args.prompt:
        prompts = [args.prompt]
    else:
        ap.error("需提供 --prompt 或 --prompt-file")
        return

    if args.out_dir:
        os.makedirs(args.out_dir, exist_ok=True)

    for i, prompt in enumerate(prompts, 1):
        print(f"生成 [{i}/{len(prompts)}]: {prompt[:40]}...")
        dest = os.path.join(args.out_dir, f"{i:02d}.png") if args.out_dir else args.out

        # 主流程：agnes
        url_or_path = None
        used_provider = args.provider
        if args.provider == "agnes":
            try:
                url_or_path = generate(prompt, args.model, args.size, provider="agnes")
            except Exception as e:
                if args.fallback:
                    print(f"  ⚠️ Agnes 失败 ({e})，回退到 sese-ai...")
                    used_provider = "sese"
                else:
                    raise
        else:
            used_provider = "sese"

        # 回退：sese
        if used_provider == "sese" and url_or_path is None:
            url_or_path = generate(prompt, args.model, args.size, provider="sese")

        # 保存
        if used_provider == "agnes":
            download(url_or_path, dest)
        else:
            # sese 返回的是本地路径，直接复制
            import shutil
            shutil.copy(url_or_path, dest)
            os.unlink(url_or_path)

        print(f"  -> {dest} [{used_provider}]")


if __name__ == "__main__":
    main()
