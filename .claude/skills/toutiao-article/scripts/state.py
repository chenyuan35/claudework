"""
头条号自动发布 - 状态原子读写 (v8.0)
每个Phase开始前和成功后都写入state.json。
启动时检测未完成任务并决定恢复策略。
阈值从 config/thresholds.yaml 读取。
"""
import json, os, hashlib, copy
from scripts.lib.config_loader import get_thresholds

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNTIME = os.path.join(BASE, "runtime")

STATE_FILE = os.path.join(RUNTIME, "state.json")
HISTORY_FILE = os.path.join(RUNTIME, "history.json")
METRICS_FILE = os.path.join(RUNTIME, "metrics.json")
TEMP_IMAGES_DIR = os.path.join(BASE, "runtime", "images")

def _history_max():
    return get_thresholds()["state"]["history_max"]

def _path(f):
    return f

def default_state():
    return {
        "run_id": None,
        "run_date": None,
        "article_index": 0,
        "phase": "idle",
        "title": None,
        "article_hash": None,
        "scheduled_time": None,
        "status": "idle",
        "retry_count": 0,
        "last_error": None,
        "publish_clicked": False,
        "publish_verified": False,
    }

def load_state():
    if not os.path.exists(STATE_FILE):
        return default_state()
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_state(s):
    os.makedirs(RUNTIME, exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(s, f, ensure_ascii=False, indent=2)

def update_state(**kwargs):
    s = load_state()
    s.update(kwargs)
    save_state(s)

def reset_to_idle():
    s = load_state()
    for k, v in default_state().items():
        s[k] = v
    s["status"] = "idle"
    s["phase"] = "idle"
    save_state(s)

def article_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]

def load_history():
    if not os.path.exists(HISTORY_FILE):
        return []
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def append_history(entry: dict):
    h = load_history()
    h.append(entry)
    h = h[-_history_max():]  # keep last N per config
    os.makedirs(RUNTIME, exist_ok=True)
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(h, f, ensure_ascii=False, indent=2)

def load_metrics():
    if not os.path.exists(METRICS_FILE):
        return {"deep_review_count": 0, "articles_total": 0, "history": []}
    with open(METRICS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_metrics(m):
    os.makedirs(RUNTIME, exist_ok=True)
    with open(METRICS_FILE, "w", encoding="utf-8") as f:
        json.dump(m, f, ensure_ascii=False, indent=2)

def detect_recovery():
    """
    启动时检测未完成任务，返回 (recovery_action, details)
    action: "continue_next" | "verify_publish" | "clear_and_restart" | "new"
    """
    state = load_state()
    if state.get("publish_verified"):
        return ("continue_next", "上一篇已确认发布，直接继续下一篇")
    if state.get("publish_clicked") and not state.get("publish_verified"):
        return ("verify_publish", f"已点击发布但未确认，标题={state.get('title')}")
    if state.get("phase") not in ("idle", "done") and state.get("run_date"):
        return ("clear_and_restart", "编辑器有内容但未点击发布，清除后从Phase 2重做")
    return ("new", "无遗留任务，开始新流程")

def detect_dirty_editor(pm_html: str) -> bool:
    """正文写入编辑器后检测是否为脏状态"""
    if not pm_html:
        return False
    clean = pm_html.strip() in ("", "<p><br></p>", "<p></p>")
    return not clean

# --- 清理临时文件 ---
def cleanup_temp(keep_images=False):
    """每日两篇成功后删除临时图片和临时HTML"""
    if os.path.exists(TEMP_IMAGES_DIR) and not keep_images:
        import shutil
        shutil.rmtree(TEMP_IMAGES_DIR, ignore_errors=True)
    os.makedirs(TEMP_IMAGES_DIR, exist_ok=True)

def ensure_runtime_dirs():
    os.makedirs(RUNTIME, exist_ok=True)
    os.makedirs(TEMP_IMAGES_DIR, exist_ok=True)

if __name__ == "__main__":
    # 测试
    ensure_runtime_dirs()
    print("state.json:", load_state())
    print("recovery:", detect_recovery())
