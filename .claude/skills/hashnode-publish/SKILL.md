---
name: hashnode-publish
description: "Publish an English article to the Dispatch blog (hashnode) — full automation, no prompts"
---

# /hashnode-publish

Publish an English article to [Dispatch](https://dispatch-blog.hashnode.dev) (@chenyuan20509). API write operations require Pro plan; current account is free tier → **Playwright browser publish only**.

**🔴 全自动原则：用户只调用技能（不提供内容）→ 由 Claude 根据发布历史和系列方向自动选题、生成文章、发布。不得询问用户"要写什么"。**

## Account
- **Blog**: dispatch-blog.hashnode.dev | Publication ID: `6a52596293afb923755ae966`
- **RSS**: `curl -s "https://dispatch-blog.hashnode.dev/rss.xml" | grep -oP "<title>.*?</title>" | tail -n +2`

## Quality gates (all must pass before publish)
- word count ≥ 1,200
- H2 headings ≥ 6
- code blocks ≥ 3
- cover image set (Cover → Unsplash → pick first result)
- tags ≥ 5 (Draft settings → Discovery tab)
- no banned words: delve/leverage/landscape/seamless/elevate/empower/unlock/dive into/in conclusion/testament

## Content pattern audit (2026-07-17 — execute before writing)

1. Read publish log and check recent 3 articles:
   - **Opening style**: Are ≥2 using the same opening type? (anecdote / data / quote / question / bold claim)
   - **Structure**: Are ≥2 following the same section structure? (problem→solution / compare→contrast / how-to / case study)
   - **Topic cluster**: Are ≥2 from the same subtopic? (security / LLM / tooling / deployment)
2. If any dimension hits threshold → the new article must differ in that dimension.
   - E.g. last 2 both started with anecdotes → next must open with data or a question.
3. This checks prevents the "same template, different title" pattern.

## Execution flow

**0. Content generation (if no article provided)** — When user invokes `/hashnode-publish` without explicit article content:
  - Read publish log to determine current series direction.
  - Continue the series with a natural next topic (narrative arc).
  - Generate article content meeting all quality gates (≥1200 words, ≥6 H2, ≥3 code blocks, no banned words).
  - Cover Unsplash keyword from mapping below.
  - Tags from MCP/AI Engineering tag set.

**1. Dedup** — check RSS for title collision.

**2. Login** — `browser_navigate("https://hashnode.com/")` — confirm `button "Write"` in sidebar (avatar present = logged in).

**3. New draft** — click sidebar `Write` (it opens a *previously-edited* draft, NOT blank) → then click the toolbar **New** button (`Array.from(document.querySelectorAll('button')).find(b => b.textContent.trim()==='New')`) to open a blank draft. Confirm `tab "Markdown"` selected (click `tab "Markdown"` if not active).

**4. Title** — `getByRole('textbox', { name: /Article Title/i })` → click → fill full title.

**5. Body** — `getByRole('textbox', { name: /start writing markdown/i })` → click → `browser_type` full body (H1 omitted; title is separate). Verify body word count ≥ 1,200 via `browser_evaluate` on the textarea value; if under → exit.

**6. Cover** — click `button "Cover"` → click `tab "Unsplash"` (must be active; click by ref if panel doesn't switch) → set search via `browser_evaluate` using native setter + dispatch `input` event on `input[placeholder="Search Unsplash photos..."]` (do NOT use `browser_type` — it throws CSS-selector parse error). Wait ~3s for results → click first `button:has(img[src*="images.unsplash.com"])`. Keyword: 'cybersecurity' (MCP/security), 'server room' (MCP/deploy), 'artificial intelligence' (AI/LLM), 'programming code' (engineering). Confirm dialog closes and "Change cover"/"Delete cover" buttons appear.

**7. Publish** — click `button "Publish"` (toolbar) → Draft settings dialog opens (4 tabs). Click `tab "Discovery"`. In the Tags textbox (`placeholder="Type to add tags"`) add each tag: type the tag text, then **click the exact `#tagN posts` suggestion button** rendered as a document-level portal (filter `document.body` buttons by `^#<tag>\d`). Synthetic Enter does NOT commit — must click the suggestion. Tags: `ai, programming, llm, software-engineering, opensource` (AI Engineering series; the MCP series variant `security` replaces `software-engineering`). → click `button "Publish"` in dialog footer. URL changes to `/edit/...` = success.

**8. Verify + Retro (2026-07-17)** — `browser_navigate("https://dispatch-blog.hashnode.dev")` → confirm the new title appears in Latest articles (check via `document.body.innerText.includes(title)`).

> **复盘按 CLAUDE.md 技能修复标准流程执行**

Then answer:

## Selectors

| Element | Selector |
|---------|----------|
| Write sidebar | `getByRole('listitem').filter({ hasText: 'Write' }).getByRole('button')` |
| New toolbar | `getByRole('button', { name: 'New' })` |
| Title | `getByRole('textbox', { name: /Article Title/i })` |
| Body | `getByRole('textbox', { name: /start writing markdown/i })` |
| Cover button | `getByRole('button', { name: 'Cover' })` |
| Unsplash tab | `getByRole('tab', { name: 'Unsplash' })` |
| Unsplash search | `getByRole('textbox', { name: /search unsplash/i })` |
| Unsplash first result | `page.getByRole('button').filter({ has: page.locator('img[src*="images.unsplash.com"]') })` |
| Publish (toolbar) | `getByRole('button', { name: 'Publish' }).first()` |
| Publish (dialog) | `getByRole('button', { name: 'Publish' }).last()` |
| Discovery tab | `getByRole('tab').nth(1)` |
| Markdown tab | `getByRole('tab', { name: 'Markdown' })` |
| Update button | `getByRole('button', { name: 'Update' })` |

## Known issues (from live runs — extra cautions only)

- **Cover target must be Unsplash**: the "Change cover"/"Delete cover" buttons confirm the cover is set; the uploaded cover URL is `cdn.hashnode.com/uploads/covers/...`.
- **Exact-tag suggestion format**: the document-level suggestion button text is `#<tag><N posts>` (e.g. `#programming0 posts`, `#llm5,660 posts`). Variants like `#llmops` are different tags — pick the exact `#<tag>` match. Confirmed tag set for the AI Engineering series: `#ai #programming #llm #software-engineering #opensource`.

## Platform research
See `references/platform-research.md` for head account benchmark data and dialog structures.

## Publish log

| # | Title | Words | Cover | Tags | Date |
|---|-------|-------|-------|------|------|
| 1 | The Thing Nobody Tells You About Running MCP Servers Remotely | — | ❌ | ❌ | 2026-07-11 |
| 2 | I Built an MCP Server in an Afternoon. Here's What Surprised Me. | — | ❌ | ❌ | 2026-07-11 |
| 3 | I Exposed My MCP Server to the Internet. Bad Idea. | 667 | ❌ | ❌ | 2026-07-13 |
| 4 | I Locked Down My MCP Server After the Internet Found It | — | ❌ | ❌ | 2026-07-14 |
| 5 | My MCP Server Worked in Dev. It Died in Production. Here's the Difference. | 1504 | ✅ | ✅ ai,programming,llm,software-engineering,opensource | 2026-07-16 |
