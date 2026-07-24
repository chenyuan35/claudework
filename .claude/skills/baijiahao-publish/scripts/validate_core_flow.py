from pathlib import Path
import re


SKILL_DIR = Path(__file__).resolve().parent.parent
SKILL_FILE = SKILL_DIR / "SKILL.md"
SCRIPTS_DIR = SKILL_DIR / "scripts"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


skill = SKILL_FILE.read_text(encoding="utf-8")

# ── 脚本存在性 ──
gate = (SCRIPTS_DIR / "check_article_gate.js").read_text(encoding="utf-8")
images = (SCRIPTS_DIR / "insert_ai_images.js").read_text(encoding="utf-8")
editor = (SCRIPTS_DIR / "open_editor_ready.js").read_text(encoding="utf-8")
cover = (SCRIPTS_DIR / "set_cover.js").read_text(encoding="utf-8")
timing = (SCRIPTS_DIR / "publish_timing.js").read_text(encoding="utf-8")

# ── SKILL.md 结构检查 ──
require("# 百家号发布" in skill, "SKILL.md missing heading")
require("质量门" in skill, "SKILL.md missing quality gate")
require("## 主管道" in skill, "SKILL.md missing pipeline section")
require("约束条件" in skill, "SKILL.md missing known issues")
require("## 最新发布记录" in skill, "SKILL.md missing publish log")

# ── 编辑器入口脚本检查（v3 修复：等渲染再操作） ──
require("waitForPublishBtn" in editor, "editor script missing waitForPublishBtn")
require("BTN_TIMEOUT" in editor, "editor script missing BTN_TIMEOUT")
require("180000" in editor, "editor script editor wait is not 180000ms")
require("editorDeadline" in editor, "editor script missing editorDeadline")
require("readystatechange" in editor, "editor script missing readystatechange wait")
require("CONTENT_PAGE_TIMEOUT" in editor, "editor script missing CONTENT_PAGE_TIMEOUT")
require("PUBLISH_WORK_TIMEOUT" in editor, "editor script missing PUBLISH_WORK_TIMEOUT")
require("TITLE_INPUT_TIMEOUT" in editor, "editor script missing TITLE_INPUT_TIMEOUT")
require("location.href" in editor, "editor script URL checks removed")
for cls in ("foldContent", "no-content", "-left"):
    require(f'[class*="{cls}"]' in editor, f"editor script missing overlay class: {cls}")

# ── 正文闸门脚本检查 ──
require("bjh_gate_stage" in gate, "gate stage selector missing")
require("hardFailures" in gate and "warnings" in gate, "hard/warning separation missing")
require("pass: hardFailures.length === 0" in gate, "warnings may still block publishing")
require("bjh_content_gate_signature" in gate, "content gate does not persist a reload-safe signature")
require("BJH_EDITOR_NOT_READY" in gate, "gate missing editor not ready check")
require("BJH_GATE_FAILED" in gate, "gate missing BJH_GATE_FAILED")

# ── AI 插图脚本检查 ──
require("BJH_AI_IMAGE_FAILED" in images, "AI-image script has no unique failure code")
require("，写实风格" in images, "AI-image prompt is not derived from section text")
require("sectionImgCount" in images, "AI-image script cannot detect existing images per section")
require("imageCounts" not in images, "stale imageCounts variable still present")
require("nativeSetter" in images, "AI-image script missing React native setter pattern")

# ── 封面 AI封图脚本检查 ──
require("BJH_COVER_FAILED" in cover, "cover script missing BJH_COVER_FAILED")
require("FeEditorApp-_65f7660e096d0b20-btn" in cover, "cover script missing generate button class")
require("确定" in cover, "cover script missing confirm button text")
require("coverSelectors" in cover, "cover script missing verification selectors")
require("verify_failed" in cover, "cover script missing verification failure code")
require("cover_set_via_ai" in cover, "cover script missing success status")
require("cheetah-tabs-tabpane-active" in cover, "cover script missing active tabpane scoping")

# ── 定时发布脚本检查 ──
require("BJH_PUBLISH_FAILED" in timing, "timing script missing BJH_PUBLISH_FAILED")
require("定时发布" in timing, "timing script missing 定时发布 text")

# ── SKILL.md 中的脚本引用 ──
require("open_editor_ready" in skill, "SKILL.md does not reference open_editor_ready.js")
require("check_article_gate" in skill, "SKILL.md does not reference check_article_gate.js")
require("insert_ai_images" in skill, "SKILL.md does not reference insert_ai_images.js")
require("set_cover" in skill, "SKILL.md does not reference set_cover.js")
require("publish_timing" in skill, "SKILL.md does not reference publish_timing.js")

# ── 技能文件铁律 ──
require("el.remove()" in skill, "SKILL.md missing React DOM safety warning")
require("browser_navigate" in skill, "SKILL.md missing SPA navigation warning")
require("不穿插" in skill, "SKILL.md missing sequential execution rule")
require("关闭弹窗只能用常规手段" in skill, "SKILL.md missing dialog close rule")
require("不能" in skill, "SKILL.md missing DOM safety constraints")

# ── 质量门关键字 ──
require("2000 汉字" in skill, "SKILL.md missing CJK count in quality gate")
require("AI 声明" in skill, "SKILL.md missing AI declaration requirement")
require("封面" in skill, "SKILL.md missing cover requirement")

print("PASS: baijiahao core flow is structurally consistent")
