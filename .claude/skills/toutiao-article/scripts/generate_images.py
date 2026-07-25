"""
头条号自动发布 - Agens→sese-ai配图生成 (v8.0)
从正文提取3段场景prompt，调用Agens API生成图片。
Agens连续3次失败→自动走sese-ai回退。
服务配置来自 config/services.yaml，不硬编码。
"""
import requests, json, sys, os, time, base64
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from scripts.state import ensure_runtime_dirs
from scripts.lib.config_loader import get_services

TEMP_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "runtime", "images")

# 从 services.yaml 读取
_svcs = get_services()
AGENS_ENDPOINT = _svcs["agens"]["primary"]["endpoint"]
AGENS_MODEL = _svcs["agens"]["primary"]["model"]
AGENS_KEY = _svcs["agens"]["primary"]["key"]
SESE_ENDPOINT = _svcs["agens"]["fallback"]["endpoint"]
SESE_AUTH = _svcs["agens"]["fallback"]["auth_header"]
SESE_MODEL = _svcs["agens"]["fallback"]["model"]

MAX_AGENS_FAILURES = 3
RETRY_WAIT = 40
TIMEOUT = 120

def call_agens(prompt: str, index: int) -> dict:
    """Call Agens API, returns {ok, path, error}"""
    try:
        r = requests.post(AGENS_ENDPOINT,
            headers={
                "Authorization": f"Bearer {AGENS_KEY}",
                "Content-Type": "application/json"
            },
            json={"model": AGENS_MODEL, "prompt": prompt, "n": 1},
            timeout=TIMEOUT)
        data = r.json()
        if "data" in data and len(data["data"]) > 0:
            url = data["data"][0]["url"]
            img_r = requests.get(url, timeout=60)
            os.makedirs(TEMP_DIR, exist_ok=True)
            path = os.path.join(TEMP_DIR, f"agens_img{index}.png")
            with open(path, "wb") as f:
                f.write(img_r.content)
            return {"ok": True, "path": path, "url": url}
        else:
            return {"ok": False, "error": json.dumps(data), "attempt": "agens"}
    except Exception as e:
        return {"ok": False, "error": str(e), "attempt": "agens"}

def call_sese(prompt: str, index: int) -> dict:
    """Call sese-ai fallback API"""
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
            timeout=TIMEOUT)
        data = r.json()
        if "images" in data and len(data["images"]) > 0 and data["images"][0].get("ok"):
            b64_data = data["images"][0]["b64"]
            os.makedirs(TEMP_DIR, exist_ok=True)
            path = os.path.join(TEMP_DIR, f"agens_img{index}.png")
            with open(path, "wb") as f:
                f.write(base64.b64decode(b64_data))
            return {"ok": True, "path": path, "attempt": "sese"}
        else:
            return {"ok": False, "error": json.dumps(data), "attempt": "sese"}
    except Exception as e:
        return {"ok": False, "error": str(e), "attempt": "sese"}

def generate_one_image(prompt: str, index: int) -> dict:
    """Generate one image with Agens→sese fallback chain."""
    # Try Agens
    agens_failures = 0
    for attempt in range(1, MAX_AGENS_FAILURES + 2):
        result = call_agens(prompt, index)
        if result["ok"]:
            print(f"  Agens img{index} OK: {result['path']}")
            return result
        agens_failures += 1
        error = result.get("error", "unknown")
        is_server_error = any(x in error for x in ["503", "timeout", "500", "502", "504"])
        is_client_error = any(x in error for x in ["400", "rejected", "402"])
        if is_server_error and attempt <= MAX_AGENS_FAILURES:
            print(f"  Agens img{index} attempt {attempt} failed ({error}), retrying in {RETRY_WAIT}s...")
            time.sleep(RETRY_WAIT)
            continue
        if is_client_error and attempt == 1:
            # Simplify prompt and retry once
            short_prompt = prompt[:100]
            print(f"  Agens client error, retrying with short prompt...")
            result2 = call_agens(short_prompt, index)
            if result2["ok"]:
                return result2
        break  # Don't retry client errors more

    # Fallback to sese-ai
    print(f"  Agens failed after {agens_failures+1} attempts, falling back to sese-ai...")
    sese_result = call_sese(prompt, index)
    if sese_result["ok"]:
        print(f"  sese-ai img{index} OK: {sese_result['path']}")
    else:
        print(f"  sese-ai img{index} also failed: {sese_result.get('error')}")
    return sese_result


def main():
    """generate_images.py <prompts_json>
    prompts_json: ["prompt1", "prompt2", "prompt3"]
    """
    if len(sys.argv) < 2:
        data = json.loads(sys.stdin.read())
    else:
        with open(sys.argv[1], "r", encoding="utf-8") as f:
            data = json.load(f)

    if isinstance(data, list):
        prompts = data
    elif isinstance(data, dict):
        prompts = data.get("prompts", [])
    else:
        prompts = [data]

    ensure_runtime_dirs()
    results = []
    for i, prompt in enumerate(prompts):
        idx = i + 1
        print(f"Generating image {idx}/3...")
        r = generate_one_image(prompt, idx)
        results.append(r)

    # Summary
    successes = [r for r in results if r.get("ok")]
    failures = [r for r in results if not r.get("ok")]

    all_ok = len(successes) == len(prompts)
    output = {
        "total": len(prompts),
        "success": len(successes),
        "fail": len(failures),
        "results": results,
        "all_ok": all_ok,
    }
    print("\n=== RESULT ===")
    print(json.dumps(output, ensure_ascii=False, indent=2))
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
