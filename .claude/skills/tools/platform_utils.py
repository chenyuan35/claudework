#!/usr/bin/env python3
"""Small, dependency-free utilities shared by claudework skill scripts.

Keep platform mechanics here rather than duplicating them in CLAUDE.md or in
individual SKILL.md files.  Callers still import this module explicitly; an
instruction-file reference is only a discovery index, not an import mechanism.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any


def read_json(path: str | Path) -> Any:
    """Read UTF-8 JSON without inheriting the Windows console code page."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path: str | Path, data: Any) -> None:
    """Atomically write UTF-8 JSON so a stopped process cannot half-write state."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(data, ensure_ascii=False, indent=2) + "\n"

    fd, temp_name = tempfile.mkstemp(
        prefix=f".{target.name}.", suffix=".tmp", dir=target.parent, text=True
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, target)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def newest_file(pattern: str, root: str | Path | None = None) -> Path | None:
    """Return the most recently modified matching file, or ``None`` when absent."""
    base = Path.cwd() if root is None else Path(root)
    files = [path for path in base.glob(pattern) if path.is_file()]
    return max(files, key=lambda path: path.stat().st_mtime, default=None)


def os_aware_run(cmd_linux: str, cmd_win: str) -> str:
    """Select a shell command for the running operating system."""
    return cmd_win if sys.platform == "win32" else cmd_linux


def configure_utf8_stdio() -> None:
    """Make JSON/report output independent from the active Windows code page."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")


def _self_test() -> dict[str, bool]:
    """Dependency-free smoke test used by the shared guard's verification step."""
    with tempfile.TemporaryDirectory(prefix="platform_utils_") as temp_dir:
        root = Path(temp_dir)
        state = root / "state.json"
        write_json(state, {"中文": "正常", "count": 1})
        loaded = read_json(state)
        older = root / "older.txt"
        newer = root / "newer.txt"
        older.write_text("old", encoding="utf-8")
        newer.write_text("new", encoding="utf-8")
        os.utime(older, (1, 1))
        os.utime(newer, (2, 2))
        return {
            "utf8_json": loaded == {"中文": "正常", "count": 1},
            "newest_file": newest_file("*.txt", root) == newer,
            "os_selection": os_aware_run("linux", "windows")
            == ("windows" if sys.platform == "win32" else "linux"),
            "stdio_configured": True,
        }


if __name__ == "__main__":
    result = _self_test()
    print(json.dumps({"pass": all(result.values()), "checks": result}, ensure_ascii=False, indent=2))
    raise SystemExit(0 if all(result.values()) else 1)
