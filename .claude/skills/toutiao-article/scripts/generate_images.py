"""
头条号自动发布 - Agens→sese-ai配图生成 (v8.2)
- Agens: 180s 超时, 2次重试
- sese-ai: 240s 超时, 1次重试
- 每篇文章按标题hash隔离图片目录
- 自动从正文提取3组提示词
- 上传前校验图片与当前文章匹配
"""
import requests, json, sys, os, time, base64, re, hashlib, io
from PIL import Image, UnidentifiedImageError
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from scripts.state import ensure_runtime_dirs
from scripts.lib.config_loader import get_services, get_thresholds

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMAGES_ROOT = os.path.join(BASE_DIR, "runtime", "images")

_svcs = get_services()
AGENS_ENDPOINT = _svcs["agens"]["primary"]["endpoint"]
AGENS_MODEL = _svcs["agens"]["primary"]["model"]
AGENS_KEY = _svcs["agens"]["primary"]["key"]
SESE_ENDPOINT = _svcs["agens"]["fallback"]["endpoint"]
SESE_AUTH = _svcs["agens"]["fallback"]["auth_header"]
SESE_MODEL = _svcs["agens"]["fallback"]["model"]

_retry = get_thresholds()["retry"]
AGENS_TIMEOUT = _retry["agens_timeout_sec"]
SESE_TIMEOUT = _retry["sese_timeout_sec"]
DOWNLOAD_TIMEOUT = _retry["image_download_timeout_sec"]
AGENS_RETRIES = _retry["image_api_retries"]
SESE_RETRIES = _retry["image_fallback_retries"]
RETRY_WAIT = _retry["image_api_wait_sec"]


_article_cfg = get_thresholds()["article"]
MIN_IMAGE_WIDTH = _article_cfg["image_min_width"]
MIN_IMAGE_HEIGHT = _article_cfg["image_min_height"]


def _validated_image_bytes(raw: bytes) -> tuple[bool, str]:
    if not raw:
        return False, "empty_image_bytes"
    try:
        with Image.open(io.BytesIO(raw)) as image:
            image.verify()
        with Image.open(io.BytesIO(raw)) as image:
            width, height = image.size
        if width < MIN_IMAGE_WIDTH or height < MIN_IMAGE_HEIGHT:
            return False, f"image_too_small:{width}x{height}"
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        return False, f"invalid_image:{type(exc).__name__}"
    return True, "ok"


def _write_validated_image(raw: bytes, img_dir: str, index: int) -> dict:
    valid, detail = _validated_image_bytes(raw)
    if not valid:
        return {"ok": False, "error": detail}
    os.makedirs(img_dir, exist_ok=True)
    path = _image_path(img_dir, index)
    part = path + ".part"
    with open(part, "wb") as f:
        f.write(raw)
    os.replace(part, path)
    return {"ok": True, "path": path}


def article_dir(title: str) -> str:
    """每篇文章独立图片目录：runtime/images/{title_hash}/"""
    h = hashlib.md5(title.encode()).hexdigest()[:12]
    d = os.path.join(IMAGES_ROOT, h)
    os.makedirs(d, exist_ok=True)
    return d


def cleanup_old_articles(current_title: str):
    """清理当前文章工作目录中的旧图片（不上传前清掉已有文件），禁止删除其他文章hash目录"""
    current_h = hashlib.md5(current_title.encode()).hexdigest()[:12]
    img_dir = os.path.join(IMAGES_ROOT, current_h)
    if not os.path.isdir(img_dir):
        return
    for f in os.listdir(img_dir):
        fp = os.path.join(img_dir, f)
        try:
            if os.path.isfile(fp):
                os.remove(fp)
        except:
            pass


def cleanup_editor_images(page):
    """清空编辑器中的旧图片DIV"""
    import warnings
    try:
        page.evaluate("""() => {
            var pm = document.querySelector('.ProseMirror');
            if (!pm) return;
            var toRemove = [];
            for (var i = 0; i < pm.children.length; i++) {
                var c = pm.children[i];
                if (c.tagName !== 'P' && c.querySelector('img')) toRemove.push(c);
            }
            for (var r of toRemove) r.remove();
            pm.dispatchEvent(new Event('input', {bubbles: true}));
        }""")
    except:
        pass


