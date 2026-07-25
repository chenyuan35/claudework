"""
头条号自动发布 - 共享配置加载器 (v8.0)
所有脚本通过此模块读取 config/*.yaml。
"""
import os, yaml

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def _load(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def get_thresholds():
    return _load(os.path.join(BASE, "config", "thresholds.yaml"))

def get_selectors():
    return _load(os.path.join(BASE, "config", "selectors.yaml"))

def get_content_policy():
    return _load(os.path.join(BASE, "config", "content_policy.yaml"))

def get_services():
    return _load(os.path.join(BASE, "config", "services.yaml"))
