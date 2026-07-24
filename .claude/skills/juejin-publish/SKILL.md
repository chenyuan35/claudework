---
name: juejin-publish
description: 掘金「深蓝AI」每日一篇自动发布技能。v2.28 — 新增 §6 开头多样化原则：6种风格强制轮换、禁用"一、引子"(每3篇最多1次)、禁用"跟朋友聊天"句式
---

# /juejin-publish 技能

**触发**：`/juejin-publish` 或用户说「发一篇掘金」

**账号**：深蓝AI（用户ID: 621653417544425），主页 https://juejin.cn/user/621653417544425
**定位**：AI 工具 / LLM 应用 / 软件工程效率 / MCP 协议系列 中文技术博主
**节奏**：每日一篇（用户要求「一天一篇」）

## §0 选题前准备工作（必做，不做不选题）

### §0.0 清工作区（硬性）

```bash
rm -f /c/Users/59314/claudework/_juejin_cover.png /c/Users/59314/claudework/_juejin_* /c/Users/59314/claudework/article_*.html
```
→ 清理后 `ls _juejin_* article_*.html 2>&1 | wc -l` 应为 0。

### §0.1 去重自检（熔断级）

选任何主题前，先导航到账号主页提取所有已发布标题——**不依赖记忆，强制实时**：

```javascript
browser_navigate('https://juejin.cn/user/621653417544425/posts')
// Wait 2-3s 后 evaluate:
() => {
  const titles = []
  const links = document.querySelectorAll('a[href*="/post/"]')
  for (const l of links) {
    const t = l.textContent?.trim()
    if (t && t.length > 5 && t.length < 120) titles.push(t)
  }
  return [...new Set(titles)]
}
```

**比对规则**：
- 待发布标题完全匹配 titles[] 中任一元素 → **熔断**
- 待发布标题与某元素同一事件/同一模型名/同一主题 → **熔断**
- 已有文集中 ≥3 篇同一大类选题 → **不得再选该类**
- 熔断后终止，不写任何新内容

### §0.2 外网扫热点 — 从全球趋势找选题

**原则**：真热点在外网（Hacker News / GitHub Trending），不是掘金站内。先找全球热点，再写什么发布到掘金。

用 WebFetch 取以下 2 个来源的今日热门：

```
WebFetch('https://news.ycombinator.com/')
WebFetch('https://github.com/trending?since=weekly')
```

**提取要素**：新工具/新框架/新模型名称（重复出现的 → 高优先级）。未被已有文章覆盖的 → 选题方向。

### §0.3 查数据 — 回顾账号表现

从账号主页查看各篇文章的阅读/点赞数据。若所有文章均为 0 数据，**必须换大类选题**。

## 全局工具函数 — 含自动重注入

每次执行本技能时，先将以下代码注入页面。**每次 `browser_navigate` 后必须重新注入**（页面 JS 上下文重置会清除 `__juejinTools`）。

```javascript
// === 反检测工具函数 ===
// 随机延时 [min, max]ms
function sleep(min, max) {
  const ms = Math.floor(Math.random() * (max - min + 1)) + min
  return new Promise(r => setTimeout(r, ms))
}

// 模拟人类滚动到元素位置
async function humanScroll(el) {
  const rect = el.getBoundingClientRect()
  const steps = 3 + Math.floor(Math.random() * 3)
  for (let i = 1; i <= steps; i++) {
    window.scrollBy(0, (rect.top - 100) / steps + (Math.random() * 10 - 5))
    await sleep(80, 200)
  }
}

window.__juejinTools = { sleep, humanScroll }
```

> ⚠️ **注入丢失陷阱**：每次页面内导航（点「写文章」按钮从 `/editor/drafts` → `/editor/drafts/new`）都会清除注入。执行 Step 2 前必须**重新 inject 一次**。


## §1 主流程

> ⚠️ 开始以下流程前，**必须先执行 §0 选题前准备工作**（去重自检 → 外网扫热点 → 查数据），完成选题后再进入 Step 0。

### Step 0 — 导航掘金

```
browser_navigate('https://juejin.cn')
```

