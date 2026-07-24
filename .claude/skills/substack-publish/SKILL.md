---
name: substack-publish
description: Substack「MINI」中文独立创作者案例研究 Newsletter 全自动发布技能。v1.0 — 赛道：拆解中文独立创作者（YouTube/Substack/B站/小红书）的赚钱路径、增长策略、内容模型；Notes 引流 + Posts 深度
---

# Substack · MINI · 中文独立创作者案例研究 v1.0

**触发**：`/substack-publish` 或「发一篇 MINI」「写个创作者案例」

---

## PHASE 0：硬性去重（熔断级，不可跳过，必须先执行）

**执行时机**：每次启动本技能、写任何内容之前。必须先到 Substack 已发布文章列表页提取所有已发布标题。

### 步骤

1. 导航到 Substack 后台已发布文章列表页（能看到已发布文章标题的页面）
2. evaluate 提取所有可见文章标题到数组 titles[]
3. 比对规则：
   - 待发布标题与 titles[] 中任一元素完全匹配 → **熔断，不发布，报告"已发布过：[重复标题]"**
   - 待发布标题关键词与 titles[] 中某元素高度重叠（同一事件/同一模型名/同一主题）→ **熔断**
4. 熔断后终止流程，不写任何新内容

### 铁律
- 每次启动技能必须先执行此事。不做就去写内容 = 流程违规。
- 不依赖记忆或历史记录——必须实时从页面提取。

---

**核心定位**：用英文写作，面向海外/海归读者拆解中文独立创作者的商业模型。**不是访谈录，是法医式解剖**——收入数字、增长拐点、平台选择、失败经历、可复用模式。

---

## 出版信息

| 字段 | 值 |
|------|-----|
| 出版物名 | MINI（可改名，本技能用 MINI 作为 slug）|
| 主页 | https://substack.com/@mini559831 |
| 账号 | @mini559831（已登录）|
| 语言 | **英文写作**（受众：海外华人 + 对中国创作者好奇的国际读者）|
| 赛道 | 中文独立创作者案例研究（ Indie hackers / Creators / Solopreneers in Chinese-speaking world）|
| 目标字数 | Posts 1800-2500 词 / Notes 50-150 词 |
| 发布频率 | 1 Post/周 + 最多 2 Notes/周（风控安全）|
| 配图 | **每篇 Post 可配图（4 种路径任选）**|

**为什么英文写作？**
- 中文读者在 Substack 上付费意愿几乎为 0（观察：中文号互动远低于英文同体量）
- 英文 = 全球受众 + Substack 官方推荐算法友好
- "中国创作者故事" 是英文世界的 **under-served niche**（供给少，需求真实）

---

## §0 赛道定义与差异化

### 赛道背景（基于 2026-07-03 浏览器调研）
- Substack Explore 上中文内容极少：@techtaiwan（科技新闻）@chaijing（播客）@karpathy（不活跃）
- **"中国独立创作者案例研究" 方向完全空白**
- 对标英文世界：Indie Hackers、The Write Path、Lenny's Newsletter 的创作者访谈

### 差异化三支柱
1. **法医式数据**：不要"他说做得好"，要"他 3 个月从 0 到 $4.2M ARR，做了这 4 步"
2. **失败解剖**：每篇必写 1-2 个失败时刻（失败比成功更有价值）
3. **可复用模板**：每篇结尾给读者能抄走的"模板/checklist"

### 不做的事
- 不做纯访谈 Q&A（无聊）
- 不做吹牛稿（"他是下一个 XXX"）
- 不做泛泛的"平台运营技巧"（没创作者当主角）
- 不写 AI 工具教程（已有太多）

---

## §0a Anti-AI Voice：去 AI 味引擎

**最高优先级**。Substack 读者付费看真人洞察，AI 味 = 退订。

### 规则 1：长短句混搭
每 3-4 句必须插入 1 个极短句（3-8 词）。
- ❌ "He spent three years building the audience before monetizing."
- ✅ "He waited three years before making a single dollar. Three. Whole. Years. Most people would've quit at month six."

**短句弹药库**：`Yeah. No.` `That hurt.` `Worth it.` `Not even close.` `Big mistake.` `Zero regrets.` `Pathetic, but true.` `So I did.` `Dumb, right?`

### 规则 2：真人过渡词
| ❌ AI 过渡 | ✅ 真人过渡 |
|-----------|------------|
| Moreover / Furthermore | Honestly, / Here's the thing… / Look, |
| It is important to note | The crazy part? / Here's what nobody talks about |
| This demonstrates | Long story short, / And guess what? |
| Consequently / Therefore | So yeah, / Which is wild when you think about it |

每篇 Post 至少 3 个真人过渡词，禁止连续两段用同类。

### 规则 3：用具体场景替代抽象总结
- ❌ "He adopted a multi-platform distribution strategy."
- ✅ "He wrote the same core idea five times a week: long-form on Substack, thread on X, 60-second tips on TikTok, and a weekly YouTube deep-dive. Same meat, different plates."

### 规则 4：破坏平行结构
每个 H2/H3 段落用不同切入角度：
- 有的从**数字**（"$0 to $12k MRR in 90 days"）
- 有的从**对话**（"I told my wife we might lose the house"）
- 有的从**反差**（"His most viral post was his worst earner"）
- 有的从**时间线**（"Month 1-3: nothing. Month 4: explosion."）

