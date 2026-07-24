#!/usr/bin/env python3
"""
run_skill.py — 统一调度入口（只做调度 + 状态恢复）

职责：
  - 解析技能名 -> task_id -> 调度 skill_guard.py
  - 保存/恢复执行状态（.claude/run_state/）
  - 无人值守：全部自动执行，仅终局错误报告

平台流程完全保留在各自 SKILL.md 与专属脚本中。

用法：
  python run_skill.py --check <skill_name>          # 执行前守卫
  python run_skill.py --post-check <skill_name> --task-id <id> [--result-files ...]
  python run_skill.py --audit <skill_path>           # 全量审计
  python run_skill.py --detect <skill_name>          # 类型检测
  python run_skill.py --scan [vuln_type] [--json]    # 脆弱模式扫描
  python run_skill.py --plan [vuln_type] [--json]    # 修复计划（不改文件）
  python run_skill.py --fix [vuln_type] [--apply]    # 受限批量修复
  python run_skill.py --rollback <manifest.json>     # 回滚一次批量修复
  python run_skill.py --list                         # 列出可执行技能

退出码：0=通过 1=守卫拦截 2=内部错误
"""

import json, sys, subprocess, uuid
from pathlib import Path
from datetime import datetime

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))
from platform_utils import configure_utf8_stdio, write_json

configure_utf8_stdio()
GUARD = TOOLS_DIR / "skill_guard.py"
SKILLS_DIR = TOOLS_DIR.parent
WORK_DIR = SKILLS_DIR.parent.parent
STATE_DIR = WORK_DIR / ".claude" / "run_state"

def run_guard(mode: str, target: str, extra: list[str] | None = None) -> dict:
    cmd = [sys.executable, "-X", "utf8", str(GUARD), mode, target]
    if extra:
        cmd.extend(extra)
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=60, cwd=str(WORK_DIR),
        )
    except subprocess.TimeoutExpired:
        return {"pass": False, "error": "skill_guard timed out after 60 seconds", "exit_code": 2}
    try:
        result = json.loads(proc.stdout)
    except json.JSONDecodeError:
        result = {"pass": False, "error": "guard parse error", "stderr": proc.stderr[:300]}
    result["exit_code"] = proc.returncode
    return result

def save_state(task_id: str, skill: str, status: str, detail: dict) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    write_json(
        STATE_DIR / f"{task_id}.json",
        {"task_id": task_id, "skill": skill, "status": status,
         "timestamp": datetime.now().isoformat(), "detail": detail},
    )


def forward_guard(args: list[str]) -> int:
    """Expose maintenance modes through the normal dispatcher without parsing them twice."""
    proc = subprocess.run(
        [sys.executable, "-X", "utf8", str(GUARD), *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(WORK_DIR),
    )
    if proc.stdout:
        print(proc.stdout, end="")
    if proc.stderr:
        print(proc.stderr, file=sys.stderr, end="")
    return proc.returncode

def resolve_path(name: str) -> Path | None:
    for p in [SKILLS_DIR / name / "SKILL.md", SKILLS_DIR / name / f"{name}.md"]:
        if p.exists():
            return p.resolve()
    return None

def main():
    if len(sys.argv) < 2:
        print(f"usage: {sys.argv[0]} --check|--post-check|--audit|--detect|--scan|--plan|--fix|--rollback|--list", file=sys.stderr); sys.exit(2)
    cmd = sys.argv[1]

    if cmd in {"--scan", "--plan", "--fix", "--rollback"}:
        sys.exit(forward_guard([cmd[2:], *sys.argv[2:]]))

    if cmd == "--list":
        skills = []
        for d in sorted(SKILLS_DIR.iterdir()):
            if not d.is_dir() or d.name == "tools": continue
            sm = d / "SKILL.md"
            if not sm.exists(): continue
            desc = ""
            for line in sm.read_text(encoding="utf-8").split("\n"):
                if line.startswith("description:"):
                    desc = line.split(":", 1)[1].strip().strip('"')
                    break
            skills.append({"name": d.name, "path": str(sm), "description": desc})
        print(json.dumps(skills, ensure_ascii=False, indent=2)); sys.exit(0)

    if cmd == "--detect":
        if len(sys.argv) < 3: print("need skill_name", file=sys.stderr); sys.exit(2)
        p = resolve_path(sys.argv[2])
        if not p: print(json.dumps({"error": f"not found: {sys.argv[2]}"})); sys.exit(2)
        result = run_guard("detect", str(p))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(0 if result.get("pass") else 1)

    if cmd == "--audit":
        if len(sys.argv) < 3: print("need skill_path", file=sys.stderr); sys.exit(2)
        result = run_guard("audit", sys.argv[2])
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(0 if result.get("pass") else 1)

    if cmd == "--check":
        if len(sys.argv) < 3: print("need skill_name", file=sys.stderr); sys.exit(2)
        name = sys.argv[2]
        task_id = str(uuid.uuid4())[:8]
        result = run_guard("pre", name)
        ok = result.get("pass", False)
        save_state(task_id, name, "pass" if ok else "blocked", result)
        out = {"task_id": task_id, "skill": name, "pass": ok, "guard": result}
        print(json.dumps(out, ensure_ascii=False, indent=2))
        sys.exit(0 if ok else 1)

    if cmd == "--post-check":
        name = sys.argv[2] if len(sys.argv) > 2 else None
        if not name: print("need skill_name", file=sys.stderr); sys.exit(2)
        extra_args = sys.argv[3:]
        task_id = None; result_files = []; i = 0
        while i < len(extra_args):
            if extra_args[i] == "--task-id":
                task_id = extra_args[i+1] if i+1 < len(extra_args) else None; i += 2
            elif extra_args[i] == "--result-files":
                i += 1
                while i < len(extra_args) and not extra_args[i].startswith("--"):
                    result_files.append(extra_args[i]); i += 1
            else: i += 1
        if not task_id: task_id = str(uuid.uuid4())[:8]
        ge = ["--task-id", task_id]
        if result_files: ge += ["--result-files"] + result_files
        result = run_guard("post", name, ge)
        ok = result.get("pass", False)
        save_state(task_id, name, "pass" if ok else "blocked", result)
        out = {"task_id": task_id, "skill": name, "pass": ok, "guard": result}
        print(json.dumps(out, ensure_ascii=False, indent=2))
        sys.exit(0 if ok else 1)

    print(f"unknown: {cmd}", file=sys.stderr); sys.exit(2)

if __name__ == "__main__":
    main()