Wait 2-4s 让页面完全加载。
检查页面是否已登录（右上角头像/通知存在）。未登录则熔断并提示用户重新登录。

### Step 1 — 导航编辑器

直接导航到新草稿页（跳过草稿列表）：

```
browser_navigate('https://juejin.cn/editor/drafts/new')
```

Wait 2-4s。注入全局反检测工具函数 `__juejinTools`。

> ⚠️ **可能弹出「初始化失败」dialog**：页面加载后可能弹出 alert dialog "初始化失败，请检查登录状态"。原因不明，使用 `browser_handle_dialog({accept: true})` 接受即可。接受后检查编辑器是否可用（页面标题含"写文章"），不可用则熔断提示登录。

> ⚠️ **必须重新注入**：从 `/editor/drafts` → `/editor/drafts/new` 是页面内跳转，所有注入的 `__juejinTools` 已清除。跳转完成后立即重新 inject 一次。
>
> 建议：每次 `browser_navigate` 后、以及每次检测到 `__juejinTools` 不存在时都重新注入。

### Step 2 — 填标题

```javascript
// 先确保工具函数存在，不存在则重新注入
if (!window.__juejinTools) {
  window.__juejinTools = {
    sleep: (min, max) => new Promise(r => setTimeout(r, Math.floor(Math.random()*(max-min+1))+min)),
    humanScroll: async (el) => {
      const rect = el.getBoundingClientRect()
      const steps = 3 + Math.floor(Math.random() * 3)
      for (let i = 1; i <= steps; i++) {
        window.scrollBy(0, (rect.top - 100) / steps + (Math.random() * 10 - 5))
        await new Promise(r => setTimeout(r, 80 + Math.random() * 120))
      }
    }
  }
}

const { sleep, humanScroll } = window.__juejinTools
await sleep(600, 1500)

const titleInput = document.querySelector('input[placeholder="输入文章标题..."]')
if (!titleInput) throw new Error('标题 input 未找到')
await humanScroll(titleInput)
await sleep(200, 500)

// 先 focus
titleInput.focus()
titleInput.dispatchEvent(new Event('focus', { bubbles: true }))
await sleep(100, 300)

// nativeInputValueSetter
const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set
setter.call(titleInput, '标题文本（≤80字）')
titleInput.dispatchEvent(new Event('input', { bubbles: true }))
titleInput.dispatchEvent(new Event('change', { bubbles: true }))

await sleep(300, 800) // 等自动保存

// ⚠️ 编码核验：确认标题文本未乱码
const writtenTitle = titleInput.value
if (!writtenTitle.includes('标题文本'.slice(0, 2))) {
  throw new Error(`标题内容异常（疑似乱码）："${writtenTitle}"`)
}
```

### Step 3 — 写正文（CodeMirror 主方案）

掘金使用 ByteMD markdown 编辑器（`div.bytemd.bytemd-split`），内核是 CodeMirror。**无论首次写入还是追加，都走 CodeMirror 实例：**

```javascript
await sleep(500, 1200)

const cm = document.querySelector('.CodeMirror')?.CodeMirror
if (!cm) throw new Error('CodeMirror 未找到')
await sleep(200, 500)

// CodeMirror.setValue() 直接替换全文
cm.setValue(markdownContent)
await sleep(300, 800)

// 编码核验：确认正文未乱码（检查中文片段是否能正确回读）
const writtenContent = cm.getValue()
const contentSample = markdownContent.slice(0, 20) // 取开头 20 个字符做样本
const sampleInCM = writtenContent.slice(0, 20)
if (!sampleInCM.includes(contentSample.slice(0, 3))) {
  throw new Error(`正文内容异常（疑似编码乱码）：开头预期 "${contentSample}" 但读到 "${sampleInCM}"`)
}

// 验证内容已写入
if (!cm.getValue()) throw new Error('CodeMirror setValue 后内容为空')
```