### 规则 5：去总结句（最重要）
**❌ 禁止句式**（碰都不要碰）：
- "The lesson here is…"
- "This case demonstrates that…"
- "What we can learn from this is…"
- "In conclusion…" / "To summarize…"

**✅ 替代方案**：以具体场景、动作、对话、反问收尾。让读者自己总结。
- ❌ "The lesson is diversification."
- ✅ "He now earns from five sources. I'd say three is the sweet spot for most people. Below that, you're one algorithm change away from zero."

### 规则 6：口语化词汇 + Contractions 强制
| ❌ 书面 | ✅ 口语 |
|--------|--------|
| approximately | around / a shocking |
| utilized | buy / use / grabbed |
| significant | massive / crazy / dumb |
| strategy | playbook / move / gamble |
| revenue | cash / earnings / top line |

Contractions 强制：`I'm / it's / wasn't / didn't / wouldn't / that's / here's / there's`。每 200 词至少 1 个，全文至少 8 个。

---

## §1 创作者选题矩阵

### 三类主角轮换（每 4 周一循环）

| 类型 | 特征 | 案例来源 | 写作角度 |
|------|------|---------|---------|
| **A 破局者** | 0→1 冷启动，无粉丝没钱 | Indie Hackers、X/Twitter、即刻 | 冷启动打法、前 100 个用户怎么来 |
| **B 转型者** | 大厂→独立、副业→全职 | 即刻、V2EX、Matters | 辞职时机、心理压力、收入替换点 |
| **C 扩容者** | 个人→团队、单平台→多平台 | YouTube、播客、 conhekt | 招人、杠杆、退出日常创作 |

### 选题红线
- **不写**：政治人物、VPN/反审查工具、色情/擦边、完全匿名无法核实
- **不写**：没有可核实收入数字的（"据说""听说"没用）
- **不写**：读者已经看过 100 次的创作者（要找 under-the-radar）
- **不写**：需要主角本人授权才能写的（**全部基于公开数据，不联系主角**）

### 选题来源（全自动扫描，Claude 子代理执行）

每篇 Post 启动时，按下列顺序让子代理**并行扫描**，每个来源返回 3-5 个候选：

| 优先级 | 来源 | 扫描方式 | 工具 |
|--------|------|---------|------|
| 1 | Indie Hackers | 热门帖 + 近 30 天新帖 | WebFetch / WebSearch |
| 2 | X/Twitter | 搜索 "made $X from" "quit my job" "indie hacker" + Chinese | WebSearch |
| 3 | YouTube | 中文"独立开发者""YouTuber 收入""副业"最新视频 | WebSearch + WebFetch |
| 4 | V2EX | /go/indie /go/sideproject 节点 | WebSearch（WebFetch 不可达，V2EX 域名被屏蔽）|
| 5 | Matters / 中文独立博客 | 搜索"独立开发""创业""副业" | WebSearch |
| 6 | Substack 自己 | 搜 "Chinese creator" "indie hacker China" | WebSearch |
| 7 | Hacker News | Show HN / Ask HN 中文相关 | WebFetch |

**子代理 prompt 模板**（每个来源一个子代理并行）：
```
扫描 {来源} 上近 30 天关于"中文独立创作者/独立开发者/副业变现"的公开案例。
每个候选返回：
- 名字/花名 + 平台主页链接
- 公开收入数字（有/无，附来源 URL）
- 独特处（破局/转型/扩容哪个）
- 失败或犹豫时刻（有/无，附来源）
- 可复用模板（有/无）
- 数据出处 URL（至少 2 个独立来源）

只返回**有公开收入数字**的候选。没有数字的丢弃。
至少返回 3 个候选，最多 5 个。
```

---

## §2 研究流程（全自动，不联系主角）

### Step 1：候选池构建（并行子代理，5 分钟）

**跳过条件**：如果 `pipeline.md` 中已有 ≥3 个候选（标注为 ready 但未发布），且距离上次全量扫描 ≤7 天 → **尝试使用 pipeline 已有候选**。

**⚠️ 可执行性校验**：跳过扫描前，必须对 pipeline 候选做快速可执行性检查——针对即将写的类型（A/B/C），确认至少 1 个候选满足：
- 有公开可核实的收入数字（附可打开的 URL）
- 数据来源 ≥ 2 个独立来源（三角验证）  
- 英文世界可索引（WebSearch/WebFetch 能取到内容）

以上任一不满足 → **不得跳过扫描**，强制启动 3-4 个子代理做新鲜扫描（避免用不可执行候选浪费时间）。

**扫描等待策略**：启动 4 个并行扫描代理后，必须等待至少 3 个返回结果再锁定候选（避免只用最快来源撞到已发过的主角）。如果 90 秒后某代理仍未返回，跳过该来源继续。如果 Indie Hackers 代理最慢，优先用 YouTube/X/V2EX 的返回结果。

如果 pipeline 候选不足或不满足可执行性，再启动 3-4 个子代理扫描上节来源，汇总去重后得到 10-15 个候选。

### Step 2：主角锁定（Claude 自动选）
**筛选硬指标**（必须满足 ≥3 项）：
- [ ] 有公开可核实的收入/订阅数字（附来源 URL）
- [ ] 有失败或黑暗时刻（不是顺风顺水）
- [ ] 有非常规决策/打法（读者没法从别的文章看到）
- [ ] 与过去 4 篇 Posts 的主角不重复类型（查 tracking.md）
- [ ] 数据出处 ≥ 2 个独立来源（三角验证）

