from __future__ import annotations

import json
from pathlib import Path

from tools import memory_guardian


def test_inspect_hermes_memory_runtime_flags_pending_and_failed_memory_jobs(tmp_path: Path) -> None:
    hermes_home = tmp_path / "hermes"
    pending = hermes_home / "pending" / "memory"
    pending.mkdir(parents=True)
    (pending / "one.json").write_text("{}", encoding="utf-8")
    (pending / "two.json").write_text("{}", encoding="utf-8")

    cron = hermes_home / "cron"
    cron.mkdir(parents=True)
    (cron / "jobs.json").write_text(
        json.dumps(
            {
                "jobs": [
                    {
                        "id": "healthy",
                        "name": "Vault 自动 git 同步",
                        "enabled": True,
                        "last_status": "ok",
                        "failure_streak": 0,
                        "script": "vault_git_auto_sync.py",
                    },
                    {
                        "id": "failed",
                        "name": "Memory Bus 上下文同步",
                        "enabled": True,
                        "last_status": "error",
                        "failure_streak": 4,
                        "script": "memory_bus_bridge.py",
                    },
                    {
                        "id": "unrelated",
                        "name": "天气提醒",
                        "enabled": True,
                        "last_status": "error",
                        "failure_streak": 9,
                    },
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    details, warnings = memory_guardian.inspect_hermes_memory_runtime(hermes_home)

    assert details["pending_memory_writes"] == 2
    assert details["enabled_memory_jobs"] == 2
    assert details["failing_memory_jobs"] == [
        {
            "id": "failed",
            "name": "Memory Bus 上下文同步",
            "last_status": "error",
            "failure_streak": 4,
        }
    ]
    assert warnings == [
        {
            "severity": "review",
            "source": "hermes_local",
            "message": "发现 2 条待审批内置记忆写入；需用户逐条批准或拒绝，禁止自动应用",
        },
        {
            "severity": "critical",
            "source": "hermes_local",
            "message": "记忆相关定时任务连续失败：Memory Bus 上下文同步 (failed, status=error, streak=4)",
        },
    ]


def test_build_health_includes_hermes_runtime_findings(monkeypatch) -> None:
    def fake_inventory(name: str, _root: Path) -> dict:
        base = {
            "exists": True,
            "file_count": 1,
            "bytes": 1,
            "newest_mtime": "2026-08-30T00:00:00+08:00",
            "missing_core": [],
            "exact_duplicate_groups": [],
        }
        if name == "dsh_tencent":
            base.update(vectors_db_quick_check="ok", temporary_files=[])
        if name == "codex_auto":
            base.update(git_remote="private", recovery_bundle=None)
        if name == "shared_vault":
            base.update(deprecated_candidates=[])
        return base

    runtime_details = {
        "pending_memory_writes": 1,
        "enabled_memory_jobs": 3,
        "failing_memory_jobs": [],
    }
    runtime_warning = {
        "severity": "review",
        "source": "hermes_local",
        "message": "pending",
    }
    monkeypatch.setattr(memory_guardian, "source_inventory", fake_inventory)
    monkeypatch.setattr(memory_guardian, "content_review_section", lambda: ([], {}))
    monkeypatch.setattr(
        memory_guardian,
        "inspect_hermes_memory_runtime",
        lambda _home: (runtime_details, [runtime_warning]),
    )

    health = memory_guardian.build_health()

    assert health["sources"]["hermes_local"]["runtime"] == runtime_details
    assert runtime_warning in health["warnings"]
    rendered = memory_guardian.render_markdown(health)
    assert "Hermes 内置记忆：待审批 1 条，启用记忆任务 3 个，失败任务 0 个。" in rendered
