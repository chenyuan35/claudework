from __future__ import annotations

from pathlib import Path
import subprocess
import sys

SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = SKILL_DIR / "scripts"
TESTS_DIR = SKILL_DIR / "tests"
REQUIRED_FILES = [
    SKILL_DIR / "SKILL.md",
    SKILL_DIR / "generate_inject.py",
    SCRIPTS_DIR / "article_contract.py",
    SCRIPTS_DIR / "validate_article.py",
    SCRIPTS_DIR / "run_baijiahao_publish.py",
    SCRIPTS_DIR / "prepare_home.js",
    SCRIPTS_DIR / "open_editor_ready.js",
    SCRIPTS_DIR / "check_article_gate.js",
    SCRIPTS_DIR / "insert_ai_images.js",
    SCRIPTS_DIR / "set_cover.js",
    SCRIPTS_DIR / "publish_timing.js",
    SCRIPTS_DIR / "verify_submission.js",
]
JAVASCRIPT_FILES = [path for path in REQUIRED_FILES if path.suffix == ".js"]
PYTHON_FILES = [path for path in REQUIRED_FILES if path.suffix == ".py"]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def run(command: list[str], label: str) -> None:
    completed = subprocess.run(
        command,
        cwd=SKILL_DIR.parents[2],
        text=True,
        capture_output=True,
        encoding="utf-8",
    )
    if completed.returncode != 0:
        details = "\n".join(part for part in (completed.stdout, completed.stderr) if part.strip())
        raise SystemExit(f"FAIL: {label}\n{details}")


def main() -> int:
    for path in REQUIRED_FILES:
        require(path.is_file() and path.stat().st_size > 0, f"missing or empty: {path}")

    skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    required_skill_terms = [
        "scripts/run_baijiahao_publish.py",
        'data-bjh-role="section-title"',
        "bjh_content_gate_signature",
        "bjh_ai_images_complete",
        "bjh_cover_complete",
        "bjh_publish_gate_receipt",
        "submission_verified",
        "mcp__playwright__browser_*",
        "bjh_stage_result",
        "article_history.json",
        "2500",
    ]
    for term in required_skill_terms:
        require(term in skill, f"SKILL.md missing contract term: {term}")

    forbidden_skill_terms = [
        "备用",
        "方案A",
        "方案 A",
        "直接 `/builder/rc/edit`",
        "html.replace('\\\\', '\\\\\\\\')",
    ]
    for term in forbidden_skill_terms:
        require(term not in skill, f"SKILL.md contains stale path: {term}")

    gate = (SCRIPTS_DIR / "check_article_gate.js").read_text(encoding="utf-8")
    images = (SCRIPTS_DIR / "insert_ai_images.js").read_text(encoding="utf-8")
    cover = (SCRIPTS_DIR / "set_cover.js").read_text(encoding="utf-8")
    publish = (SCRIPTS_DIR / "publish_timing.js").read_text(encoding="utf-8")
    pipeline = (SCRIPTS_DIR / "run_baijiahao_publish.py").read_text(encoding="utf-8")

    require("sectionCount" in gate and "allStrong" in gate, "browser gate lacks strong-based section counting")
    require("new Set(imageSources.filter(Boolean))" in gate, "browser gate lacks unique image check")
    require("bjh_stage_result" in gate, "browser gate must write bjh_stage_result")
    require("content_gate_passed" in gate, "browser gate must set content_gate_passed status")
    require("naturalWidth > 1" in images, "image module lacks real-image validation")
    require("waitUntil" in images, "image module must use condition polling waitUntil")
    require("images_complete" in images, "image module must return images_complete")
    require("bjh_ai_images_complete" in images, "image module must write bjh_ai_images_complete")
    require("cover_complete" in cover, "cover module must return cover_complete")
    require("bjh_cover_complete" in cover, "cover module must write bjh_cover_complete")
    require("scheduled" in publish, "publish module must return scheduled")
    require("bjh_publish_gate_receipt" in publish, "publish module must write gate receipt")
    require("bjh_stage_result" in pipeline, "pipeline must merge bjh_stage_result")
    require("article_history" in pipeline or "HISTORY_FILE" in pipeline, "pipeline must track article history")
    require("mcp__playwright__browser_" in pipeline, "pipeline does not emit MCP Playwright tools")
    for forbidden in ("selenium", "puppeteer", "nodriver", "playwright.sync_api", "playwright.async_api"):
        require(forbidden not in pipeline.lower(), f"pipeline contains forbidden browser dependency: {forbidden}")

    for path in JAVASCRIPT_FILES:
        run(["node", "--check", str(path)], f"JavaScript syntax: {path.name}")
    run([sys.executable, "-m", "py_compile", *map(str, PYTHON_FILES)], "Python syntax")
    run(
        [sys.executable, "-m", "unittest", "discover", "-s", str(TESTS_DIR), "-v"],
        "contract and pipeline tests",
    )
    print("PASS: baijiahao modular pipeline is structurally consistent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