def generate_prompts(title: str, html: str) -> list:
    """根据文章标题、小标题和正文自动生成3组英文图片提示词（写实摄影风）"""
    # 提取小标题：同时匹配 <h2>/<h3> 和 <p><strong>
    headings = re.findall(r'<h[23]>(.*?)</h[23]>', html, re.DOTALL)
    if not headings:
        headings = re.findall(r'<p><strong>([^<]+)</strong></p>', html)
    # 提取正文前几段
    paras = re.findall(r'<p>(.*?)</p>', html, re.DOTALL)

    prompts = []

    # Prompt 1: 标题场景 + 第一个小标题
    ctx1 = title[:60]
    if len(headings) > 1:
        ctx1 += " - " + headings[1][:40]
    prompts.append(
        f"Chinese realistic home scene photography: {ctx1}. "
        f"Real-life family setting, natural lighting, sharp focus, "
        f"authentic daily environment, photorealistic texture, "
        f"1:1 aspect ratio, documentary photography style."
    )

    # Prompt 2: 中间小标题场景
    mid_idx = len(headings) // 2
    ctx2 = headings[mid_idx][:60] if len(headings) > mid_idx else (paras[5][:60] if len(paras) > 5 else title[:60])
    prompts.append(
        f"Chinese realistic home photography: {ctx2}. "
        f"Everyday household scene, honest natural lighting, "
        f"fine details, real-life texture, warm ambient tone, "
        f"1:1 aspect ratio, documentary photo quality."
    )

    # Prompt 3: 结尾场景
    ctx3 = headings[-1][:60] if len(headings) > 1 else (paras[-3][:60] if len(paras) > 3 else title[:60])
    prompts.append(
        f"Chinese realistic interior photography: {ctx3}. "
        f"Authentic home environment, natural light, realistic texture, "
        f"candid daily moment, clean composition, "
        f"1:1 aspect ratio, photorealistic documentary style."
    )

    return prompts


def _image_path(img_dir: str, index: int) -> str:
    return os.path.join(img_dir, f"article_img{index}.png")


def _image_exists_in_dir(img_dir: str, index: int) -> bool:
    p = _image_path(img_dir, index)
    if not os.path.isfile(p) or os.path.getsize(p) <= 0:
        return False
    try:
        with open(p, "rb") as f:
            valid, _ = _validated_image_bytes(f.read())
        return valid
    except OSError:
        return False


def validate_image_ownership(img_dir: str, expected_title_hash: str) -> bool:
    """校验图片目录名与文章hash一致"""
    actual = os.path.basename(img_dir)
    return actual == expected_title_hash


def call_agens(prompt: str, img_dir: str, index: int) -> dict:
    try:
        r = requests.post(AGENS_ENDPOINT,
            headers={
                "Authorization": f"Bearer {AGENS_KEY}",
                "Content-Type": "application/json"
            },
            json={"model": AGENS_MODEL, "prompt": prompt, "n": 1},
            timeout=AGENS_TIMEOUT)
        data = r.json()
        if "data" in data and len(data["data"]) > 0:
            url = data["data"][0].get("url")
            if not url:
                return {"ok": False, "error": "no_url_in_response", "attempt": "agens"}
            img_r = requests.get(url, timeout=DOWNLOAD_TIMEOUT)
            img_r.raise_for_status()
            content_type = img_r.headers.get("Content-Type", "").lower()
            if not content_type.startswith("image/"):
                return {"ok": False, "error": f"invalid_content_type:{content_type}", "attempt": "agens"}
            saved = _write_validated_image(img_r.content, img_dir, index)
            if not saved["ok"]:
                return {**saved, "attempt": "agens"}
            return {**saved, "url": url, "attempt": "agens"}
        else:
            return {"ok": False, "error": json.dumps(data, ensure_ascii=False)[:300], "attempt": "agens"}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}", "attempt": "agens"}


