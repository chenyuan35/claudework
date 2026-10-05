---
name: motion-graphics
description: >
  Use when the user wants a short, design-led motion graphic where motion is the
  message: kinetic typography, stat or number count-up, chart/data-viz hit,
  logo sting, brand lockup, lower-third, callout, social overlay, animated
  headline/tweet/news item, motion poster, or quick captured-page highlight.
  Usually under 10s and up to ~30s, with no narration arc, voice-over, or
  live-action subject. Can render to MP4 or transparent overlay. Not for longer,
  multi-scene, narrated, or brand-reel pieces (use general-video), narrated
  website videos (website-to-video), topic explainers
  (faceless-explainer), product promos (product-launch-video), PR videos
  (pr-to-video), or captions on existing footage (embedded-captions). When unsure whether it's a
  quick motion-first piece or a longer / narrated treatment, see /hyperframes.
metadata:
  {
    "tags": "orchestrator, motion-graphics, kinetic-type, data-viz, logo-reveal, lower-thirds, news, tweet, webpage, asset-fusion, short-form, overlay, no-narration",
  }
---

# motion-graphics — dispatch entry

> **Confirm the route before Step 0.** This skill makes a **short, design-led, unnarrated motion graphic** (motion is the message; ~under 10s, no voice-over). A **longer, multi-scene, or narrated** treatment → `/general-video`; a **narrated video of a website** → `/website-to-video`; a **topic explainer** → `/faceless-explainer`; a **product promo** → `/product-launch-video`; **captions on existing footage** → `/embedded-captions`. **Out of scope**: live / at-render-time data, or footage it can't capture. Unsure motion-first-vs-narrated? **Read `/hyperframes` first.**

A short design-led motion graphic. **Asset-first**: decide the asset strategy and source real material _before_ designing the shot, then design the shot around what you have, then compose by reusing catalog capabilities. All artifacts go to `PROJECT_DIR = videos/<project-name>/` (created in Step 0); all paths below are relative to it.

| Phase    | Execution                                                             | Primary artifact                                                 | Detailed flow                 |
| -------- | --------------------------------------------------------------------- | ---------------------------------------------------------------- | ----------------------------- |
| init     | Bash                                                                  | `hyperframes.json`                                               | Step 0                        |
| plan     | subagent — **decide search?** + classify + asset strategy             | `shot-plan.json` (draft: category, `asset_needs` queries, brief) | `agents/director.md` (Part 1) |
| source ◇ | Bash — media-use resolve (**skip if `asset_needs` is empty**)         | `assets/` + `assets/index.md`                                    | `phases/source/guide.md`      |
| design   | subagent — shot design around resolved assets                         | `shot-plan.json` (final: block(s) + layout + motion + positions) | `agents/director.md` (Part 2) |
| build    | subagent — reuse-first composition                                    | `compositions/index.html`                                        | `agents/builder.md`           |
| render   | Bash — `hyperframes render` (MP4, or `--format webm/mov` for overlay) | `renders/video.mp4`                                              | Step 5                        |
| verify   | Bash — `lint` / `inspect` -> repair subagent on failure               | (fixes in place)                                                 | `agents/finalize.md`          |

`◇ source` runs only when the chosen category declares assets. Pure code/text categories (e.g. `kinetic-type`, most `charts`/`stat`) have `asset_needs: []` and skip straight from plan to design.

## Categories — split by the search decision

`plan`'s **first decision is: does this need a search?** That fork splits the categories into two groups; then the specific category is picked — for search-driven, **by the type of content the search returns**. Each category is one `categories/<id>/module.md` (its planning + build rules); the shared motion vocabulary lives in `references/motion-vocabulary.md` (→ `hyperframes-animation` rules/blueprints + registry blocks).

**Form categories — no search; the user supplies the content:**

| Category       | Intent                                         | Leans on                                                                    |
| -------------- | ---------------------------------------------- | --------------------------------------------------------------------------- |
| `kinetic-type` | punchy line / quote / title, motion-first text | `caption-*` blocks + animation rules                                        |
| `stat`         | single hero number / count-up + ring           | `apple-money-count` / `rules/{counting-dynamic-scale, stat-bars-and-fills}` |
| `charts`       | bar / line / pie / race / % from data          | `data-chart` block                                                          |
| `logo-reveal`  | logo sting / brand lockup (user logo)          | `logo-outro` / `rules/svg-path-draw`                                        |
| `lower-thirds` | name / title bars, callouts, social overlays   | `caption-*` + registry overlay blocks                                       |

**Search-driven categories — search first, then animate by content type** (the RWA path):

