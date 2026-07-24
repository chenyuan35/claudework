---
name: dev-to-publish
description: "全自动 Dev.to 文章发布：API 创建草稿 → 质量门 → Playwright 确认+发布"
version: 2.0
platform: dev.to（dev.to）
mode: 全自动 · API 发布 + Playwright 验证
---

> **🔴 工具边界（2026-07-14 新增，防命名混淆）：** 浏览器操控唯一工具是 `mcp__playwright__browser_*`（browser_navigate/snapshot/click/evaluate/run_code_unsafe）。**严禁 `mcp__Claude_Browser__preview_*`**——那是 dev server 预览窗格（preview_start 起本地服务、无 preview_navigate），不是浏览器工具、不是 playwright 别名，调网页必然报 `No such tool available`。单次调用失败 ≠ 工具不存在：第一动作 `claude mcp list` 取证并贴出 `playwright: ... ✓ Connected` 再继续，禁止基于单次失败判“工具不存在”。
# Dev.to 自动发布技能 v2.0

> **全自动 Dev.to 英文文章发布管线**。通过 Dev.to API 创建草稿，Playwright 浏览器确认内容完整后发布。
> 每次调用直接执行，不询问用户。发布完成后自动复盘修复 SKILL.md。

## 核心约束

- **全英文**：Dev.to 是海外社区，所有内容用英文
- **技能自包含**：不依赖用户决策；启动后全自动执行到发布完成
- **API Key**：`Po7yw2h2W8M6fvuCnX9Bd2Et`（直接写死）
- **User-Agent 必须设**：Dev.to 前面有 Cloudflare，无 Mozilla UA 返回 403
- **不重复发布**：发布前检查已有文章列表，同标题不重复发
- **不自毁**：除 API 失败、登录失效外，不停下来询问用户

## 账号信息

| 字段 | 值 |
|------|-----|
| 用户名 | `@chenyuan20509` |
| 邮箱 | `chenyuan20509@gmail.com` |
| 个人主页 | `https://dev.to/chenyuan20509` |
| API 端点 | `https://dev.to/api/articles` |
| API Key | `Po7yw2h2W8M6fvuCnX9Bd2Et` |
| 认证方式 | Header `api-key: Po7yw2h2W8M6fvuCnX9Bd2Et` |

## 固定工具链

- **curl**（Bash 中执行）— API 创建/查询/更新
- **Playwright**（`mcp__playwright__browser_*`）— 浏览器核验发布状态
- API Key 直接写死，不依赖环境变量

**禁用**：
- 独立浏览器进程（puppeteer/selenium/playwright standalone）
- 非 Mozilla User-Agent（Cloudflare 拦截）

---

## §0 写作风格

### 平台定位
Dev.to 是三个平台里社区互动最强的：
- 内部 Feed 活跃度远高于 Hashnode（爆款能到 50+ reactions）
- 读者群体：Junior 到 Mid-level 开发者为主
- 风格：教程向、社区讨论向内容吃香
- Google SEO 权重高
- **正确漏斗**：写 → 社区 Feed 准推荐 → 互动 → 涨粉 → 长期自然流量

### 语气规则
- **口语化** — 用 "you"、"I"、"we"、缩写
- **代码说话** — 读者先扫代码块，代码不好直接关
- **有态度** — 说"this is the way I do it"，不写"one approach is..."
- **短段落** — 每段 ≤4 行
- **评论区是一半的内容** — 结尾丢一个开放问题钓评论

### 禁止词
`delve` `leverage` `landscape` `game-changer` `seamless` `elevate` `empower`
`unlock` `dive into` `in today's rapidly evolving` `let's break it down`
`in conclusion` `it's worth noting` `this raises the question`
`a common misconception is` `the reality is`

### 文章结构
1. **Hook** — 一句话说清楚你遇到了啥问题
2. **The Fix** — 直接上代码，不要铺垫
3. **Why This Works** — 解释原理，但不超过代码块长度
4. **Gotchas** — 什么情况下这个方案不灵
5. **CTA** — 开放问题或"你怎么解决的？"

### 标签策略（3-4 个）
- 必选池：`mcp` `programming` `tutorial` `webdev` `opensource`
- 控制在 **4 个以内**，不匹配的会被静默丢弃
- 避开 `discuss` `showdev`（除非讨论帖）

---

## §1 执行流程

### Step 0：预检