**自动选**：满足指标最多的候选。平局时选"最 under-the-radar"（搜索量最低）。

### Step 3：深度研究（子代理执行，不联系主角）
**必须做**：
1. 翻主角所有公开帖/视频/Newsletter（3 个月内）—— WebFetch 存档
2. 找到收入数字出处（亲口说/播客/Newsletter/采访）—— 截图/存档 URL
3. 记录 1-2 个失败或犹豫时刻 —— 附来源 URL
4. 找到 1 个读者能抄走的"模板/checklist" —— 从公开内容提炼
5. 三角验证：主角说 + 平台数据 + 第三方评论（至少 2 个独立来源）

**禁止**：
- 不凭记忆写收入数字（必须附来源 URL）
- 不把猜测当事实（"probably" "likely" 是红线）
- 不联系主角（不发私信/DM/邮件）
- 不写"未公开"的数字（没有数字就不写具体数，用区间或丢弃该候选）

### Step 4：写作提纲（Claude 自动生成）
每篇 Post 必须包含：
- **Hook**：一个反直觉的事实/数字/场景（前 50 词抓住读者）
- **Background**：主角是谁、做什么、读者为什么该关心
- **The Pivot**：关键转折（辞职？换平台？第一次收入？）
- **Numbers**：收入/增长/成本的真实数字（附来源）
- **Failure**：失败/犹豫/差点放弃的时刻（附来源）
- **Playbook**：读者能抄走的 3-5 步模板
- **Takeaway**：一个反直觉的读者洞察（不总结，是"这让我想到…"）

### Step 5：写 + 自查
按 §4 写作风格写完后，用 §0a 六条规则对照自查，**每条必须打钩**才能进 §6。

---

## §3 Notes 引流打法

### Notes 定义
Substack 的短帖功能，**类似 Twitter**，出现在关注者信息流 + Explore 页面。**免费、高曝光、可以挂 Post 链接**。

### Notes 类型轮换

| 类型 | 频率 | 模板 | 目的 |
|------|------|------|------|
| **Snippet** | 3/周 | "我刚写完 /@mini559831 深度拆解了 [创作者] 怎么做 [具体事情] —— 数字放评论区了" | 引流到 Post |
| **Data Drop** | 1/周 | 直接公布一个反直觉数字（"73% 的中文独立开发者前 6 个月收入 <$100/月"） | 涨关注 |
| **Question** | 1/周 | 问读者一个选择题（"你会辞掉 $200k 的工作做独立吗？"） | 互动 + 话题 |
| **Contrarian** | 1-2/周 | 一个反主流观点（"别急着做 Newsletter，先做这个"） | 爆款潜力 |

### Notes 写作硬规则
- **50-150 词**，超过 200 词没人看
- **第一句必须是钩子**（数字/反直觉/提问），前 20 词定生死
- **每篇 Notes 必须有明确 CTA**（read the full post / comment below / subscribe）
- **禁止**：无病呻吟、鸡汤、"今天天气真好"

### Notes 引流时机
- Post 发布后 **8h** 发 **1 篇** Snippet Notes（不挂链接，纯钩子）
- Post 发布后 **24h** 可选发第 2 篇（仅当首篇 Notes 点赞 ≥5）
- **禁止同一天发 2 篇 Notes**
- **一周内最多 2 篇 Notes + 1 篇 Post**

---

## §4 写作风格引擎

### 文风内核：Ben Thompson + Lenny Rachitsky 混合体

**Ben Thompson（Stratechery）风格**：
- 一个核心论点贯穿全文
- 用"Platform/Content/Commerce"框架解构
- 每段有论据不空谈

**Lenny Rachitsky 风格**：
- 数字至上（具体到 $ 和 %）
- 引用主角原话（精确到词）
- 可操作建议（不是理论，是下一周就能做的行动）

### 段落结构模板（§4.1 供参考，非硬套）

```
{Hook 段：一个反直觉事实 / 数字 / 场景}

{背景：主角做什么、为什么读者该关心}

{The Pivot：关键转折时刻}

{数字段落：真实收入 + 增长曲线}

{失败段：犹豫 / 差点放弃 / 决策失误}

{Playbook：3-5 步可复用模板（每个主角不同）}

{Takeaway：反直觉洞察，以一个场景/问题收尾}
```

**硬规则**：
- 每段 2-4 句，超 5 句必拆
- 每个 H2 段落必须包含 **至少 1 个具体数字或主角原话**
- H2 标题必须**不带 "How to" / "Why"**（太 AI），用**名词短语 + 数字**
  - ❌ "How One Developer Built a $10k MRR Product"
  - ✅ "From $0 to $12k MRR: What He Did in 90 Days"
  - ✅ "The 3-Platform Payout: One Creator's Revenue Split"

### 数据呈现规则
- **货币**：统一 USD，括号附 CNY（"earned $12,000/month (≈¥86,000)"）
- **时间**：统一用 "Month 1/Month 6" 或具体年月（"March 2024"）
- **百分比**：保留一位小数（"73.2%" 比 "73%" 更可信）
- **大数字**：用 $12k 而非 $12,000（Newsletter 惯例）
- **必须给语境**：数字本身没意义，要 comparison（"$12k MRR sounds small until you see his 3% conversion rate"）

### 标题公式（§4.2）

**公式 A（数字反差）**：
`[低数字] to [高数字] in [时间]: [反直觉结论]`
- "$0 to $4.2M ARR in 18 Months: Why He Refused VC"

