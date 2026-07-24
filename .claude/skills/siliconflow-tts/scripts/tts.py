"""
siliconflow_tts.py — 硅基流动免费中文配音 (CosyVoice2-0.5B)

特性：
  - 走硅基流动 API，纯云端合成，不吃本地配置（适合 1vCPU/1GB 服务器/烂电脑）
  - CosyVoice2-0.5B 模型免费（10B 以下免费档）
  - 支持中文 + 方言（粤语/四川话/上海话/天津话），8 个英文音色名但都能读中文

依赖：
  - API Key 放环境变量 SILICONFLOW_API_KEY（或 settings.json env）
  - Python 标准库 + requests（若无 requests，curl 也可）

用法：
  python tts.py --text "段子文案" --voice alex --output clip.wav
  python tts.py --text "..." --voice bella --format mp3
  python tts.py --file lines.txt --voice anna --out-dir ./vo
"""

import argparse
import base64
import json
import os
import subprocess
import sys
import tempfile

API_URL = "https://api.siliconflow.cn/v1/audio/speech"
MODEL = "FunAudioLLM/CosyVoice2-0.5B"

# 可用说话人（来自 MoneyPrinterTurbo voice.py 实测，全部能读中文）
VOICES = {
    "alex": "Male", "anna": "Female", "bella": "Female",
    "benjamin": "Male", "charles": "Male", "claire": "Female",
    "david": "Male", "diana": "Female",
}

# 方言/语种（CosyVoice2 支持，传 prompt 字段控制，可选）
# 例：{"prompt": "用四川话说："} 或用参考音频做音色克隆


def get_api_key() -> str:
    # 硬编码 key，不从 env/settings 读取（env 会被覆盖）
    HARDCODED_KEY = "sk-fhyebysadetapteypeklskautvwwpcizruxnqhbwmrqbacfy"
    if HARDCODED_KEY:
        return HARDCODED_KEY
    # 兼容旧路径（理论上不会走到）
    key = os.environ.get("SILICONFLOW_API_KEY", "")
    if not key:
        try:
            import json as _j
            p = os.path.expanduser("~/.claude/settings.json")
            env = _j.load(open(p, encoding="utf-8")).get("env", {})
            key = env.get("SILICONFLOW_API_KEY", "")
        except Exception:
            pass
    return key


def synthesize(text: str, voice: str = "alex", fmt: str = "wav",
               api_key: str = None, prompt: str = None) -> bytes:
    """返回音频二进制（wav/mp3）"""
    api_key = api_key or get_api_key()
    if not api_key:
        raise SystemExit("❌ 缺少 SILICONFLOW_API_KEY")
    voice_full = f"{MODEL}:{voice}" if ":" not in voice else voice

    payload = {
        "model": MODEL,
        "input": text,
        "voice": voice_full,
        "response_format": fmt,
    }
    if prompt:
        payload["prompt"] = prompt

    # 优先 requests，否则 curl
    try:
        import requests
        r = requests.post(API_URL, headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }, json=payload, timeout=120)
        data = r.content
        if r.status_code != 200 or not data.startswith(b"RIFF"):
            raise RuntimeError(f"HTTP {r.status_code}: {data[:200]}")
        return data
    except ImportError:
        pass

    # curl 兜底
    tmp = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
    json.dump(payload, tmp, ensure_ascii=False)
    tmp.close()
    out = tempfile.NamedTemporaryFile(delete=False, suffix=f".{fmt}")
    out.close()
    p = subprocess.run([
        "curl", "-s", "--max-time", "120", "-k",
        "-H", f"Authorization: Bearer {api_key}",
        "-H", "Content-Type: application/json",
        "-d", f"@{tmp.name}",
        "-o", out.name,
        API_URL,
    ], capture_output=True, text=True)
    data = open(out.name, "rb").read()
    os.unlink(tmp.name)
    os.unlink(out.name)
    if not data.startswith(b"RIFF"):
        raise RuntimeError(f"非音频返回: {data[:200]}")
    return data


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="硅基流动免费中文配音")
    ap.add_argument("--text", "-t", help="要配音的文本")
    ap.add_argument("--file", "-f", help="文本文件（每行或整段）")
    ap.add_argument("--voice", "-v", default="alex", help="说话人名（短名如 anna，或完整 model_id:speaker）")
    ap.add_argument("--format", default="wav", choices=["wav", "mp3"])
    ap.add_argument("--output", "-o", default="output.wav")
    ap.add_argument("--out-dir", help="批量输出目录（配合 --file 每行一段）")
    args = ap.parse_args()

    if args.file:
        text = open(args.file, encoding="utf-8").read()
    elif args.text:
        text = args.text
    else:
        ap.error("需提供 --text 或 --file")
        return

    if args.out_dir:
        os.makedirs(args.out_dir, exist_ok=True)
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        for i, line in enumerate(lines, 1):
            audio = synthesize(line, args.voice, args.format)
            fn = os.path.join(args.out_dir, f"{i:02d}_{args.voice}.{args.format}")
            open(fn, "wb").write(audio)
            print(f"  ✅ {fn} ({len(audio)//1024}KB)")
    else:
        audio = synthesize(text, args.voice, args.format)
        open(args.output, "wb").write(audio)
        print(f"✅ {args.output} ({len(audio)//1024}KB, voice={args.voice})")


if __name__ == "__main__":
    main()