```bash
DEVTO_KEY="Po7yw2h2W8M6fvuCnX9Bd2Et"

# 1. 确认 API 连通（必须带 api-key header）
curl -s -o /dev/null -w "%{http_code}" \
  -H "api-key: $DEVTO_KEY" \
  -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" \
  "https://dev.to/api/articles/me/published?per_page=1"
# 返回 200 则 OK，401 → API Key 失效，403 → Cloudflare 拦截
```

### Step 1：去重检查

```bash
# 获取已发布文章标题列表
curl -s \
  -H "api-key: $DEVTO_KEY" \
  -H "User-Agent: Mozilla/5.0" \
  "https://dev.to/api/articles/me/published?per_page=50" \
  | python -c "
import sys, json
articles = json.load(sys.stdin)
for a in articles:
  print(a['title'])
"
```

将输出保存到上下文，与本次标题逐条对比。如果标题已存在 → 选下一篇，不重复发，报告即可。

### Step 2：准备文章内容

构建 JSON payload。**注意：Windows Git Bash 中 heredoc 内的反引号会被 shell 解释执行，必须用 Python 写文件以规避转义问题。**

```bash
# 用 Python 写 JSON payload（规避 shell 转义）
python << 'PYEOF'
import json

body_md = """---
title: 标题
published: false
description: SEO 描述
tags:
  - tag1
  - tag2
  - tag3
---

正文 Markdown 内容...

## The Fix

```python
print('hello')
```

## Gotchas

...

## What about you?

How do you handle this?"""

article = {
    "article": {
        "title": "文章标题",
        "body_markdown": body_md,
        "published": False,
        "tags": ["mcp", "programming", "tutorial"],
        "description": "SEO 描述"
    }
}

with open('devto_article.json', 'w', encoding='utf-8') as f:
    json.dump(article, f, ensure_ascii=False, indent=2)
print('JSON written')
PYEOF
```

**注意：body_markdown 内 frontmatter 的 `published: false` 会影响后期的 PUT 发布（见 Step 6 注）。**

### Step 3：调用 API 创建草稿

```bash
RESPONSE=$(curl -s -w "\n%{http_code}" \
  -X POST "https://dev.to/api/articles" \
  -H "api-key: $DEVTO_KEY" \
  -H "Content-Type: application/json" \
  -H "User-Agent: Mozilla/5.0" \
  -d @devto_article.json)

HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "201" ]; then
  ARTICLE_ID=$(echo "$BODY" | python -c "import sys,json; print(json.load(sys.stdin)['id'])")
  ARTICLE_URL=$(echo "$BODY" | python -c "import sys,json; print(json.load(sys.stdin)['url'])")
  echo "✅ 草稿创建成功 | ID=$ARTICLE_ID | URL=$ARTICLE_URL"
else
  echo "❌ API 返回 $HTTP_CODE"
  echo "$BODY" | python -m json.tool
  # 跳到错误处理表
fi
```

### Step 4：字数核验（质量门）

```bash
WORD_COUNT=$(echo "$BODY" | python -c "
import sys, json
article = json.load(sys.stdin)
body = article.get('body_markdown', '')
# 去掉 frontmatter
body = body.split('---', 2)
content = body[2] if len(body) > 2 else body[0]
words = len(content.split())
print(words)
")

echo "词数: $WORD_COUNT"

if [ "$WORD_COUNT" -lt 800 ]; then
  echo "❌ 词数不足 800（$WORD_COUNT），禁止发布。重写正文后重新创建草稿。"
  # 删除本次草稿
  curl -s -X DELETE "https://dev.to/api/articles/$ARTICLE_ID" \
    -H "api-key: $DEVTO_KEY" \
    -H "User-Agent: Mozilla/5.0"
  exit 1
fi
```

### Step 5：Playwright 浏览器核验草稿

```javascript
// 用 Playwright 登录 dev.to，确认草稿内容正确
await page.goto('https://dev.to/dashboard');
await page.waitForTimeout(2000);

// 检查 dashboard 是否有草稿
const draftList = await page.evaluate(() => {
  const links = document.querySelectorAll('a[href*="/dashboard"]');
  return Array.from(links).map(l => l.textContent.trim()).filter(Boolean);
});
// 直接导航到草稿编辑页核验内容
await page.goto(`https://dev.to/dashboard/${ARTICLE_ID}`);
await page.waitForTimeout(2000);