**公式 B（反主流）**：
`[常见建议] is Dead. Here's What [实际赢家] Did Instead.`
- "Build an Audience First is Dead. Here's How He Sold Before He Had Followers."

**公式 C（好奇缺口）**：
`I Studied [N] [创作者类型]. [最反直觉的发现].`
- "I Studied 30 Indie Developers in China. 70% Earned Less Than $100/month for Their First Year — and That's the Good News."

**标题硬规则**：
- 60-90 字符（Substack 标题被截断临界点）
- 前 40 字符必须有 **数字 / 反直觉事实 / "I" 主语**
- 禁止词：Ultimately, Finally, Just, Very, Really, Amazing, Incredible（这些词让读者想到 AI）

⚠️ 不得连续两篇使用同一标题公式（2026-07-17）

---

## §5 发布流程（Playwright MCP）

### 前置
- Playwright MCP 已连接（mcp__playwright__* 工具可用）
- 已登录 Substack（@mini559831）
- **Notion API**：尝试 `notion_sync.py read`，如果连接失败（网络/代理/SSL 错误）→ **降级**：跳过 Notion 查询，仅依赖本地 `memory/substack-posts/tracking.md` 和 `pipeline.md` 确认当前状态。Notion 恢复前不做结构修改决策。

### §5.1 写新 Post

**Step 1：打开新建 Post 编辑器（单一路径：browser_run_code_unsafe + filename）**

Substack Create 按钮基于 Radix UI，evaluate 类点击可能不触发菜单展开。锁死为单一可靠路径：

```
0. navigate → https://substack.com/@mini559831

1. 用 browser_run_code_unsafe 点击 Create + Article：
   
   async (page) => {
     const nav = page.locator('[role="navigation"]');
     const createBtn = nav.locator('button:has-text("Create")');
     await createBtn.click();
     await page.waitForTimeout(1000);
     const articleItem = page.locator('[role="menuitem"]').filter({ hasText: 'Article' });
     await articleItem.click();
     return 'Clicked Create → Article';
   }

2. 等待跳转到编辑器（URL 变为 .../publish/post/{id}）
```

⚠️ 不依赖 evaluate、不依赖硬编码 ref ID、不依赖 getByRole。

**Step 2：填写标题和副标题（⚠️ 两个 Title 字段都要填）**

Substack 编辑器有**两个独立的 Title 字段**，缺一不可：
1. **Inline 标题**（编辑器内，`[placeholder="Title"]`）—— 决定性字段。**必须用** `browser_type` 的 `slowly: true` 参数填入，触发 Substack 的标题检测。仅 `fill()` 可能无法注册。如果发布时报 "Please set a title"，说明此字段未正确填入。
2. **File Settings 标题**（左侧面板，`[placeholder="Add a title..."]`）—— SEO 字段，自动跟随 inline 标题，也可手动设置。

```
# 第一步：填 inline 标题（决定性）
click [placeholder="Title"]
pressSequentially "¥51,000 in 6 Months: The Chinese Indie Dev ..."

# 第二步：填副标题
click [placeholder="Add a subtitle…"]
type 副标题（可选，1 句总结本文）

# 第三步（可选）：填 File Settings 标题
click [placeholder="Add a title..."]  
type 同标题
```

**已知陷阱**：如果先填了 File Settings 的 Title，再点 Continue → 弹出 "Please set a title" 对话框：
```
1. browser_handle_dialog({accept: true}) 关闭弹窗
2. 重新用 pressSequentially 填入 inline title
3. 重新点 Continue
```

**Step 3：ProseMirror 内容写入（单一路径：Python → inject.js → browser_run_code_unsafe filename）**

- 英文对象的中文原文引用 → **只保留英文翻译，不保留中文原文**
- Substack 编辑器基于 TipTap/ProseMirror
- **TipTap 标签兼容表**：

  | 标签 | TipTap 支持 | 注入建议 |
  | `<h2>`, `<h3>` | ✅ 原生支持 | 直接使用 |
  | `<p>`, `<br>` | ✅ 原生支持 | 直接使用 |
  | `<blockquote>` | ✅ 原生支持 | 直接使用 |
  | `<strong>`, `<em>`, `<a>` | ✅ 原生支持 | 直接使用 |
  | `<ul>`, `<ol>`, `<li>` | ✅ 原生支持 | 直接使用 |
  | `<code>`, `<pre>` | ✅ 原生支持 | 直接使用 |
  | `<hr>` | ⚠️ 部分支持 | 可用但不推荐 |
  | `<table>` | ❌ **不支持**，被压平为纯文本 | **注入前将表格转为文字描述**（"Milestone: $X / Revenue: $Y" 格式） |
  | `<details>`/`<summary>` | ❌ 不支持 | 删除或转为正文 |
  | `<img>` | ❌ 不支持直接内嵌 | 通过工具条 Image 按钮上传，不用 `<img>` 标签 |

- **Bold/Italic 预处理**：`**text**` 转为 `<strong>text</strong>`，移除 `*text*` 星号

- **单一路径：`python _gen_inject.py` + `browser_run_code_unsafe filename`**

  1. 执行 `C:\Users\59314\claudework\_gen_inject.py`（自动取最新 md 文件，生成 inject.js）
  2. 用 `browser_run_code_unsafe({filename: "C:\\Users\\59314\\claudework\\inject.js"})` 注入
  3. 验证输出 N >= 10000；N < 8000 熔断