| Returned content | Category       | Animation                                                      |
| ---------------- | -------------- | -------------------------------------------------------------- |
| webpage / link   | `webpage`      | webpage / UI animation (scroll, reveal, cursor, callouts)      |
| news article     | `news`         | headline reveal + source card + key-fact callouts              |
| tweet            | `tweet`        | animated tweet card                                            |
| image / entity   | `asset-fusion` | the asset's geometry _becomes_ the chart (RWA diegetic fusion) |

Build order: one at a time, coverage-first (rough is fine). `kinetic-type` ported from the prototype; the rest follow.

## Prerequisites

macOS Apple Silicon or Linux x64. System tools: `brew install node ffmpeg`. `npx hyperframes doctor` once. macOS GPU render: `export PRODUCER_BROWSER_GPU_MODE=hardware`.

Optional keys (local fallbacks if unset) — only needed by categories that source/generate assets via media-use:

| Key                                 | Used for                                                    | Fallback                        |
| ----------------------------------- | ----------------------------------------------------------- | ------------------------------- |
| `GEMINI_API_KEY` / `GOOGLE_API_KEY` | image generation (media-use resolve)                        | skip generate / search-only     |
| (asset_scout / search providers)    | `webpage`/`news`/`tweet` + `asset-fusion` real-asset search | category degrades to asset-free |

## Flow

### Step 0 — Initialize

cwd is the agent workspace root; write all artifacts under `PROJECT_DIR = videos/<project-name>/`. `<project-name>`: use the dir the user gave, else a short kebab-case name from the intent (`<subject>-motion`). Not the workspace basename or a timestamp.

Only when `$PROJECT_DIR/hyperframes.json` is absent:

```bash
PROJECT_DIR="${MOTION_GRAPHICS_DIR:-videos/<project-name>}"
mkdir -p "$(dirname "$PROJECT_DIR")"
npx hyperframes init "$PROJECT_DIR" --non-interactive --example=blank
```

`init` checks the installed skills against the latest on GitHub and updates the global set if any are out of date.

**Constraints:** never `hyperframes init` in the workspace root; never nest another `hyperframes/` inside `PROJECT_DIR`; every Bash command (master + subagents) is a `(cd "$PROJECT_DIR" && ...)` subshell — never bare `cd`.

### Step 1 — Plan (subagent: Director Part 1)