def call_sese(prompt: str, img_dir: str, index: int) -> dict:
    try:
        r = requests.post(SESE_ENDPOINT,
            headers={
                "Authorization": SESE_AUTH,
                "Content-Type": "application/json"
            },
            json={
                "model": SESE_MODEL,
                "prompt": prompt,
                "aspect_ratio": "1:1",
                "quality": "1k"
            },
            timeout=SESE_TIMEOUT)
        data = r.json()
        if "images" in data and len(data["images"]) > 0 and data["images"][0].get("ok"):
            b64_data = data["images"][0]["b64"]
            raw = base64.b64decode(b64_data, validate=True)
            saved = _write_validated_image(raw, img_dir, index)
            if not saved["ok"]:
                return {**saved, "attempt": "sese"}
            return {**saved, "attempt": "sese"}
        else:
            return {"ok": False, "error": json.dumps(data, ensure_ascii=False)[:300], "attempt": "sese"}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}", "attempt": "sese"}


def generate_one_image(prompt: str, img_dir: str, index: int) -> dict:
    """每张图独立重试：Agens × 2 → sese × 1"""
    if _image_exists_in_dir(img_dir, index):
        print(f"  img{index} 已存在，跳过 ({_image_path(img_dir, index)})")
        return {"ok": True, "path": _image_path(img_dir, index), "skipped": True}

    for attempt in range(1, AGENS_RETRIES + 2):
        result = call_agens(prompt, img_dir, index)
        if result["ok"]:
            print(f"  Agens img{index} attempt {attempt} OK")
            return result
        error = result.get("error", "unknown")
        is_retryable = any(x in error.lower() for x in ["503", "timeout", "500", "502", "504", "readtimeout", "connection"])
        print(f"  Agens img{index} attempt {attempt} failed: {error}")
        if is_retryable and attempt <= AGENS_RETRIES:
            print(f"    retrying in {RETRY_WAIT}s...")
            time.sleep(RETRY_WAIT)
        else:
            break

    print(f"  Agens img{index} exhausted, falling back to sese-ai...")
    for attempt in range(1, SESE_RETRIES + 2):
        sese_result = call_sese(prompt, img_dir, index)
        if sese_result["ok"]:
            print(f"  sese-ai img{index} attempt {attempt} OK")
            return sese_result
        error = sese_result.get("error", "unknown")
        is_retryable = any(x in error.lower() for x in ["503", "timeout", "500", "502", "504", "readtimeout", "connection", "524"])
        print(f"  sese-ai img{index} attempt {attempt} failed: {error}")
        if is_retryable and attempt <= SESE_RETRIES:
            print(f"    retrying in {RETRY_WAIT}s...")
            time.sleep(RETRY_WAIT)
        else:
            break

    return {"ok": False, "error": f"all providers exhausted for img{index}", "attempt": "both"}


def main():
    """generate_images.py [prompts_file | stdin]
    输入JSON格式:
      {"prompts": [...]} 或
      {"title": "...", "html": "..."} (自动提取prompts)
    """
    if len(sys.argv) < 2:
        data = json.loads(sys.stdin.read())
    else:
        with open(sys.argv[1], "r", encoding="utf-8") as f:
            data = json.load(f)

    title = data.get("title", "article")
    html = data.get("html", "")

    # 从输入提取prompts，或从正文自动生成
    prompts = data.get("prompts", [])
    if not prompts and html:
        prompts = generate_prompts(title, html)
        print(f"Auto-generated {len(prompts)} prompts from article content")
    elif not prompts:
        prompts = [title]

    # 每篇文章独立目录
    ensure_runtime_dirs()
    img_dir = article_dir(title)

    # 保留同一标题已成功图片，generate_one_image 会逐张校验并跳过
    results = []
    for i, prompt in enumerate(prompts):
        idx = i + 1
        print(f"Generating image {idx}/{len(prompts)}...")
        r = generate_one_image(prompt, img_dir, idx)
        results.append(r)

    successes = [r for r in results if r.get("ok")]
    failures = [r for r in results if not r.get("ok")]

    all_ok = len(successes) == len(prompts)
    output = {
        "total": len(prompts),
        "success": len(successes),
        "fail": len(failures),
        "results": results,
        "all_ok": all_ok,
        "image_dir": img_dir,
        "title_hash": hashlib.md5(title.encode()).hexdigest()[:12],
    }
    print("\n=== RESULT ===")
    print(json.dumps(output, ensure_ascii=False, indent=2))
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