- **禁止路径**（验证不可靠）：`browser_evaluate` 直接传 HTML（引号问题）、sections 数组分拆（截断 5.7K/13K）、`execCommand`（倒序）

- **建议**：一次性注入全部正文，不分多次 evaluate（避免重叠）
- **CJK 注入前阻断（双重验证）**：注入 HTML 前，先扫描**完整 markdown 源文件**（不是只扫 HTML）。只要存在 CJK 统一表意文字，就停止发布流程并报错：`"CJK detected — replace all Chinese characters with English before proceeding"`。英文读者看不懂中文原文。引用主角原话时只保留英文翻译。

  **双重验证（不可跳过任一步）：**
  
  **Step A — Grep 扫描**：
  ```bash
  grep -nP '[一-龿]' {源文件路径}
  ```
  返回非空 → 熔断，列出匹配行号并报错。

  **Step B — Python 二次验证（Grep 通过后必须执行）**：
  ```python
  import re
  with open(r'{源文件路径}', 'r', encoding='utf-8') as f:
      content = f.read()
  matches = re.findall(r'[一-龿]', content)
  if matches: print(f'CJK FOUND: {set(matches)}')
  else: print('No CJK found')
  ```
  Python 找到 CJK → 熔断，不信任 Grep 的"clean"结果。
  
  ⚠️ **铁律**：如果 Grep 和 Python 结果不一致（Grep clean 但 Python 有匹配），以 Python 为准熔断。Grep 工具可能存在编码/引擎差异，Python 正则更可靠。
  
  ⚠️ 特别注意源文件中的中文人名（如"肖弘"）、平台名（如"即刻"）、习惯用语（如"口碑"）、以及 Source URL 标题——全要用英文替代或移除。

- **🔁 去重检查**：注入前扫描正文中是否有完全相同的段落文本连续出现（判断指标：连续两行 `<p>` 内容相同或 80% 以上相似）。发现重复则报错并定位行号，不可发布。

**Step 4：设置 Newsletter 描述与元数据**
- File Settings 位于左側面板，包含：
  - **Title**（`[placeholder="Add a title..."]`）— SEO 标题，自动从正文标题填充
  - **Description**（`[placeholder="Add a description..."]`）— 写 2-3 句，总结本文 + 一个数字钩子
  - **Thumbnail** — 见 §5.3

该侧边栏元素可能不在 viewport 内，用 evaluate 设置值：
```javascript
() => {
  const el = document.querySelector('[placeholder="Add a description..."]');
  if(el) { el.value = '你的描述'; el.dispatchEvent(new Event('input', {bubbles: true})); }
}
```

**⚠️ 已知陷阱**：侧边栏出现 "Loading..."（图片上传中）时，其 overlay 会拦截 File Settings 中 Description 字段的 input 事件，evaluate 写入的值可能不生效。发布后 Social preview 会回退到显示正文首句。

**推荐顺序**：先点 "Done" 关闭侧边栏 → 点 "Continue" 打开发布对话框 → 在发布对话框的 **Social preview → Edit** 中设置描述文本（点击 Social preview 区域 → Edit 按钮 → 填写 description），此时没有 overlay 遮挡。

**Step 5：发布前检查**
- [ ] 标题符合 §4.2 公式
- [ ] 正文 1800-2500 词
- [ ] 至少 3 处具体数字
- [ ] 至少 1 段主角原话引用
- [ ] §0a 六条去 AI 规则全过
- [ ] 结尾没有总结句（§0a 规则 5）

**Step 6：发布（"Continue"→发布对话框→"Send to everyone now"）**

Substack 编辑器没有直接的 "Publish" 按钮，发布走的是 "Continue" 通道：

```
1. 内容写完后 click text="Continue"（CSS: button:has-text("Continue")）
   → 弹出 "Publish" 发布对话框

2. 在发布对话框中：
   a. 设置标签（可选）：click [placeholder="Select or create tags"]
      → type 标签名 → press Enter
   b. Audience: "Everyone"（默认选中）
   c. Comments: "Everyone"（默认选中）
   d. Delivery: "Send via email and the Substack app"（默认选中）
   e. Scheduling: 不选（发布即发）

3. click text="Send to everyone now"
   → 可能弹出 "Please set a title" 对话框（inline title 未注册时）
   → 解决：browser_handle_dialog({accept: true})
        → 用 pressSequentially 重填 inline title
        → 关闭 File Settings 侧边栏（click "Done"）
        → 重新 click Continue → 重走发布流程
   → 正常时：按钮变为 "Publishing..."（含 progressbar）

4. **⚠️ "Publish without buttons" 紧接在 Send 之后弹出，与 "Publishing..." 同时存在**
   这不是错误——这是 Substack 的发布后订阅按钮引导对话框，它覆盖在 Publishing overlay 上，不关闭则发布卡住。
   出现条件是 publish dialog 中 Audience 选了 "Everyone"。
   必须立即执行，不等待：
   click text="Publish without buttons" 跳过（用 evaluate 或 Playwright click 均可）
   
   点完后，"Publishing..." 进度继续，"Publishing..." → 跳转为 "Your post is live!"

5. 页面跳转为 "Your post is live!" 页面（URL: .../publish/posts/detail/{id}/share-center）
   显示 Post URL（如 https://{slug}.substack.com/p/{post-slug}）
   确认看到 heading "Your post is live!" 即为成功

6. 复制 Post URL：从分享框的 textbox 中复制链接
   或记下页面显示的 slug URL

#### 发布后（Post-Publish）

**7. 写入 tracking.md**

```
更新 tracking.md：
- 添加新行：日期 | 标题 | 类型 | 主角 | 平台 | 收入数字 | 字数 | ✅ published
- 添加 URL / Open URL / Hero Image / Tag 元数据行
```

**8. 更新主角池 pipeline.md**

```
将 pipeline.md 中对应候选标记为 "✅ Published YYYY-MM-DD"
（用 ~~strikethrough~~ 或标注完成状态）
```

**9. 安排 Notes 引流（§3 规则）—— CronCreate 自动提醒**

Post 发布后，**立即用 CronCreate 安排 8h 后发布 1 篇 Snippet Notes**（不依赖人工记忆）：

```json
{
  "cron": "{当前分钟+2分钟} {当前小时+8} {当前日} {当前月} *",
  "recurring": false,
  "prompt": "Substack MINI Notes 引流：为刚刚发布的 Post 写一篇 Snippet Note（50-120 词，含 1-2 个反直觉数字，不直接挂链接）。Post 主题是：[主题]。目的：让读者好奇点进 profile。不承认是 AI，以个人身份发言。"
}
```

⚠️ 规则：
- ⏰ 发布当天立刻发 Notes → ✘ 禁止。等待 8h 窗口，避免触发 Substack 的同一内容密集发布检测。
- ⛔ 一周内最多 2 篇 Notes + 1 篇 Post
- 📝 Notes 模板见 §3
```