Dispatch one subagent. prompt = full `agents/director.md` + `## Dispatch context` (`SKILL_DIR` / `PROJECT_DIR` / the user's request / `Schema: <SKILL_DIR>/references/shot-plan-ir.md`). It must:

1. **Decide: does this need a search?** (the first fork)
   - **No** → pick a **form category** (kinetic-type / stat / charts / logo-reveal / lower-thirds); content is user-supplied; `asset_needs: []`.
   - **Yes** → emit a **search plan** into `asset_needs[]` (news / web / tweet / image; two-pole queries). The specific **search-driven category** (webpage / news / tweet / asset-fusion) is confirmed by the content type returned in Step 2, and finalized in Step 3.
2. Write a draft `shot-plan.json` (envelope + chosen form category _or_ search intent + `asset_needs` + a one-paragraph shot brief). Schema: `references/shot-plan-ir.md`.

Validation: `[ -s "$PROJECT_DIR/shot-plan.json" ] && echo ok || echo missing`.

### Step 2 — Source ◇ (Bash: media-use, conditional)

If `shot-plan.json.asset_needs` is non-empty, resolve assets (search / generate / fetch → frozen project-local paths + ledger). See `phases/source/guide.md` (wraps `media-use resolve`; the search-driven categories use the news/web/tweet/image search). If `asset_needs` is empty, **skip to Step 3**.

```bash
# illustrative — see phases/source/guide.md
(cd "$PROJECT_DIR" && node <SKILL_DIR>/phases/source/resolve.mjs --plan ./shot-plan.json --out ./assets)
```

Degrade gracefully: if a search/provider is unavailable, the category falls back to asset-free (note it in `context.log`).

### Step 3 — Design (subagent: Director Part 2)

Dispatch a subagent (prompt = `agents/director.md` Part 2 + dispatch context including the resolved `assets/index.md` if Step 2 ran + `catalog-map.md`). It designs the shot **around the available assets**: pick the catalog block(s) + the `hyperframes-animation` rules/blueprints, the layout, the motion, beats, and (for `asset-fusion`) the `element_positions` + eyedropper palette. Finalizes `shot-plan.json` (`content.block` + `content.customize` + per-category content).

### Step 4 — Build (subagent: Builder, reuse-first)

Dispatch a subagent. prompt = full `agents/builder.md` + dispatch context (`shot-plan.json`, `catalog-map.md`, the category's `module.md`, `references/motion-vocabulary.md`, `references/builder-contract.md`). **Reuse-first**: `npx hyperframes add <block>` + customize in place; hand-author only gaps + the asset-fusion affordance. Output `compositions/index.html` honoring the HF contract (paused GSAP timeline on `window.__timelines`, `class="clip"` + stable ids, `tl.seek(0)`, deterministic).

### Step 5 — Render (Bash)

```bash
(cd "$PROJECT_DIR" && npx hyperframes render . --skill=motion-graphics -q draft -o ./renders/video.mp4)
# transparent overlay variant: --format webm  (or mov)
```

### Step 6 — Verify (Bash → repair subagent on failure)

```bash
(cd "$PROJECT_DIR" && npx hyperframes lint . && npx hyperframes inspect .)
```

exit 0 → done. On lint/inspect errors, dispatch the repair subagent (`agents/finalize.md`: snapshot QA + one in-place fix pass + re-render). Never change a fixed duration in repair.


🔴 完成后：必须执行下方「复盘」流程（定位根因→修复→量纲检查→分支检查门→验证→异常表）。
### Report + optional preview

Report the final output (`renders/video.mp4`, or the `.webm` / `.mov` overlay variant) + duration. **Don't open a preview during the run.** Offer one only on request, started **after** render so it serves the final file:

```bash
(cd "$PROJECT_DIR" && npx hyperframes preview)   # Studio UI; or `npx hyperframes play` for a shareable link
```

Flags live in the `hyperframes-cli` skill (`references/preview-render.md`).

## Resume table

| State                                                    | Continue from            |
| -------------------------------------------------------- | ------------------------ |
| no `shot-plan.json`                                      | Step 1 (plan)            |
| `shot-plan.json` has `asset_needs`, no `assets/`         | Step 2 (source)          |
| `shot-plan.json` final, no `compositions/index.html`     | Step 3/4 (design+build)  |
| `compositions/index.html` exists, no `renders/video.mp4` | Step 5 (render) + Step 6 |
| `renders/video.mp4` exists                               | Report + stop            |

## Design notes (maintainers — execution does not read this)

- **Asset-first rationale:** sourcing is front-loaded and informs shot design (the RWA flow: analyze → search → review → compose). the search-driven categories (`webpage`/`news`/`tweet`) and `asset-fusion` both lean on media-use search (news/web/tweet/image), which is media-use's documented RWA lineage.
- **Reuse-first:** the in-ecosystem analog of LLM-generated templates is "compose catalog blocks + `hyperframes-animation` rules". HF's paused GSAP timeline ≙ Remotion's `useCurrentFrame`.
- **Category module contract:** one `categories/<id>/module.md` (planning + build), sharing `references/motion-vocabulary.md` (+ optional eval). Adding a category = drop the folder + register its classifier line in `agents/director.md` + its row in `catalog-map.md`; the phase pipeline is untouched.
- **Directory shape:**
  ```
  videos/<project-name>/
    hyperframes.json  context.log
    shot-plan.json            # the IR (Director output)
    assets/  assets/index.md  # media-use output (if sourced)
    compositions/index.html   # Builder output
    renders/video.mp4
  ```
- **Registration:** in `hyperframes` router — add the "design-led short motion graphic" intent + Workflow description; carve the motion-graphics triggers out of `/general-video`; add reverse Do-NOT-use edges. See `motion-graphics-genre.md` §5-7.

# 第1步：检查坐标表中每个命令在当前环境是否可执行
# 第2步：扫描残留文件
ls _csdn_*.js _csdn_*_loader.js _csdn_b64*.js 2>/dev/null && echo "⚠️ 残留文件未清理" || echo "✅ 无残留"
# 第3步：检查中文验收步骤是否在注入后位置
# 第4步：确认所有 base64 解码使用 TextDecoder，无裸 atob
grep -n "atob" SKILL.md | grep -v "TextDecoder" && echo "⚠️ 裸 atob 存在" || echo "✅ 无裸 atob"
# 第5步：确认无 HTTP server fetch 残留
grep -q "fetch.*localhost" SKILL.md && echo "⚠️ HTTP fetch 残留" || echo "✅ 无 HTTP fetch"
```

---

## 技能执行复盘（仅在触发时执行，整条 SOP 的最后一步）

本节不是例行仪式。产物验收一次通过、实际执行与 SOP 一致、无人工绕过或用户纠正、无可避免等待且未超过 20 分钟时，直接交付，不复盘、不输出“无修改”、不改文件。

只有出现技术报错或验证失败、流程偏移或模糊分支、质量返工、重复调用或可避免超时、用户指出目标偏移时，才执行一次全面闭环：读取日志和产物证据，检查技术、质量、效率、流程偏移和下次复用性，定位唯一根因；直接替换现有 SKILL.md 或脚本中的失效步骤，删除冲突旧写法；完成真实渲染或产物复验后继续交付。不得生成复盘文件或报告。
