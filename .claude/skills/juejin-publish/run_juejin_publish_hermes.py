from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any, Mapping

SPEC = {'name': 'juejin-publish', 'title': '掘金文章发布', 'mode': 'browser', 'entry_url': 'https://juejin.cn/', 'create_action': '写文章', 'required_inputs': ['title', 'body_markdown', 'tags'], 'runner': 'scripts/run_juejin_publish_hermes.py'}
SKILL_DIR = Path(__file__).resolve().parents[1]


def validate_contract() -> None:
    text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    required = (
        "HERMES_SOP_CONTRACT_START",
        "## Hermes 执行合同",
        "## 操作验收表",
        "## 发布门",
    )
    missing = [item for item in required if item not in text]
    forbidden = ("." + "claude", "mcp__" + "claude", "localhost:" + str(8932), "playwright" + "-mcp-server.sh")
    found = [item for item in forbidden if item.casefold() in text.casefold()]
    if missing or found:
        raise ValueError({"missing": missing, "forbidden": found})


async def run(payload: Mapping[str, Any]) -> dict[str, Any]:
    missing = [name for name in SPEC["required_inputs"] if not payload.get(name)]
    if missing:
        raise ValueError({"status": "input_invalid", "missing": missing})
    if SPEC["mode"] == "browser":
        steps = [
            {"tool": "mcp__playwright__browser_navigate", "url": SPEC["entry_url"]},
            {"tool": "mcp__playwright__browser_snapshot", "purpose": "verify signed-in dashboard"},
            {"tool": "mcp__playwright__browser_click", "target": SPEC["create_action"]},
            {"tool": "mcp__playwright__browser_snapshot", "purpose": "verify editor before any content mutation"},
        ]
    else:
        steps = [{"tool": "local_validation", "purpose": "validate inputs and dedup evidence only"}]
    return {"status": "ready", "skill": SPEC["name"], "mode": SPEC["mode"], "steps": steps}


def main() -> int:
    parser = argparse.ArgumentParser(description="Hermes publishing skill contract")
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--plan", type=Path)
    args = parser.parse_args()
    if args.validate:
        validate_contract()
        print(json.dumps({"status": "valid", "skill": SPEC["name"]}, ensure_ascii=False))
        return 0
    if args.plan is None:
        parser.error("use --validate or --plan <input.json>")
    payload = json.loads(args.plan.read_text(encoding="utf-8"))
    print(json.dumps(asyncio.run(run(payload)), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