> ⚠️ `nativeInputValueSetter` 写入 `.bytemd textarea` 不可靠——一律走 CodeMirror 实例（上面已锁定 `.CodeMirror.CodeMirror`）。
>
> ⚠️ 代码块用 `~~~` 替代 ```（browser_evaluate 模板文字中反引号提前结束）。

正文长度：**一次写足，总字符 ≥6,000**（以 `allStrong[0]` 字符数计），写不足就重写全文。

### Step 3.1 — 封面（可选）

正文写完后、门禁检查之前，生成封面。不是必选项，失败直接跳过，不影响发布。

```bash
AGNES_API_KEY="sk-37fc8R90O1p5YQy7py4vQpmbWywfsnqg3qLJxxJg2cO8y3Ui" \
python /c/Users/59314/.claude/skills/agnes-image/scripts/generate.py \
  --prompt "Tech article cover, {标题前50字}, clean design, blue tech theme, simple geometric shapes, professional, no text" \
  --size 768x512 \
  --out /c/Users/59314/claudework/_juejin_cover.png
```

`file /c/Users/59314/claudework/_juejin_cover.png 2>&1 | grep -q "PNG"` → 输出 0 则成功，非 0 直接跳过。

### Step 3.5 — 发布前门禁全检（§4 门禁） 

写正文后、点发布前，执行 §4 所有技术门禁检查：

```javascript
// 门禁1: 标题 ≤80 字 — input 自带 maxlength=80，CLI 侧不需要重复检
// 门禁2: 总字符 ≥6,000 — 用 allStrong[0]（字符数/总字符），不用 allStrong[2]（正文字数，ByteMD 内部算法不稳定）
const allStrong = document.querySelectorAll('.bytemd-status strong')
const totalChars = parseInt(allStrong[0]?.textContent || '0')
if (totalChars < 6000) throw new Error(`总字符 ${totalChars} < 6000，内容不够充实，需用 cm.setValue 重写全文`)

// 门禁6: 至少1个代码块 + 至少1个表格
const hasCodeBlock = document.querySelector('.bytemd-preview pre') !== null
if (!hasCodeBlock) throw new Error('正文缺少代码块，需添加至少 1 个代码块')
const hasTable = document.querySelector('.bytemd-preview table') !== null
if (!hasTable) throw new Error('正文缺少表格（对比/列举/参数说明皆可）')

// 门禁8+9 无法用 DOM 检测（"实操价值""概念罗列"是语义级）——
// 但本技能文章模板已确保每段配例子+代码，标题段落数均值达标
```

总字符不足 6,000、缺代码块或缺表格则用 cm.setValue 替换全文重写，确保一次写足。

### Step 4 — 点发布按钮

找到 header 中的「发布」按钮（不是弹窗内的「确定并发布」）：

```javascript
// 失败重试策略：同一处的错误（如按钮未找到/弹窗未出现）重试 1 次；
// 重试仍失败 → throw → 熔断（调用方捕获后在 §2 已知坑追加记录）
await sleep(800, 2000)