### §5.3 图片生成与上传（默认每篇 Post 配图）

**策略：Agens 生成 → Substack 上传**

#### 步骤 1：Agens API 生成图片（每篇必做）

1. **调用（同步 Bash，timeout=120000，不用 run_in_background）：**
   ```bash
   python "C:\Users\59314\claudework\generate_image.py" "<prompt>" "C:\Users\59314\claudework\substack_img_{YYYYMMDD}_{slug}.jpg" "1536x1024"
   ```
   路径必须用双引号包裹，否则 Bash tool 会吃掉括号和波浪号导致路径变形成 `C:\Users\59314\Claudework\Users59314claudeworkgenerate_image.py`。

2. **结果判断**：
   - ✅ 输出 `IMAGE_URL: https://...` + `Saved to ... (N bytes)` → 记录本地路径，进 Step 2 上传
   - ❌ 空/超时/报错 → **直接重跑一次本命令**（不要检查 key/endpoint——已验证正确：`BASE_URL: https://apihub.agnes-ai.com/v1` / `API_KEY: sk-37fc8R90O1p5YQy7py4vQpmbWywfsnqg3qLJxxJg2cO8y3Ui` / `MODEL: agnes-image-2.1-flash`）
   - ❌ 重跑仍失败 → **跳过图片**，纯文字发布（不重试第三次）

**推荐尺寸**：`1536x1024`（3:2 横版，Substack hero image 最佳比例）

**固定 Prompt（每篇不变，保证风格一致）**：
```
Minimalist editorial illustration: {主角核心意象}. Style: abstract, flat design, muted blue/grey palette, no text. Mood: calm and focused.
```

{主角核心意象} 仅替换主角的标志性场景名词（如 "a lone developer at a desk" / "a person stepping off a corporate ladder" / "a seedling through cracked concrete" 等），不改变风格、色彩、氛围描述。

**Prompt 示例**（根据主角类型轮换）：
- 独立开发者：`Minimalist editorial illustration: a lone developer at a desk with multiple glowing screens showing upward growth charts, abstract geometric style, muted blue and green palette, no text`
- 辞职创业者：`Minimalist editorial illustration: a person stepping off a rigid corporate ladder onto an uncertain but bright path, warm orange fading to cool blue`
- YouTuber：`Minimalist editorial illustration: a creator with camera and microphone, audience as abstract dots connecting into a network, muted purple palette`
- 副业初期：`Minimalist editorial illustration: a seedling growing through cracked concrete, soft morning light, muted green and grey`

脚本成功后输出 `IMAGE_URL` 和本地路径。记录本地路径供下一步使用。

#### 步骤 2：上传到 Substack 编辑器

通过左侧 File Settings 面板的 Thumbnail 上传（优先于工具条 Image 按钮）

```
1. 在 File Settings 区域找到 Thumbnail 上传
   → click label[for="file-sidebar-file-input"]（可能不在 viewport，用 evaluate 点击：
     document.querySelector('label[for="file-sidebar-file-input"]').click()）
   → 系统文件选择器打开 → browser_file_upload({paths: ["本地图片路径"]})

2. 等待上传完成：观察侧边栏预览是否出现缩略图
   → 若 30 秒后仍无预览 → 跳过图片，纯文字发布

3. 若上传成功（缩略图预览出现）→ 带着图片继续发布
```

**⚠️ 上传受阻时的处理**：图片上传后 "Loading..." 会留在 File Settings 侧边栏，其 overlay 会拦截 Continue 按钮的点击（pointer-events）。此时必须：
1. 关闭 File Settings 侧边栏——如果 "Done" 按钮在 viewport 外（常见），用 evaluate `document.querySelector('.file-sidebar-header-button').click()` 关闭
2. 点击 "Continue" 按钮，弹出 Publish 对话框
3. 注意：图片可能实际上传成功（文件已被接受），只是缩略图预览未刷新。关闭侧边栏后 Continue 正常可用。上传状态不影响发布。

**重要**：图片是加分项，不是必须项。上传失败时跳过图片，纯文字发布。