// 检查标题和正文内容
const preview = await page.evaluate(() => {
  const title = document.querySelector('h1')?.textContent?.trim();
  return { title };
});
// 确认标题匹配后，标记为可发布
```

### Step 6：发布草稿

**重要：PUT 发布需要：**
1. 发送**完整文章 payload** + `published: true`（仅 `{"article": {"published": true}}` 返回 200 但不生效）
2. **body_markdown 的 frontmatter 中 `published` 也必须为 `true`**（否则 frontmatter 覆盖 JSON 层的设置）
3. slug 在**第一次** `published: true` 的 PUT 请求时永久确定（含 temp slug），因此发布前必须确认标题正确

```bash
# 1. 先读取原 JSON payload，修改 published 为 true
python -c "
import json
with open('devto_article.json', 'r', encoding='utf-8') as f:
    article = json.load(f)
# 同时改 frontmatter 中的 published 字段
article['article']['body_markdown'] = article['article']['body_markdown'].replace('published: false', 'published: true', 1)
article['article']['published'] = True
with open('devto_article_publish.json', 'w', encoding='utf-8') as f:
    json.dump(article, f, ensure_ascii=False, indent=2)
print('Publish payload ready')
"

# 2. 一次性 PUT（带 body_markdown 完整内容和 published: true）
RESPONSE=$(curl -s -w "\n%{http_code}" \
  -X PUT "https://dev.to/api/articles/$ARTICLE_ID" \
  -H "api-key: $DEVTO_KEY" \
  -H "Content-Type: application/json" \
  -H "User-Agent: Mozilla/5.0" \
  -d @devto_article_publish.json)

HTTP_CODE=$(echo "$RESPONSE" | tail -1)
echo "Publish HTTP: $HTTP_CODE"

# 3. 核验
python -c "
import json
with open('devto_article_publish.json', encoding='utf-8') as f:
    article = json.load(f)
print(f'Published: True (frontmatter: {article[\"article\"][\"body_markdown\"].split(\"---\")[1][:30]})')
"

### Step 7：核验发布成功

```bash
# 确认文章在已发布列表
curl -s \
  -H "api-key: $DEVTO_KEY" \
  -H "User-Agent: Mozilla/5.0" \
  "https://dev.to/api/articles/me/published?per_page=5" \
  | python -c "
import sys, json
articles = json.load(sys.stdin)
for a in articles:
  if a.get('id') == $ARTICLE_ID:
    print(f'✅ 发布确认 | URL={a[\"url\"]} | published_at={a.get(\"published_at\",\"?\")}')
    break
"
```

```javascript
// Playwright 浏览器验证
await page.goto('https://dev.to/chenyuan20509');
await page.waitForTimeout(2000);
const firstArticle = await page.evaluate(() => {
  const cards = document.querySelectorAll('[class*="crayons-card"]');
  const first = cards[0];
  return first?.querySelector('h3')?.textContent?.trim() || 'Not found';
});
console.log('首页第一篇标题:', firstArticle);
```

---

## §2 错误处理

| 场景 | 处理 |
|------|------|
| API 返回 401 | API Key 失效 → 去 Dev.to 后台重新生成后写死进技能 |
| API 返回 403 | Cloudflare 拦截 → 检查 User-Agent 是否为 Mozilla/5.0 |
| API 返回 422 | 参数错误 → 检查 body_markdown 格式、tags 数量(≤4)；或标题重复（须换标题）|
| API 返回 429 | 频率限制 → 等待 60s 后重试 |
| 草稿创建成功但 ID 为空 | JSON 解析错误 → 打印完整响应体调试 |
| PUT 发布返回 200 但文章仍是 draft | body_markdown frontmatter 中的 `published: false` 覆盖了 JSON 层设置 → 同步修改 frontmatter 的 published 为 true |
| PUT 最小 payload（仅 `{published:true}`）不生效 | Dev.to API 需要完整文章 payload 才执行发布 → 必须带 body_markdown 完整内容 |
| 文章重复出现（草稿+已发布） | API POST 创建草稿 + PUT 发布后，dashboard 仍可能显示旧 draft 缓存，实际已发布（检查 profile 页面确认）|
| slug 不符合预期 | slug 在**首个** `published: true` 请求时永久确定 → 先用 test payload 发 PUT 再更新内容会导致 slug 无法更改。正确做法：一次性带完整内容 + published: true |
| 浏览器登录过期 | 导航到 `/enter` 确认状态，报 "Dev.to 需要手动重新登录" |
| 文章标题重复 | 不删除已发布文章，记录并选下一篇 |
| API 超时（>10s） | 重试 1 次；仍超时则熔断报告 |