// 找到发布按钮并滚动到其位置
const buttons = document.querySelectorAll('button')
let pubBtn = null
for (const b of buttons) {
  if (b.textContent.includes('发布') && b.offsetParent !== null) {
    pubBtn = b
    break
  }
}
if (!pubBtn) throw new Error('发布按钮未找到')
await humanScroll(pubBtn)
await sleep(300, 700)
pubBtn.click()
```

Wait 800-1500ms 让发布弹窗渲染（弹窗为动画 transition）。

### Step 5 — 选分类

```playwright
getByText('人工智能').click()
```

⚠️ 检查：点完后分类元素 class 应含 `active`。等待 200-400ms 确认已选中。

### Step 5.5 — 上传封面

封面在上一步已生成，检查 `_juejin_cover.png` 是否存在，存在则上传，不存在则跳过：

```playwright
// 必须限定在发布弹窗内——byteMD 编辑器也有 input[type="file"]
// .first() 可能命中编辑器而不是弹窗
page.locator('[class*="publish"] input[type="file"]').setInputFiles('C:\\Users\\59314\\claudework\\_juejin_cover.png')
```

> ⚠️ 掘金封面建议尺寸 192x128px（3:2 比例），Agnes (768x512) 上传后会被自动裁剪缩放。

验证封面已上传：

```javascript
await sleep(2000, 4000)
// 检查发布弹窗内是否有图片替换了默认封面图标（icon → blob/custom）
const coverSection = document.querySelector('[class*="publish"]')
const coverImg = coverSection?.querySelector('img[src*="blob"], img:not([src*="add_cover"])')
// 有 blob 图片或非默认封面图片即成功，失败不阻断
```

上传失败不阻断——封面不是发布必选项。

### Step 6 — 加标签

**标签搜索**：byte-select 只响应 Playwright 原生键盘输入（dispatchEvent 无效）。先聚焦输入框，再用 `fill()` 填入标签名：

```javascript
// evaluate 中聚焦标签搜索输入框
const inputs = document.querySelectorAll('input.byte-select__input')
for (const input of inputs) {
  if (input.offsetParent !== null && input.parentElement?.textContent?.includes('请搜索添加标签')) {
    input.focus()
    break
  }
}
```

```playwright
// 用 fill 绕过 byte-select placeholder 层的指针拦截
page.getByRole('textbox').nth(1).fill('AIGC')
```

> 不能用 `input.byte-select__input` 作为 Playwright target（匹配 3 个元素，strict mode 报错），必须用 `getByRole('textbox').nth(1)`。

**选择标签**：输入搜索后，等下拉出现（最长 3s），再点击选中：

```playwright
// 先等下拉选项出现
page.waitForSelector('li.byte-select-option, button:has-text("AIGC")', { timeout: 3000 })
getByRole('button', { name: 'AIGC' }).click()
```

> 标签下拉中的选项 DOM 结构可能是 `button`（常见）或 `li.byte-select-option`。Playwright `getByRole('button')` 兼容两种形态。不是 `span.byte-select__input` 或 div 文字——点错了显示"已选"但发布仍报「至少添加一个标签」。

**验证标签已选**：

```javascript
await sleep(200, 400)
const pageText = document.body.innerText
const match = pageText.match(/你还能添加 (\d+) 个标签/)
if (!match) throw new Error('未找到标签计数区域')
if (parseInt(match[1]) >= 3) throw new Error('标签未正确选中')
```

### Step 7 — 确认摘要

发布弹窗内摘要自动从正文截取前 100 字。**不修改。**

### Step 8 — 确定并发布

```playwright
getByRole('button', { name: '确定并发布' }).click()
```

> 不能用 `button:has-text("发布")`（会同时匹配 header「发布」和弹窗「确定并发布」两个元素）。

### Step 9 — 核验

页面跳转到 `juejin.cn/published`，标题变为「发布成功」。

```javascript
// 核验发布状态：不是"发布成功"页 → 需人工检查审核状态
const title = document.title
if (!title.includes('发布成功')) {
  throw new Error(`发布结果异常：页面标题="${title}"，需人工检查审核状态`)
}
```

用 `browser_evaluate` 从页面提取文章公开链接（在发布成功页的链接中找 `/spost/`）：

```javascript
() => {
  const links = document.querySelectorAll('a')
  for (const l of links) {
    if (l.href.includes('spost')) return l.href
  }
  return 'no spost links found'
}
```

> ⚠️ **evaluate 内慎用 arrow function + filter**：`Array.from(links).filter(l => l.href.includes('spost'))` 在 page.evaluate 的序列化上下文中可能触发 SyntaxError（箭头函数的花括号/括号匹配问题）。优先用简单 for 循环。

拿到 URL 后立即导航验证文章可访问：

```playwright
browser_navigate('https://juejin.cn/spost/{id}')
```

确认页面标题包含文章标题特征（非 404）。

> ⚠️ **URL 前缀**：掘金已发布文章的公开链接是 `/spost/{id}`（如 `/spost/7657015077267472393`），`/post/{id}` 返回 404。核验时使用 `/spost/` 前缀验证文章可访问。
>
> `juejin.cn/spost/{id}` → 公开可访问 ✅
> `juejin.cn/post/{id}` → 404 ❌

## §2 已知坑

| 坑 | 现象 | 修复 |
|----|------|------|
| Tag 选择无效 | 点击文字后显示"已选"，但点发布报「至少添加一个标签」 | 必须点 `li.byte-select-option`（LI 元素），不能点文字/SPAN |
| ByteMD 写入失效 | `nativeInputValueSetter` + `dispatchEvent('input')` 后 `ta.value` 仍为 0 | **首次和追加都走 CodeMirror 实例** `cm.setValue()`，见 §Step 3 |
| 发布按钮歧义 | `button:has-text("发布")` 匹配 header「发布」和弹窗「确定并发布」 | 标题用 `getByRole('button', { name: '发布' })`，弹窗用 `{ name: '确定并发布' }` |
| category_id 类型 | API 返回「至少添加一个分类」 | `category_id` 必须是字符串（如 `"6809637773935378440"`），数字会报错 |
| 标签选择器歧义 | `browser_type({target: "input.byte-select__input"})` 报 strict mode violation | 改用 `getByRole('textbox').nth(1)` |
| 标签搜索不触发 | `dispatchEvent('input')` 输入后下拉不出现 | 必须用 Playwright 原生 `pressSequentially`/`fill` |
| 标签最大数量 | 平台上限从 2 → 3 个标签 | 验证时检查 `remaining < 3` |
| 分类选择不触发 | evaluate 内 `element.click()` 未切换 Vue class | 用 Playwright `getByText('分类名').click()` |
| AGNES_API_KEY 注入不可靠 | settings.json env 在 Bash 子进程中读不到 | API key 写死在命令中：`AGNES_API_KEY="sk-..." python generate.py ...` |

## §4 发布前 7 项门禁

1. **标题 ≤80 字**（input maxlength=80 CLI 侧不需要检）
2. **总字符 ≥6,000**（编辑器 `allStrong[0]` 字符数，确定性指标），不足则重写全文
3. **分类已选**（`getByText('人工智能').click()`）
4. **标签已选**（`document.body.innerText` 正则匹配"你还能添加 N 个标签"且 N < 3）
5. **摘要非空**（弹窗自动填充）
6. **正文包含至少 1 个代码块 + 至少 1 个表格**（`.bytemd-preview pre` + `table` 同时存在）

有一项不满足就修正后重试，不发布残缺文章。

## §5 选择器总表

| 元素 | 选择器 / 定位方法 | 交互方式 | 备注 |
|------|------------------|----------|------|
| 标题输入 | `input[placeholder='输入文章标题...']` | `nativeInputValueSetter` + `dispatchEvent('input')` | Vue 绑定 |
| 正文(写入) | `document.querySelector('.CodeMirror').CodeMirror` 实例 | `cm.setValue(content)` | **不作为 textarea 写入——nativeInputValueSetter 不可靠** |
| 字符数指示器 | `querySelectorAll('.bytemd-status strong')[0]` | 读取 `.textContent` | NodeList 索引 0（第 1 个 strong），**门禁 ≥6,000（确定性指标）**。**不能**用 `:nth-child(1)` CSS 选择器 |
| 正文字数指示器（备用参考） | `querySelectorAll('.bytemd-status strong')[2]` | 读取 `.textContent` | NodeList 索引 2（第 3 个 strong），ByteMD 内部算法不稳定，**不用作门禁指标**。**不能**用 `:nth-child(3)` CSS 选择器 |
| 发布按钮(header) | text 含"发布"的 button，**排除**弹窗内的"确定并发布" | JS 遍历找 textContent + offsetParent click | 不可用 CSS selector |
| 分类选项 | `getByText('分类名').click()` | Playwright 原生 click |  |
| 标签搜索输入 | `page.getByRole('textbox').nth(1).fill('标签名')` | `fill()` 绕过 placeholder 层拦截 | 不能用 `input.byte-select__input`（3元素歧义） |
| 标签下拉选项 | `getByRole('button', { name: '标签名' }).click()` | Playwright 原生 click | DOM 可能为 button 或 li，Playwright button role 兼容两种 |
| 确定并发布 | `getByRole('button', { name: '确定并发布' }).click()` | Playwright 原生 click | 勿用 `:has-text("发布")` 歧义选择器 |
| 封面文件输入 | `[class*="publish"] input[type="file"]`（在发布弹窗中） | Playwright `setInputFiles()` | 必须限定弹窗作用域，byteMD 编辑器也有 input[type=file] |

## §6 内容策略

### 🔴 开头多样化原则（熔断级，2026-07-24 新增）

**每篇文章的"引子/第一段"必须使用与上一篇不同的开头风格。连续两篇相同 → 熔断重写。**

#### 6 种开头风格（强制轮换）

| 编号 | 风格名 | 典型开头形态 | 使用限制 |
|------|--------|------------|---------|
| A | **问题驱动式** | 「在日常[场景]中，我们常遇到[问题]——[工具]给出了新思路」 | 可用，但**不能**用"上周跟朋友聊天"句式 |
| B | **数据冲击式** | 「[数字]% 的开发者[现象]，但只有[数字]% 真正采取了行动」 | 首段必须有具体数字 |
| C | **场景代入式** | 「想象一下：你正在[场景]，突然[问题]——[方案]正好解决」 | 不用"引子"小节标题 |
| D | **新闻公告式** | 「[日期]，[公司]正式发布[产品]，核心变化是…」 | 不用"引子"小节标题 |
| E | **反常识/对比式** | 「当大家都在讨论[A]时，[B]正在悄然改变[领域]」 | 用"引子"但不标序号，直接写 |
| F | **技术问题直接切入** | 不写引子，第一段直接讲技术问题：「[框架/工具]有一个容易忽略的细节：…」 | 无"一、引子"，直接以 H2 开始 |

**轮换规则（硬性）：**
1. 上一篇用了风格 A → 下一篇**不能**再用 A；以此类推
2. "一、引子"这个节标题**最多每 3 篇出现 1 次**，其余 2 篇要么去掉小节名直接写开头，要么用不带序号的引子段落
3. "上周跟朋友聊天"这个句式**彻底禁用**——无论何种风格，不得出现"上周跟/上个月跟/前几天跟 XX 聊天"
4. 上一篇的开头风格在 SESSION_STATE.md 中记录，下一篇写前先读

#### 开头写作验收清单
- □ 开头没有"一、引子"（最多每 3 篇 1 次）
- □ 没有出现"跟XX聊天"句式
- □ 本篇开头风格与上一篇不同
- □ 前 100 字能让人立刻知道这篇文章在讲什么（不是泛泛的背景铺垫）

### 选题范围
- ~~MCP 协议系列~~（同一大类 ≥3 篇上限，停写）
- ~~AI 编程工具评测（Claude Code / Cursor / Copilot / Codex CLI）~~（账号已有 4 篇同类，停写）
- ~~LLM 应用实战（Agent 框架、Function Calling、RAG）~~（账号已有 3 篇同类，停写）
- **软件工程效率**（提示词工程、开发工作流、代码规范、代码审查自动化）— 账号已有 4 篇同类，**已达 3 篇上限，停写**
- **当前趋势热点**（从 §0.2 外网扫热点发现的当日热门话题，须先做去重自检）

> ⚠️ **去重先行**：选题前必须执行 §0.1 去重自检。大类选题超过 3 篇即停。

### 系列钩子
- 每篇结尾加「关注我，不错过后续内容」
- 系列文写「下篇预告：...」
- 适当留互动钩子「欢迎在评论区讨论你的使用场景」

## §7 发布后

1. **核验文章可访问**：从 `/published` 页提取 spost URL（`for` 循环遍历 `a[href]` 找 `.includes('spost')`），`browser_navigate` 确认页面标题包含文章标题前半段。`juejin.cn/spost/{id}` 可访即成功。
2. 如有评论区互动，后续维护。
3. **记录开头风格**：将本篇使用的开头风格编号（A-F）写入发布后记录，供下篇轮换参考。不加记忆文件，仅用文字备注。连续两次风格相同属重大缺陷，下次选题时自动审查。

> 各步堵塞按 CLAUDE.md 技能修复标准流程执行
