import hashlib
from pathlib import Path


def generate(article_path: Path, inject_path: Path, title: str = "", keywords: list[str] | None = None) -> dict[str, object]:
    """读取 article.html → 转义 JS 模板字符串 → 写入 inject.js"""
    html = article_path.read_text(encoding="utf-8")
    escaped = html.replace("\\", "\\\\").replace("`", "\\`").replace("${", "\\${")
    js_func = f"() => {{ UE_V2.instants['ueditorInstant0'].setContent(`{escaped}`); }}"
    inject_path.parent.mkdir(parents=True, exist_ok=True)
    inject_path.write_text(js_func, encoding="utf-8")
    return {
        "status": "inject_ready",
        "articleSha256": hashlib.sha256(article_path.read_bytes()).hexdigest(),
        "injectLength": len(js_func),
    }