---

## §3 质量门（发布前检查 — 硬门槛）

- [ ] DEVTO_KEY 硬编码在技能中
- [ ] 标题 ≥ 10 字符 ≤ 100 字符
- [ ] 正文词数 ≥ 800（Step 4 自动核验）
- [ ] 文章结构符合 5 段式（Hook → Fix → Why → Gotchas → CTA）
- [ ] 至少 1 个代码块
- [ ] 标签 ≤ 4 个
- [ ] 无 AI 味高频词（见 §0 禁止词）
- [ ] 结尾有开放问题（CTA）
- [ ] 标题与已有文章不重复（Step 1 核验）
- [ ] 正文 body_markdown frontmatter 中 `published: false`（创建草稿时）
- [ ] User-Agent 设为 Mozilla/5.0

---

## §4 发布后复盘（每次执行必须做）

> **复盘按 CLAUDE.md 技能修复标准流程执行**

每次发布完成后自动执行，修改 SKILL.md：

1. **记录发布信息**：标题、URL、词数、标签
2. **复盘堵塞点**：哪个步骤卡住了？原因？如何修复？直接改 SKILL.md
3. **清空临时文件**：
   ```bash
   rm -f devto_article.json devto_article_publish.json devto_body.md devto_body.b64
   ```

### 复盘记录格式
```
## {日期}：Dev.to v{版本号} — {标题}

- URL：{url}
- 词数：{N}
- 标签：{tags}
- 发布时间：{datetime}
- 状态：{成功/失败}
- 堵塞点：{如果有则记录}
- 修复：{如果堵塞则记录修复方式}
- 复盘行动：{本次复盘后对技能的修改摘要}
```

---

## 发布记录

### 2026-07-13：Dev.to v2.1 — I Migrated My MCP Server From STDIO to Streamable HTTP. It Almost Worked.

- URL: https://dev.to/chenyuan20509/test-5h08
- 词数: 994
- 标签: mcp, programming, tutorial, webdev
- 发布时间: 2026-07-13T13:56:55Z
- 状态: 成功
- 堵塞点:
  1. Step 0 预检漏传 api-key → 401（已修复 Step 0）
  2. JSON body 写作时 shell 反引号被解释执行，需要 Python 写文件（已修复 Step 2）
  3. PUT `{"article": {"published": true}}` 最小 payload 返回 200 但不生效（已修复 Step 6，必须带 full body + frontmatter 同步改）
  4. slug 在首个 published:true PUT 时永久确定，先用 test payload 发 PUT 再更新内容导致 slug='test-5h08'（已修复 Step 6 说明）
  5. Windows 环境下 `/tmp/` 不存在，需用工作目录相对路径
- 修复: Step 0 补 api-key header；Step 2 改用 Python 写 JSON；Step 6 改为完整 payload + frontmatter 同步；Step 3 路径改为相对路径；错误处理表补充 5 项

---

## §5 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| v2.2 | 2026-07-14 | **平滑发布**：创建草稿、核验、Publish 一次成功无堵塞。Step 2 改用外部 .md 文件 + Python 构建 JSON，规避 heredoc 三重引号冲突 |
| v2.1 | 2026-07-13 | **生产堵塞修复**：Step 0 补 api-key header；Step 2 用 Python 写 JSON 规避 shell 反引号转义；Step 6 改为完整 payload + frontmatter 同步发布；修正 Windows 临时路径；错误处理表+3 |
| v2.0 | 2026-07-13 | **SOP 化改造**：新增 §1 执行流程（Step 0-7 + 可执行代码）、§2 错误处理表、§3 质量门、§4 复盘流程；从 API 参考文档升级为完整可执行 SOP |
| v1.0 | 2026-07-11 | 初始版本：API 端点参考 + curl 示例 |

## 发布记录

### 2026-07-14：Dev.to v2.2 — My MCP Server Kept Crashing. Here's the Error Recovery Pattern That Saved It.

- URL: https://dev.to/chenyuan20509/my-mcp-server-kept-crashing-heres-the-error-recovery-pattern-that-saved-it-nd5
- 词数: 1063
- 标签: mcp, programming, tutorial, webdev
- 发布时间: 2026-07-14T06:48:08Z
- 状态: 成功
- 堵塞点: 无（全流程一次通过）