### §5.2 写新 Notes（含 Post 链接预览）

```
1. navigate → https://substack.com/home
2. click text="What's on your mind?"（首页 composer）
   → 弹出 "New note" 对话框

3. Note 内容写入：Notes 编辑器是一个 contenteditable 元素
   （非标准 textbox），用 evaluate 注入：

   () => {
     const dialog = document.querySelector('[role="dialog"]');
     if (!dialog) return 'No dialog';
     const editor = dialog.querySelector('[contenteditable]');
     if (!editor) return 'No contenteditable';
     editor.focus();
     editor.innerText = '50-150词的Note内容\n\nhttps://post-url-here';
     editor.dispatchEvent(new Event('input', { bubbles: true }));
     return 'Text set';
   }

   → Substack 会自动解析 URL 并显示 Post 预览卡

4. click text="Post" 发布

5. 验证：页面 reload 后 Note 出现在信息流中
```

---

## §6存档与追踪

### 文章存档
每篇 Post 本地留一份 markdown：
- 路径：`C:\Users\59314\claudework\memory\substack-posts\{YYYY-MM-DD}-{slug}.md`
- 元数据：标题、主角名、主角平台、发布日期、URL、写作耗时

### 选题追踪表
`C:\Users\59314\claudework\memory\substack-posts\tracking.md`

```markdown
# MINI Posts Tracking

| 日期 | 标题 | 类型(A/B/C) | 主角 | 平台 | 收入数字 | 状态 |
|------|------|------------|------|------|---------|------|
| 2026-07-10 | ... | A | XXX | 即刻 | $12k MRR | published |
| ... | ... | ... | ... | ... | ... | idea |
```

### 主角池（长期维护）
`C:\Users\59314\claudework\memory\substack-posts\pipeline.md`

列出**已研究但还没写** + **正在联系** + **已拒绝** 的主角，标注来源平台、收入数字、特殊角。

---

## §7变现路径

### Phase 1（0-1000 免费订阅）
- 全部 Posts 免费
- Notes 引流为主
- 数据目标：订阅增长 ≥ 50/周

### Phase 2（1000-5000）
- Posts 免费（案例研究深度）
- 付费档："MINI Templates"——每篇 Post 的 playbook 扩展版（多 5 个案例 + 模板文件 + 月度更新）
- 定价：$8/月 或 $80/年

### Phase 3（5000+）
- 加付费社区（Substack Chat / 私人社群）
- 季度 Live 案例复盘
- 收入目标：$2k MRR

---

## §8 检测与修复

### 发布前自检清单（硬阻断）
任何一项不通过，不得发布：

- [ ] **Hook 检测**：第一段有数字/反直觉事实/场景？
- [ ] **数字密度**：全文具体数字 ≥ 5 个？
- [ ] **失败检测**：有至少 1 段写失败/犹豫？
- [ ] **Playbook**：有 3-5 步可复用模板？
- [ ] **去 AI 过渡词检测**：全文无 moreover/furthermore/consequently/therefore/in conclusion？
- [ ] **Contractions 检测**：每 200 词至少 1 个？
- [ ] **平行结构检测**：连续两个 H2 段落结构不全雷同？
- [ ] **总结句检测**：结尾无 "The lesson here…" / "In conclusion…"？
- [ ] **字数**：1800-2500 词（超 2500 砍案例，少 1800 加细节）
- [ ] **标题**：60-90 字符，前 40 有数字/反直觉/"I"？
- [ ] **纯英文检测（双重验证）**：全文无中文字符（CJK 统一表意文字范围 一-鿿）——英文读者看不懂中文原文
  - **Step A — Grep 扫描**：`grep -nP '[一-龿]' {源文件路径}`
  - **Step B — Python 二次验证**（Grep 通过后必须执行）：
    ```bash
    python -c "import re; content = open(r'{源文件路径}', encoding='utf-8').read(); matches = re.findall(r'[一-龿]', content); print(f'{'FOUND: ' + str(set(matches)) if matches else 'Clean'}')"
    ```
  - **铁律**：Grep 和 Python 结果不一致时以 Python 为准熔断。Grep 工具可能存在编码/引擎差异。
  - 特别注意中文名（肖弘、艾逗笔）、平台名（即刻）、口语词（口碑）、Source URL 标题——全要用英文替代或移除

### AI 红线（一票否决）
出现任一条，整篇重写相关段：
- 无数字支撑的断言
- "In conclusion" / "The lesson is" / "This demonstrates"
- 连续三个 H2 同一句式开头
- 没有主角原话引用
- 全篇无 failure 段落

---

## §9 启动首周任务表

| 任务 | 优先级 | 完成标志 |
|------|--------|---------|
| 写 1 篇定位 Post（"MINI 是什么、写给谁"） | P0 | 发布 |
| 写 2 篇案例研究 Posts（A 类 + B 类各一） | P0 | 发布 |
| 每天发 1 篇 Notes（Snippet + Data Drop） | P0 | 7 篇存档 |
| 建立主角池（pipeline.md ≥ 10 候选） | P1 | 文件存档 |
| 配置主页 About 与 Profile | P1 | 浏览器确认 |
| 设计主页 banner 与 logo | P2 | 可选首版先跳过 |

---

## §10 FAQ

**Q：主角不回应我私信怎么办？**
A：**不发私信**。全部基于公开数据写作。Substack 上的 Indie Hackers / Lenny's Newsletter / Stratecery 都是基于公开信息分析，不是采访。有公开数字就写，没有就换一个主角。

