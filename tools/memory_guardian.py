#!/usr/bin/env python3
"""Non-destructive health checks and snapshots for the user's agent memories.

The script deliberately has no delete, prune, archive, or rewrite mode. It may
write a generated health report and create new backup files, but it never edits
the native memories owned by DSH, Codex/ChatGPT, Hermes, Honcho, or TDai.

Since 2026-08-26 the weekly `health` command also performs read-only
CONTENT-level review (duplicate lines, duplicate L1 records, stale pending
entries, extra Next-action anchors, diary gaps). Findings enter the `review`
lifecycle gate only; nothing is ever auto-deleted.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable


HOME = Path(os.environ.get("USERPROFILE", str(Path.home()))).resolve()
WORKSPACE = HOME / "claudework"
VAULT_REPO = HOME / "Documents" / "Obsidian Vault"
VAULT_MEMORY = VAULT_REPO / "MEMORY"
STATE_ROOT = HOME / ".agent-memory"
REPORT_ROOT = STATE_ROOT / "reports"
BACKUP_ROOT = STATE_ROOT / "backups"

SOURCES: dict[str, Path] = {
    "dsh_curated": HOME / ".dsh" / "memory",
    "dsh_tencent": HOME / ".memory-tencentdb" / "memory-tdai",
    "codex_auto": HOME / ".codex" / "memories",
    "hermes_local": HOME / "AppData" / "Local" / "hermes" / "memories",
    "shared_vault": VAULT_MEMORY,
}

CORE_FILES: dict[str, tuple[str, ...]] = {
    "dsh_curated": ("active.md", "decisions.md", "profile.md"),
    "dsh_tencent": ("persona.md", "vectors.db"),
    "codex_auto": ("MEMORY.md", "memory_summary.md", "raw_memories.md"),
    "hermes_local": ("MEMORY.md", "USER.md"),
    "shared_vault": ("AGENTS.md", "USER.md", "SOUL.md", "README-使用说明.md"),
}

TEXT_SUFFIXES = {".md", ".txt", ".json", ".jsonl", ".yaml", ".yml"}
SKIP_PARTS = {".git", ".secrets", "__pycache__"}
DEPRECATED_TERMS = (
    "cc switch",
    "memory bus",
    "claude/codex/hermes",
    "claude 专属",
    "claude记忆",
    "作废",
    "deprecated:",
    "superseded_by:",
)
SENSITIVE_NAME_TERMS = ("secret", "token", "credential", "cookie", "api_key", "apikey")
ACTIVE_POLICY_DOCS = {"AGENTS.md", "knowledge/记忆治理协议-迁移版.md"}

# ── content-review patterns (added 2026-08-26) ──────────────────────────────
PENDING_LINE_RE = re.compile(r"pending_[A-Za-z0-9_]+\s*:")
EMBEDDED_DATE_RE = re.compile(r"20\d{2}-\d{2}-\d{2}")
NEXT_ACTION_PREFIX_RE = re.compile(r"^#{0,6}\s*next\s*action", re.IGNORECASE)


def now_local() -> dt.datetime:
    return dt.datetime.now().astimezone()


def iso_time(value: float | None) -> str | None:
    if value is None:
        return None
    return dt.datetime.fromtimestamp(value).astimezone().isoformat(timespec="seconds")


def iter_files(root: Path) -> Iterable[Path]:
    if not root.exists():
        return
    for path in root.rglob("*"):
        try:
            relative = path.relative_to(root)
        except ValueError:
            continue
        if any(part in SKIP_PARTS for part in relative.parts):
            continue
        try:
            if path.is_file():
                yield path
        except OSError:
            continue


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def git_output(repo: Path, *args: str) -> str | None:
    if not (repo / ".git").exists():
        return None
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode != 0:
        return None
    return completed.stdout.strip()


def latest_manifested_backup(filename: str) -> str | None:
    if not BACKUP_ROOT.exists():
        return None
    for candidate in sorted(BACKUP_ROOT.iterdir(), reverse=True):
        if not candidate.is_dir():
            continue
        manifest_path = candidate / "manifest.json"
        target = candidate / filename
        if not (manifest_path.exists() and target.exists()):
            continue
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            entry = next((item for item in manifest.get("files", []) if item.get("path") == filename), None)
            if entry and entry.get("sha256") == sha256_file(target):
                return str(target)
        except (OSError, ValueError, StopIteration):
            continue
    return None


def sqlite_quick_check(path: Path) -> str:
    if not path.exists():
        return "missing"
    try:
        uri = f"file:{path.as_posix()}?mode=ro"
        with sqlite3.connect(uri, uri=True, timeout=5) as connection:
            row = connection.execute("PRAGMA quick_check").fetchone()
        return str(row[0]) if row else "no-result"
    except Exception as exc:  # report only; never attempt a repair
        return f"error:{type(exc).__name__}"


def source_inventory(name: str, root: Path) -> dict[str, Any]:
    files = list(iter_files(root)) if root.exists() else []
    mtimes: list[float] = []
    total_bytes = 0
    sensitive_names: list[str] = []
    exact_hashes: dict[str, list[str]] = {}
    deprecated_candidates: list[str] = []

    for path in files:
        try:
            stat = path.stat()
        except OSError:
            continue
        total_bytes += stat.st_size
        mtimes.append(stat.st_mtime)
        relative = path.relative_to(root).as_posix()
        relative_path = path.relative_to(root)
        is_native_backup = ".backup" in relative_path.parts
        lowered_name = path.name.lower()
        if not is_native_backup and any(term in lowered_name for term in SENSITIVE_NAME_TERMS):
            sensitive_names.append(relative)

        if not is_native_backup and path.suffix.lower() in TEXT_SUFFIXES and stat.st_size <= 2 * 1024 * 1024:
            try:
                digest = sha256_file(path)
                exact_hashes.setdefault(digest, []).append(relative)
                is_shared_candidate_area = (
                    name == "shared_vault"
                    and not relative.startswith(("memory/", "archive/"))
                    and relative not in {"health.md"}
                    and relative not in ACTIVE_POLICY_DOCS
                )
                if is_shared_candidate_area:
                    sample = path.read_text(encoding="utf-8", errors="replace")[:16_384].lower()
                    if any(term in sample for term in DEPRECATED_TERMS):
                        deprecated_candidates.append(relative)
            except OSError:
                pass

    duplicates = [paths for paths in exact_hashes.values() if len(paths) > 1]
    missing_core = [item for item in CORE_FILES[name] if not (root / item).exists()]
    age_days = None
    if mtimes:
        age_days = int((now_local().timestamp() - max(mtimes)) // 86400)

    inventory: dict[str, Any] = {
        "path": str(root),
        "exists": root.exists(),
        "file_count": len(files),
        "bytes": total_bytes,
        "oldest_mtime": iso_time(min(mtimes) if mtimes else None),
        "newest_mtime": iso_time(max(mtimes) if mtimes else None),
        "days_since_latest_write": age_days,
        "missing_core": missing_core,
        "exact_duplicate_groups": duplicates[:20],
        "sensitive_name_candidates": sorted(sensitive_names)[:30],
    }

    if name == "shared_vault":
        inventory["deprecated_candidates"] = sorted(set(deprecated_candidates))[:50]
        inventory["daily_notes"] = len(list((root / "memory").glob("20??-??-??.md")))
        inventory["knowledge_files"] = len(list((root / "knowledge").rglob("*.md")))
        inventory["git_status"] = git_output(VAULT_REPO, "status", "--porcelain", "--untracked-files=no")
        inventory["git_remote"] = git_output(VAULT_REPO, "remote", "get-url", "origin")

    if name == "codex_auto":
        memory_file = root / "MEMORY.md"
        inventory["memory_index_lines"] = (
            len(memory_file.read_text(encoding="utf-8", errors="replace").splitlines())
            if memory_file.exists()
            else 0
        )
        inventory["rollout_summaries"] = len(list((root / "rollout_summaries").glob("*.md")))
        inventory["git_status"] = git_output(root, "status", "--porcelain", "--untracked-files=no")
        inventory["git_remote"] = git_output(root, "remote", "get-url", "origin")
        inventory["recovery_bundle"] = latest_manifested_backup("codex-memories.bundle")

    if name == "dsh_tencent":
        inventory.update(
            {
                "conversation_shards": len(list((root / "conversations").glob("*.jsonl"))),
                "record_shards": len(list((root / "records").glob("*.jsonl"))),
                "scene_blocks": len(list((root / "scene_blocks").glob("*.md"))),
                "persona_backups": len(list((root / ".backup" / "persona").glob("*"))),
                "scene_backup_sets": len(list((root / ".backup" / "scene_blocks").glob("*"))),
                "temporary_files": [
                    str(path.relative_to(root).as_posix())
                    for path in root.rglob("*.tmp*")
                    if path.is_file() and now_local().timestamp() - path.stat().st_mtime > 86400
                ][:30],
                "vectors_db_quick_check": sqlite_quick_check(root / "vectors.db"),
            }
        )

    return inventory


# ── content-level review (read-only; added 2026-08-26) ──────────────────────

def curated_content_findings(root: Path) -> tuple[list[dict[str, str]], dict[str, Any]]:
    """Check DSH curated markdown files for duplicate lines, extra Next-action
    anchors, and stale pending_* entries. Report-only."""
    findings: list[dict[str, str]] = []
    details: dict[str, Any] = {}
    stale_cutoff = now_local().date() - dt.timedelta(days=7)

    for filename in CORE_FILES["dsh_curated"]:
        path = root / filename
        if not path.exists():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        lines = text.splitlines()
        file_detail: dict[str, Any] = {}

        seen: dict[str, int] = {}
        duplicate_samples: list[str] = []
        duplicate_pairs = 0
        for idx, raw in enumerate(lines, start=1):
            key = raw.strip()
            if len(key) < 12:
                continue
            if key in seen:
                duplicate_pairs += 1
                if len(duplicate_samples) < 10:
                    duplicate_samples.append(f"L{seen[key]}==L{idx}: {key[:60]}…")
            else:
                seen[key] = idx
        file_detail["duplicate_line_pairs"] = duplicate_pairs
        file_detail["duplicate_line_samples"] = duplicate_samples
        if duplicate_pairs:
            findings.append(
                {
                    "severity": "review",
                    "source": "dsh_curated",
                    "message": f"{filename} 存在 {duplicate_pairs} 处逐字重复行；仅列人工复核，不自动删除",
                }
            )

        if filename == "active.md":
            anchors = [
                idx
                for idx, raw in enumerate(lines, start=1)
                if NEXT_ACTION_PREFIX_RE.match(raw.strip())
            ]
            file_detail["next_action_lines"] = anchors
            if len(anchors) > 1:
                findings.append(
                    {
                        "severity": "review",
                        "source": "dsh_curated",
                        "message": f"active.md 出现 {len(anchors)} 个 Next action 锚点（行 {anchors[:8]}）；契约要求唯一",
                    }
                )

        stale_pending: list[str] = []
        for idx, raw in enumerate(lines, start=1):
            if not PENDING_LINE_RE.search(raw):
                continue
            match = EMBEDDED_DATE_RE.search(raw)
            if not match:
                continue
            try:
                entry_date = dt.date.fromisoformat(match.group(0))
            except ValueError:
                continue
            if entry_date < stale_cutoff:
                stale_pending.append(f"L{idx}: {raw.strip()[:80]}")
        file_detail["stale_pending_entries"] = stale_pending
        if stale_pending:
            findings.append(
                {
                    "severity": "review",
                    "source": "dsh_curated",
                    "message": f"{filename} 存在 {len(stale_pending)} 条超过 7 天未清的 pending_* 记录；需人工裁决移除或更新",
                }
            )

        details[filename] = file_detail
    return findings, details


def tdai_l1_duplicate_groups(db_path: Path, limit: int = 10) -> tuple[list[dict[str, str]], dict[str, Any]]:
    """Find L1 records whose content text is exactly duplicated. Report-only."""
    if not db_path.exists():
        return [], {"error": "vectors.db missing"}
    uri = f"file:{db_path.as_posix()}?mode=ro"
    try:
        connection = sqlite3.connect(uri, uri=True, timeout=5)
        try:
            rows = connection.execute(
                "SELECT COUNT(*) AS n, SUBSTR(GROUP_CONCAT(record_id, ','), 1, 160) AS ids "
                "FROM l1_records GROUP BY content HAVING n > 1 ORDER BY n DESC LIMIT ?",
                (limit,),
            ).fetchall()
            redundant = connection.execute(
                "SELECT COALESCE(SUM(n - 1), 0) FROM "
                "(SELECT COUNT(*) AS n FROM l1_records GROUP BY content HAVING n > 1)"
            ).fetchone()[0]
        finally:
            connection.close()
    except Exception as exc:  # report only; never attempt a repair
        return (
            [
                {
                    "severity": "review",
                    "source": "dsh_tencent",
                    "message": f"L1 内容重复检查失败: {type(exc).__name__}",
                }
            ],
            {"error": f"{type(exc).__name__}: {exc}"},
        )
    groups = [{"count": row[0], "record_ids_sample": row[1]} for row in rows]
    findings: list[dict[str, str]] = []
    if groups:
        findings.append(
            {
                "severity": "review",
                "source": "dsh_tencent",
                "message": f"l1_records 存在内容完全相同的重复组（采样 {len(groups)} 组，冗余共 {redundant} 条）；需人工确认后用官方 deleteL1Batch 清理",
            }
        )
    return findings, {"group_samples": groups, "redundant_records": redundant}


def vault_daily_note_gaps(root: Path, limit: int = 30) -> tuple[list[dict[str, str]], dict[str, Any]]:
    """Detect missing days in the shared-vault diary sequence. Report-only."""
    folder = root / "memory"
    dates: list[dt.date] = []
    for path in folder.glob("20??-??-??.md"):
        try:
            dates.append(dt.date.fromisoformat(path.stem))
        except ValueError:
            continue
    if not dates:
        return [], {"missing_dates": [], "span_days": 0, "present": 0}
    lo, hi = min(dates), max(dates)
    present = set(dates)
    missing: list[str] = []
    cursor = lo
    while cursor <= hi:
        if cursor not in present:
            missing.append(cursor.isoformat())
        cursor += dt.timedelta(days=1)
    findings: list[dict[str, str]] = []
    if missing:
        preview = ", ".join(missing[:8]) + ("…" if len(missing) > 8 else "")
        findings.append(
            {
                "severity": "review",
                "source": "shared_vault",
                "message": f"共同层日记 {lo}~{hi} 区间缺 {len(missing)} 天：{preview}",
            }
        )
    return findings, {
        "missing_dates": missing[:limit],
        "missing_count": len(missing),
        "span_days": (hi - lo).days + 1,
        "present": len(present),
    }


def content_review_section() -> tuple[list[dict[str, str]], dict[str, Any]]:
    findings: list[dict[str, str]] = []
    section: dict[str, Any] = {}
    curated_findings, curated_details = curated_content_findings(SOURCES["dsh_curated"])
    findings.extend(curated_findings)
    section["curated"] = curated_details
    tdai_findings, tdai_details = tdai_l1_duplicate_groups(SOURCES["dsh_tencent"] / "vectors.db")
    findings.extend(tdai_findings)
    section["tdai_l1_duplicates"] = tdai_details
    vault_findings, vault_details = vault_daily_note_gaps(VAULT_MEMORY)
    findings.extend(vault_findings)
    section["vault_daily_notes"] = vault_details
    return findings, section


def build_health() -> dict[str, Any]:
    sources = {name: source_inventory(name, root) for name, root in SOURCES.items()}
    warnings: list[dict[str, str]] = []

    for name, data in sources.items():
        if not data["exists"]:
            warnings.append({"severity": "critical", "source": name, "message": "记忆源不存在"})
        if data["missing_core"]:
            warnings.append(
                {
                    "severity": "critical",
                    "source": name,
                    "message": "缺少核心文件: " + ", ".join(data["missing_core"]),
                }
            )
        if data["exact_duplicate_groups"]:
            warnings.append(
                {
                    "severity": "review",
                    "source": name,
                    "message": f"发现 {len(data['exact_duplicate_groups'])} 组完全相同文件；仅列为人工复核，不自动删除",
                }
            )

    tdai = sources["dsh_tencent"]
    if tdai.get("vectors_db_quick_check") != "ok":
        warnings.append(
            {
                "severity": "critical",
                "source": "dsh_tencent",
                "message": f"vectors.db quick_check={tdai.get('vectors_db_quick_check')}",
            }
        )
    if tdai.get("temporary_files"):
        warnings.append(
            {
                "severity": "review",
                "source": "dsh_tencent",
                "message": f"发现 {len(tdai['temporary_files'])} 个临时检查点文件；先观察是否持续存在",
            }
        )

    codex = sources["codex_auto"]
    if not codex.get("git_remote") and not codex.get("recovery_bundle"):
        warnings.append(
            {
                "severity": "review",
                "source": "codex_auto",
                "message": "本地 Git 没有远端且没有已校验 bundle，换机前必须建立私有备份",
            }
        )

    shared = sources["shared_vault"]
    if shared.get("deprecated_candidates"):
        warnings.append(
            {
                "severity": "review",
                "source": "shared_vault",
                "message": f"发现 {len(shared['deprecated_candidates'])} 个旧 Claude/Memory Bus/作废候选；需逐个注明替代关系后归档",
            }
        )

    content_findings, content_review = content_review_section()
    warnings.extend(content_findings)

    return {
        "schema_version": 2,
        "generated_at": now_local().isoformat(timespec="seconds"),
        "mode": "read-only-health+content-review",
        "source_policy": "native memories are inspected but never rewritten or deleted",
        "sources": sources,
        "warnings": warnings,
        "content_review": content_review,
    }


def human_bytes(value: int) -> str:
    size = float(value)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"


def render_markdown(health: dict[str, Any]) -> str:
    lines = [
        "# 三智能体记忆健康检查",
        "",
        f"> 生成时间：{health['generated_at']}",
        "> 本报告只读检查源记忆；不会删除、归档或改写任何原文件。",
        "",
        "## 总览",
        "",
        "| 记忆源 | 文件 | 大小 | 最近写入 | 核心缺失 |",
        "|---|---:|---:|---|---|",
    ]
    for name, data in health["sources"].items():
        lines.append(
            f"| `{name}` | {data['file_count']} | {human_bytes(data['bytes'])} | "
            f"{data['newest_mtime'] or '-'} | {', '.join(data['missing_core']) or '无'} |"
        )

    lines.extend(["", "## 需要复核", ""])
    if not health["warnings"]:
        lines.append("- 未发现需要复核的问题。")
    else:
        for warning in health["warnings"]:
            lines.append(f"- **{warning['severity']} / {warning['source']}**：{warning['message']}")

    review = health.get("content_review") or {}
    if review:
        curated = review.get("curated") or {}
        active_detail = curated.get("active.md") or {}
        duplicate_pairs = sum(
            int((curated.get(filename) or {}).get("duplicate_line_pairs", 0))
            for filename in CORE_FILES["dsh_curated"]
        )
        stale_total = sum(
            len((curated.get(filename) or {}).get("stale_pending_entries") or [])
            for filename in CORE_FILES["dsh_curated"]
        )
        tdai_dups = review.get("tdai_l1_duplicates") or {}
        vault = review.get("vault_daily_notes") or {}
        lines.extend(
            [
                "",
                "## 内容级复核明细",
                "",
                f"- DSH curated：逐字重复行 {duplicate_pairs} 处，过期 pending 条目 {stale_total} 条，"
                f"active.md 的 Next action 锚点 {len(active_detail.get('next_action_lines') or [])} 个。",
                f"- TDai L1：内容完全相同的重复组（采样）{len(tdai_dups.get('group_samples') or [])} 组，"
                f"冗余记录 {tdai_dups.get('redundant_records', 0)} 条。清理必须人工确认后走官方 deleteL1Batch。",
                f"- 共同 Vault 日记：跨度 {vault.get('span_days', 0)} 天 / 实有 {vault.get('present', 0)} 篇，"
                f"区间内缺失 {vault.get('missing_count', 0)} 天。",
                "",
            ]
        )

    tdai = health["sources"]["dsh_tencent"]
    codex = health["sources"]["codex_auto"]
    shared = health["sources"]["shared_vault"]
    lines.extend(
        [
            "## 分层指标",
            "",
            f"- DSH 腾讯记忆：对话分片 {tdai.get('conversation_shards', 0)}，记录分片 "
            f"{tdai.get('record_shards', 0)}，场景块 {tdai.get('scene_blocks', 0)}，"
            f"persona 备份 {tdai.get('persona_backups', 0)}，数据库检查 `{tdai.get('vectors_db_quick_check')}`。",
            f"- Codex 自动记忆：索引 {codex.get('memory_index_lines', 0)} 行，rollout 摘要 "
            f"{codex.get('rollout_summaries', 0)} 篇，已校验恢复 bundle："
            f"{'有' if codex.get('recovery_bundle') else '无'}。",
            f"- 共同 Vault：日记 {shared.get('daily_notes', 0)} 篇，knowledge 文档 "
            f"{shared.get('knowledge_files', 0)} 篇。",
            "",
            "## 生命周期门",
            "",
            "- `active`：当前规则、确认偏好、正在推进的项目状态。",
            "- `review`：疑似重复、过时、冲突或超过体积阈值；只能人工确认。",
            "- `archive`：已有替代项且保留审计价值；用 Git 移动，不删除。",
            "- `protected`：核心规则、用户画像、数据库、密钥引用和最近可恢复备份；禁止自动处理。",
            "",
            "## 自动化边界",
            "",
            "周检只更新本报告和本机 JSON 报告。任何合并、归档、过期删除、Provider 写入或数据库维护都必须单独执行并验证。",
            "",
        ]
    )
    return "\n".join(lines)


def write_health() -> tuple[Path, Path, dict[str, Any]]:
    health = build_health()
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    VAULT_MEMORY.mkdir(parents=True, exist_ok=True)
    json_path = REPORT_ROOT / "latest.json"
    markdown_path = VAULT_MEMORY / "health.md"
    json_path.write_text(json.dumps(health, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    markdown_path.write_text(render_markdown(health), encoding="utf-8")
    return json_path, markdown_path, health


def copy_tree_filtered(source: Path, destination: Path, excluded_names: set[str] | None = None) -> None:
    excluded_names = excluded_names or set()
    for path in iter_files(source):
        relative = path.relative_to(source)
        if any(part in excluded_names for part in relative.parts):
            continue
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)


def sqlite_backup(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    source_uri = f"file:{source.as_posix()}?mode=ro"
    with sqlite3.connect(source_uri, uri=True) as source_db, sqlite3.connect(destination) as destination_db:
        source_db.backup(destination_db)
        row = destination_db.execute("PRAGMA quick_check").fetchone()
    if not row or row[0] != "ok":
        raise RuntimeError(f"SQLite snapshot verification failed: {destination}")


def git_bundle(repo: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(
        ["git", "-C", str(repo), "bundle", "create", str(destination), "--all"],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode != 0:
        raise RuntimeError(f"git bundle failed for {repo}: {completed.stderr.strip()}")


def create_snapshot() -> Path:
    stamp = now_local().strftime("%Y%m%d-%H%M%S")
    destination = (BACKUP_ROOT / stamp).resolve()
    expected_parent = BACKUP_ROOT.resolve()
    if expected_parent not in destination.parents:
        raise RuntimeError("Refusing to create snapshot outside the dedicated backup root")
    destination.mkdir(parents=True, exist_ok=False)

    copy_tree_filtered(SOURCES["dsh_curated"], destination / "dsh-curated")
    copy_tree_filtered(SOURCES["hermes_local"], destination / "hermes-local")

    tdai_source = SOURCES["dsh_tencent"]
    tdai_destination = destination / "dsh-tencent"
    for name in ("conversations", "records", "scene_blocks", ".metadata"):
        source_dir = tdai_source / name
        if source_dir.exists():
            copy_tree_filtered(source_dir, tdai_destination / name)
    if (tdai_source / "persona.md").exists():
        tdai_destination.mkdir(parents=True, exist_ok=True)
        shutil.copy2(tdai_source / "persona.md", tdai_destination / "persona.md")
    sqlite_backup(tdai_source / "vectors.db", tdai_destination / "vectors.db")

    git_bundle(SOURCES["codex_auto"], destination / "codex-memories.bundle")
    git_bundle(VAULT_REPO, destination / "obsidian-vault.bundle")

    rule_files = {
        "dsh-AGENTS.md": HOME / ".dsh" / "AGENTS.md",
        "codex-AGENTS.md": HOME / ".codex" / "AGENTS.md",
        "workspace-AGENTS.md": WORKSPACE / "AGENTS.md",
        "hermes-SOUL.md": HOME / "AppData" / "Local" / "hermes" / "SOUL.md",
    }
    rules_destination = destination / "rules"
    rules_destination.mkdir(parents=True, exist_ok=True)
    for target_name, source in rule_files.items():
        if source.exists():
            shutil.copy2(source, rules_destination / target_name)

    files: list[dict[str, Any]] = []
    for path in sorted(iter_files(destination), key=lambda item: item.as_posix().lower()):
        if path.name.endswith(("-wal", "-shm")):
            continue
        relative = path.relative_to(destination).as_posix()
        files.append({"path": relative, "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    manifest = {
        "schema_version": 1,
        "created_at": now_local().isoformat(timespec="seconds"),
        "policy": "local non-secret recovery snapshot; no source files changed",
        "excluded": [
            "all .secrets directories",
            "provider configuration and credentials",
            "Hermes state.db and application caches",
            "TDai rolling .backup directory and live WAL/SHM files",
        ],
        "files": files,
    }
    (destination / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return destination


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("health", "snapshot", "all"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command in {"snapshot", "all"}:
        snapshot = create_snapshot()
        print(json.dumps({"snapshot": str(snapshot)}, ensure_ascii=False))
    if args.command in {"health", "all"}:
        json_path, markdown_path, health = write_health()
        critical = sum(1 for item in health["warnings"] if item["severity"] == "critical")
        review_items = sum(1 for item in health["warnings"] if item["severity"] == "review")
        print(
            json.dumps(
                {
                    "health_json": str(json_path),
                    "health_markdown": str(markdown_path),
                    "warnings": len(health["warnings"]),
                    "critical": critical,
                    "review_items": review_items,
                },
                ensure_ascii=False,
            )
        )
        if critical:
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
