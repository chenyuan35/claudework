---
name: claude-skill-layout
description: Audit, consolidate, verify, or roll back Claude Code personal and project Skill directories on this Windows machine. Use when Claude Skills are scattered between C:\Users\59314\.claude\skills and C:\Users\59314\claudework\.claude\skills, duplicate names override each other, or the user wants claudework to hold the canonical copies without breaking global discovery.
---

# Claude Skill layout

Use `scripts/consolidate_claude_skills.ps1` as the only mechanical owner.

## Invariants

- Treat `C:\Users\59314\claudework\.claude\skills` as the physical canonical store.
- Preserve `C:\Users\59314\.claude\skills` as Claude's personal discovery path by replacing each migrated child with a directory junction to its canonical child.
- Do not move or merge `.agents\skills`, `.codex\skills`, plugin caches, or AppData. They belong to different loaders. Preserve any pre-existing valid junction from the Claude personal root into one of those stores.
- Personal Skills currently override same-name project Skills. Preserve current behavior by making the currently effective personal copy canonical; back up every replaced project copy first.
- Never overwrite a divergent directory without a complete backup and manifest.
- Never delete physical Skill directories during migration. Use verified moves and junctions only.
- Do not read or store credentials, tokens, cookies, or session files.

## Workflow

1. Run `-Action Audit` and record physical personal entries, canonical junctions, external shared junctions, project entries, and physical name conflicts.
2. Run `-Action Migrate`. Keep the returned backup path.
3. Run `-Action Verify -BackupPath <path>`.
4. Verify Claude still sees one personal entry for a migrated Skill and the project copy remains readable.
5. If any check fails, run `-Action Rollback -BackupPath <path>`.

## Acceptance

- Every migrated personal Skill path is a junction whose target is the same-name child under the canonical claudework root; pre-existing valid shared-store junctions remain unchanged.
- Every canonical target contains `SKILL.md`.
- Project-only Skills remain untouched.
- The backup contains the original personal Skills, every replaced project directory, and `manifest.json`.
- Audit reports no physical directory remaining directly under the personal Skill root.