**Q：收入数字是编的吗？**
A：**绝对不编**。没有公开数字就不写具体数，用区间（"five figures monthly"）或标注"未公开"。编一次信任永久破产。

**Q：主角是中国大陆作者，写他会不会给他惹麻烦？**
A：红线：不碰政治、不碰敏感行业。商业案例 + 收入数字 = 安全。不确定就不写。

**Q：Substack 推荐算法怎么看？**
A：Substack 主推荐在 Explore 页 + 同类作者互推。Phase 1 别想算法，先把 **10 篇高质量 Posts** 铺完，算法自己会来。

---

**版本历史：**
- v2.1 (2026-07-21)：§5.1 Step 1——Create 按钮从 evaluate 切换为 `browser_run_code_unsafe` 单一路径，移除不稳定的 evaluate click 路径；§5.1 Step 3——HTML 注入从"方案 A（evaluate 传参）+ 备选 sections 数组"合并为单一 `_gen_inject.py` + `browser_run_code_unsafe filename` 路径，解决之前双引号 JS 解析失败→内容截断的 bug（5.7K/13K）；增加 N < 8000 熔断验证；移除 50+ 行死代码/分支/备选方案；新增 `_gen_inject.py` 独立脚本固化到 claudework 目录：§5.1 Step 3 + §8——CJK 阻断升级为双重验证（Grep + Python，Python 为裁判）；§5.1 Step 1——Create 按钮定位将 evaluate 方案升为首选（Playwright API locator 不可用），移除失效的 getByRole 备选；§5.1 Step 7——Notes 引流从"人工安排"改为 CronCreate 自动定时提醒；复盘2026-07-20执行（发布 Richard Wang）三个堵塞点已修入 SOP
- v1.8 (2026-07-16)：§5.1 Step 1——Create 按钮定位去除 [aria-label="Create"]（匹配 nav+profile 两个按钮导致 strict mode violation），改用 nav scope 限定；§5.1 Step 4——Description 字段写入被 Loading overlay 遮挡不生效的已知陷阱，增加"先关侧边栏→在发布对话框 Edit 中设置"的推荐顺序
- v1.7 (2026-07-14)：§2 Step 1——加入并行扫描等待策略（等待 ≥3 代理返回再锁定主角，Indie Hackers 最慢则跳过）；§5.3——上传 "Loading..." overlay 修复，改用 evaluate 点击 viewport 外的 Done 按钮；§6——移除"复盘记记忆"隐含要求（技能自包含，反馈教训直接改技能文件自身，不新建记忆文件）
- v1.6 (2026-07-11)：§5.1 Step 1——Create 按钮废除 Radix 硬编码 ID（#radix-P0-6），改用 [aria-label="Create"] + Playwright 原生 click（evaluate.click 不触发 Radix 菜单）；§5.1 Step 3——CJK 检测范围扩张到完整 markdown 源文件（不只 HTML），加重复段落检测；§5.1 Step 6——"Publish without buttons" 定位为"与 Publishing 同时弹出"，注明必须立即关闭而非等待；§2 Step 1——跳过扫描条件加可执行性校验（候选必须有英文可核实数据，否则强制重新扫描）；§8——纯英文检测细化扫描命令和易遗漏中文词清单
- v1.5 (2026-07-10)：§5.3——Agens 调用路径加双引号铁律（Windows 路径防断裂）；§5.1 Step 3——大 HTML 注入方案 A 重写为可执行 Python 文件模式+注释 Windows heredoc 陷阱+已验证 15K+ 字符直接传；§5 Step 3——新增 CJK 注入前阻断硬规则（正则 `[一-鿿]` 扫描，含中文直接熔断）
- v1.4 (2026-07-08)：§5.1 Step 3——加入 TipTap 标签兼容表（table/不支持项预处理）、bold 标记预处理、大 HTML 注入 SOP（方案 A/B）、`**text**`→`<strong>` 转换铁律；§5.3——Agens 生成 timeout=15s + 熔断规则（exit code 124 跳过）；§5.1 Step 6——发布后 3 步（tracking.md 更新 / pipeline.md 标记 / Notes 引流提醒）；§2 Step 1——加跳过扫描条件（pipeline 候选 ≥3 且 7 天内扫描过）；前置——Notion 不可达降级方案
- v1.3 (2026-07-07)：修复 §5.1 Step 2——两个 Title 字段陷阱（inline 决定性 + File Settings 可选），"Please set a title" 弹窗恢复流程；修复 §5.2——Notes 须用 contenteditable evaluate 而非 textbox；修复 §5.3——图片上传超时后 overlay 拦截 Continue 按钮的绕过步骤；§5.1 Step 6——"Send to everyone now" 失败弹窗处理与 "Your post is live!" 确认步骤
- v1.2 (2026-07-06)：§5 发布流程修正——Create+Article→编辑器、ProseMirror innerHTML 完整示例、左侧面板 File Settings 描述字段、"Continue"→发布对话框→"Send to everyone now" 真实发布路径；§5.3 图片上传增加 10s timeout 降级；§1 选题来源 V2EX 标注 WebFetch 不可达改用 WebSearch
- v1.1 (2026-07-03)：研究流程全自动重构——不联系主角、不采访、全部基于公开数据 + 子代理并行扫描
- v1.0 (2026-07-03)：首版，基于浏览器调研 + 同系技能反模式沉淀

> **复盘按 CLAUDE.md 技能修复标准流程执行**
