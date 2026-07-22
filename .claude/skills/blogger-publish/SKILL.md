---
name: blogger-publish
description: Blogger「WealthWiseDaily」个人理财博客全自动发布技能。v6.3 — 第40篇发布（2026-07-21）Side Hustle 真实时薪实验。已发布 40 篇 ✅ HTTP server + CORS fetch 注入方案稳定运行中
---

# Blogger · WealthWiseDaily · 全自动发布 v2.0

**触发**：`/blogger-publish` 或「发一篇 WealthWiseDaily」

---

## PHASE 0：硬性去重（熔断级，不可跳过，必须先执行）

**执行时机**：每次启动本技能、写任何内容之前。必须先到 Blogger 已发布文章列表页提取所有已发布标题。

### 步骤

1. 导航到 Blogger 后台文章列表页：`https://www.blogger.com/blog/posts/2611555253226715248`
2. evaluate 提取所有已发布文章标题：
   ```javascript
   // 🔥 [v6.0] 修复：body.innerText + SmartMoneyMoves 分割法在2026-07-18实测返回空数组
   // 实测有效方法：querySelectorAll('[role="listitem"]') + textContent 提取
   const items = document.querySelectorAll('[role="listitem"]');
   const titles = [];
   items.forEach(item => {
     const text = item.textContent.trim();
     const lines = text.split('\n').map(l => l.trim()).filter(l => l.length > 10 && l.length < 200);
     if (lines.length > 0) titles.push(lines[0]);
   });
   // titles[] 现在包含所有已发布文章标题（含 "SmartMoneyMoves" 后缀，比对时取前缀即可）
   ```
3. 比对规则：
   - 待发布标题与 titles[] 中任一元素完全匹配 → **熔断，不发布，报告"已发布过：[重复标题]"**
   - 待发布标题关键词与 titles[] 中某元素高度重叠（同一事件/同一模型名/同一主题）→ **熔断**
4. 熔断后终止流程，不写任何新内容

### 铁律
- 每次启动技能必须先执行此事。不做就去写内容 = 流程违规。
- 不依赖记忆或历史记录——必须实时从页面提取。

---

**本技能不是"生成计划后等待确认"的助手流程，而是"具备硬阻断条件的全自动执行流程"。任何确认式停顿都视为偏移。**

## 博客信息

| 字段 | 值 |
|------|-----|
| 博客名 | WealthWiseDaily / https://aineedhelpfromotherai.blogspot.com |
| 后台 | https://www.blogger.com/blog/posts/2611555253226715248 |
| Google 账号 | chenyuan19920509@gmail.com（已登录）|
| 博主资料名 | SmartMoneyMoves |
| 定位 | 个人理财 · 省钱攻略 · 英文 |
| 目标字数 | 2000-2500 词（首次落笔即应 ≥2000，不以 1800 为合格线）|
| 目标美式受众 | Gen Z / Millennials，30-45 岁，中产焦虑 |
| 当前博文 | 42 篇已发布（最新: 2026-07-22 第42篇 Grocery Budget 选题 — I Tracked Every Grocery Receipt for 30 Days — 5 Swaps That Cut My Bill by $340）|

---

## §0 文风引擎：NerdWallet + Penny Hoarder 样式调查

### 从 NerdWallet 真实文章提取的核心风格规则

**规则 A：用 personal experiment 代替抽象说教**
- NerdWallet 每篇至少 1 个作者亲身实验（"I tried X, here's what happened"）
- 必须写清楚行动 + 时间 + 结果 = 数字
- 例：NerdWallet writer Amanda Barroso used a Brick device → cut spending by **$300** in one month
- 例：NerdWallet writer Kate Ashford tracked spending for 30 minutes → saved **$600** in the year ahead

**规则 B：数据必须有出处**
- NerdWallet 的数据来源格式："[Source] survey of [N] [demographic], conducted by [firm]"
- 例："according to a NerdWallet survey, 45% of Americans say..."
- 例："The Penny Hoarder's 2026 Financial Anxiety Barometer found 65% of Americans..."
- 禁止凭空编造"专家说"——必须引用真实报告或有真实署名的作者

**规则 C：段落结构 = 1 句 hook + 1-2 句展开 + 可选 1 句数字/数据**
- 每段 1-3 句，禁止超 3 句
- 句长下限 8 词、上限 28 词
- NerdWallet 常见段落模式：
  ```
  {问题/观察句}
  {数据句或具体例子}
  {如果合适：解决办法句}
  ```

**规则 D：作者署名与专家引用**
- 作者署名格式：NerdWallet 写 "By [Name], [Title]"
- 专家引用格式："[Quote]," said [Name], [Title] based in [City, State]
- 内部作者引用："NerdWallet writer [Name] found..."

**规则 E：人称与口吻**
- "we" 集体口吻："Here's what we found"，"We'd say yes"
- "you" 读者直接对话："Ask yourself these questions"
- 非正式但权威，不用太口语："Here are some more ways to make tracking your spending impactful"

**规则 F：标题格式（来自 NerdWallet 标题分析）**
- 通常为 60-80 字符，含问句或"数字 + 关键词"
- 例子："Is an Annual or Monthly Subscription Better? Plus More June Money Questions"
- 例子："What to Buy (and Skip) on Prime Day 2026"
- 例子："Ready for Summerween? Redditors Share Budget-Friendly Tips"
- 本博客使用相同模式

---

## §0a Anti-AI Voice：去 AI 味引擎

### 核心原则

把"完美"变成"真实"。真人写作会有：小瑕疵、情绪起伏、口语化、甚至轻微重复。读者不是在看教科书，是在听一个人聊天。

每次生成文章后，先用本节规则自检，再走 §5 质量门。

---

### 规则 1：长短句混搭，打破平滑节奏

每 3-4 句必须插入 1 个极短句（3-8 词），像钉子一样打断 AI 式平滑节奏。

❌ AI 节奏（平滑但乏味）：
> I sat down one Sunday afternoon and went through every single recurring charge on my account. The total hit me harder than I expected. I was paying roughly $640 per month for things that brought me almost zero value.

✅ 真人节奏（有起伏）：
> I finally sat down last Sunday, coffee in hand, and opened my credit card statements. Man… the total actually made me swear out loud. Dozens of subscriptions I'd completely forgotten about.

**短句弹药库**（轮换使用）：
`I was shocked.` `Total waste.` `Never again.` `Yeah. I know.` `That hurt.` `You get the idea.` `So I did.` `Dumb, right?` `That stung.` `Zero regrets.` `Worth it.`

---

### 规则 2：用真人过渡词替代 AI 过渡词

| ❌ AI 过渡 | ✅ 真人过渡 |
|------------|------------|
| Moreover, / Furthermore, | You know, / Honestly, / Look, |
| It is important to… | The truth is… |
| It is worth noting that… | The funny thing is… / Funny enough… |
| This demonstrates that… | I'll be honest… / Long story short… |
| Consequently, / Therefore, | So yeah, / And guess what? / Which brings me to… |

**每篇文章至少用 2 个真人过渡词。** 不要连续两段用同一类过渡。

---

### 规则 3：自嘲 + 真情绪，拒绝端着的权威

每篇文章至少 1 处 self-deprecating humor。英文读者最喜欢这个，也是最有效的去 AI 味手段。

❌ "I reviewed my subscriptions and found inefficiencies."
✅ "I'm the person who paid **$316** per gym visit. Let that sink in."

❌ "The total was significantly higher than expected."
✅ "Yeah, I felt pretty stupid when I saw it."

❌ "One must carefully evaluate recurring expenses."
✅ "I almost kept paying for something I hadn't opened in 11 months. Dumb, right?"

❌ "It is advisable to cancel unused subscriptions."
✅ "I was too embarrassed to admit I'd forgotten about it. So I just let it keep billing me. Pathetic, but true."

---

### 规则 4：破坏完美平行结构

**核心问题**：如果每个 H3 段落都用同一句式（"I signed up → I used once → I cancelled"），读者立刻识别为 AI。

**修复方法**：
- 每个故事换一个切入角度：有的从情感（"This one hurt the most"）、有的从数字（"**$210** for a single nap"）、有的从对话（"The rep offered me a freeze. I almost said yes."）
- 不要每个 H3 都包含 "sign up → use → cancel" 三段
- 有的故事停在"我还在付"，有的停在"我笑自己"

**§4.1 切入角度表** 中的 5 种结构是参考指南，不是硬模板。连续 2 个 H3 结构雷同，必须改其中一个。

---

### 规则 5：口语化词汇 + Contractions

| ❌ 书面词汇 | ✅ 口语词汇 |
|-------------|------------|
| approximately | around / a shocking |
| utilize | use |
| demonstrate | show |
| was paying roughly | was somehow bleeding |
| recurring charge | auto-payment / that thing draining my account |
| cancel the service | kill it / dump it / drop it |
| The total was $640 | The total hit me harder than I expected |

**Contractions 强制**：`I'm / I'd / it's / wasn't / didn't / couldn't / you're / that's / don't / won't`。每 200 词至少 1 个，全文至少 5 个。

---

### 规则 6：去总结句（最重要）

**❌ 禁止句式**（AI 最爱，碰都不要碰）：
- "The lesson here is…"
- "This experience taught me that…"
- "What I learned from this is…"
- "This demonstrates the importance of…"
- "In conclusion…" / "To summarize…"
- **"But here's the thing"** — ChatGPT 招牌句式，极容易被识别
- **"The problem with X isn't Y. It's that Z."** — AI 二元对比结构
- **"The pattern is universal"** / "The math really is that simple" — 伪深刻总结句

**✅ 替代方案**：直接以具体场景、动作、对话或开放问题收尾。让读者自己总结，不要替他总结。

❌ "The lesson is that subscriptions should be judged by usage, not by price."
✅ "Judge subscriptions by how often you use them, not by what they cost. That one rule has saved me more than any budgeting app ever did."

❌ "This taught me the importance of regularly reviewing my finances."
✅ "I set a recurring calendar reminder called 'Subscription Purge' every six months. 30 minutes. Saved me thousands already."

❌ "But here's the thing I realized after thinking about it…"
✅ "Look, after stressing about it for a few days I realized something obvious."

❌ "The problem with the gas hike isn't the dollar amount. It's that it's new."
✅ "What stings isn't the size of the number. It's that this cost wasn't there six months ago."

❌ "But the pattern is universal: there is waste in almost every household budget."
✅ "Thing is, most people are bleeding money somewhere. Almost always in places they approved years ago and never circled back to."

---

### 规则 7（2026-07-10 新增）：移除 AI 标记句式结构

**核心问题**：即使每个词都口语化，特定的句式结构仍然是 AI 签名。读者不识别个别单词，但识别句式节奏。

**四类高危结构（每次生成后全文扫描）：**

**① "But here's the thing" / "Here's the thing" 家族**
- 这是 ChatGPT 的 signature phrase，出现在数以百万计的 AI 生成文本中
- 替换：`Look,` / `Honestly,` / 直接说观察（跳过过渡短语）
- ❌ "But here's the thing I realized after fuming about it for a few days."
- ✅ "Look, after stressing about it for a few days I realized something obvious."

**② "The problem with X isn't Y. It's that Z." 二元对比结构**
- AI 最爱用"不是A，是B"的完整对比句——读者熟悉这个节奏
- 替换：拆成两句，用具体名词替代抽象代词
- ❌ "The problem with the gas hike isn't the dollar amount. It's that it's new."
- ✅ "What stings isn't the size of the number. It's that this cost wasn't there six months ago."

**③ "The X is universal / The math is simple" 伪深刻总结**
- AI 在每个故事结尾喜欢加一句"放之四海而皆准"的总结——读者在 Reddit 上管这叫 "the AI mic drop"
- 替换：要么直接闭嘴（留白），要么转成幽默自嘲
- ❌ "But the pattern is universal: there is waste in almost every household budget."
- ✅ "Thing is, most people are bleeding money somewhere. Almost always in places they approved years ago and never circled back to."

**④ 双重情感词并列表述**
- AI 喜欢用 "both relieved and annoyed"、"excited but nervous" 等对比情感并列——显得像在列清单
- 替换：只说一个情感 + 具体动作为什么
- ❌ "I hung up feeling both relieved and annoyed at myself."
- ✅ "I hung up annoyed at myself. Mostly because the whole thing took 14 minutes."

**全文性检测方法**（写完所有段落后再做，不边写边修）：
1. 扫描每一段找上述 4 类结构
2. 如果某段找不到更好的替换方案，删掉该段换一种完全不同的话说
3. 如果某段只有 1-2 处 AI 句式但其他都 OK，修改该句即可，不必整段重写

每次生成后对照自查这一段：

| 维度 | ❌ AI 风格 | ✅ 真人风格 |
|------|-----------|------------|
| 调查数据 | "According to a NerdWallet survey, the average American spends $30 to $80 per month on unused subscriptions alone. I was spending nearly 8x that amount." | "NerdWallet says the average person wastes **$30–80** a month on subscriptions they don't use. I was somehow doing eight times that. Yeah, I felt pretty stupid when I saw it." |
| 焦虑数据 | "The Penny Hoarder's 2026 Financial Anxiety Barometer found that 65% of Americans say recurring costs are their biggest financial stressor." | "I just read that **65%** of Americans say recurring bills stress them out more than anything else (according to The Penny Hoarder). After seeing my number, I totally get why." |
| 段落开头 | "I sat down one Sunday afternoon and went through every single recurring charge on my account." | "I finally sat down last Sunday, coffee in hand, and opened my credit card statements. Man… the total actually made me swear out loud." |
| 数字表达 | "I was paying roughly $640 per month." | "I was somehow bleeding **$640** a month. Each one a charge I'd approved and forgotten." |

---


### 结尾规则

- 结尾 100 词内不得出现抽象说教
- 结尾固定格式：**评论钩子 CTA** — 以 `<p><b>Drop a comment:</b> What [topic] have you tried? I'd love to compare notes.</p>` 收尾。无其他选项。
- 禁止："In conclusion" / "To summarize" / "The lesson is" / "This taught me"

## §1 可引用数据源（采集自 2026 年 6 月 NerdWallet / Penny Hoarder 真实文章）

以下数据均来自 2026 年已发布的头部博客文章，可在文章正文中直接引用。

### NerdWallet 调查数据
- 计划夏季旅游的美国人平均支出 **$3,940**（含机票/住宿）
- 89% 的夏季旅行者会采取省钱措施
- 67% 认为多付钱买可退票值得，62% 同样认为旅行保险值得
- 45% 美国人希望减少非必要支出
- 夏季旅行者省钱方式：35% 自驾代替飞、33% 按价格选住宿不按体验

### Penny Hoarder 调查数据
- Penny Hoarder 2026 Financial Anxiety Barometer：65% 美国人说生活必需品（房租/食品/水电）是最大财务焦虑源
- 订阅审计：很多人每月在未使用的订阅上花费 **$30-$80**

### 通用理财数据
- 500-1000 美元是起步应急基金目标
- 3-6 个月生活支出是完整应急基金目标
- 50/30/20 预算规则是引用最广的预算方法
- 高利率储蓄账户（HYSA）当前 APY 约 3.5-4.5%

---

## §2 SmartMoneyMoves 人设 → 行文引擎

**规则 1：拒绝抽象，给具体数字**
  ❌ "Saving money is important for your future."
  ✅ "I cut my grocery bill from **$680** to **$410**/month."

**规则 2：用 personal experiment 代替教科书定义**
  ❌ "A budget is a financial plan that helps you track income and expenses."
  ✅ "I avoided my bank statements for months. When I finally checked, I was down **$2,300**."

**规则 3：承认不完美，但给出路**
  ❌ "You should save 20% of your income every month."
  ✅ "Saving 20% is the ideal. Start with 5%. Seriously."

**规则 4：质疑行业惯例**
  ❌ "A 401(k) is a great retirement savings vehicle."
  ✅ "Those 'management fees' in fine print? They're eating **0.5-1%** every year."

**规则 5：短句 + 口语化**
  ❌ "It is important to consider the various factors that may impact your ability to save."
  ✅ "Want to save more? Stop overthinking. Pick one thing and do it this week."

---

## §3 标题生成器

| 公式 | 模板 | 示例 |
|------|------|------|
| **Question + Hook** | `[Question]? Plus [Angle]` | "Is an Annual or Monthly Subscription Better? Plus More June Money Questions" |
| **Number + Action** | `[N] Ways to [Goal]` | "9 Ways to Cut Your Monthly Bills Without Feeling the Pinch" |
| **Mistake + Cost** | `[N] [Topic] Mistakes Costing You $X` | "7 Subscription Mistakes Costing You $3,200 a Year" |
| **Experiment** | `I [Action] for [Time]. Here's What Happened` | "I Tracked Every Dollar for 30 Days. Here's What I Found" |
| **数据冲击** | `[Number] [Thing] I Found When I [Action]` | "$2,400 in Waste I Found When I Opened My Bank Statement" |
| **反直觉** | `What [Common Thing] Actually Costs You $[X] a Year` | "What Your 'Small' Daily Coffee Actually Costs You $1,825 a Year" |

**标题检查清单**：
- [ ] 含具体数字
- [ ] 60-80 字符
- [ ] 有个人角度或问句（NerdWallet 风格）
- [ ] 包含 1 个情感钩子（Costing / Quietly / Surprising / Without Pain）

⚠️ 连续两篇禁止使用同一标题公式（从 6 种中轮换）。

---

## §3b 选题方法（头部交叉研究驱动）

**⚠️ 重要**：不按预设选题表生成。每次执行 `/blogger-publish`，必须先研究头部博客当前热点，找交叉点，再合成独特角度。

### 研究流程

1. 用 **Exa web_search_exa** 搜索 2-4 个头部博客最新文章
   - **NerdWallet** (`nerdwallet.com/finance`) — 数据驱动，comparison 内容
   - **The Penny Hoarder** (`thepennyhoarder.com`) — 省钱故事 + 操作指南
   - **Financial Samurai** (`financialsamurai.com`) — 个人经验
   - **Mr. Money Mustache** (`mrmoneymustache.com`) — FIRE 运动
2. 提取每家的当前热题：标题 + 核心角度 + 数据点
3. 找交叉点：什么主题多家都在做？同一主题的不同角度是什么？
4. 合成：交叉点 + §0 文风引擎 + SmartMoneyMoves 人设 → 你的独特角度
5. 如果找不到交叉点，继续翻更深页面

### 搜索工具

使用 **Exa web_search_exa**（`mcp__exa__web_search_exa`）搜索，支持 `site:nerdwallet.com` 格式过滤。

### 独创性规则
- NerdWallet 用调查数据 → 你用 personal experiment
- Penny Hoarder 用列表 → 你用故事串联
- 从不直接抄标题、结构或角度
- 每个 H3 tip 必须包含 1 个"我"的亲身经历

### 选题多样性约束（2026-07-03 硬性规则）

**问题**：截至第 9 篇，最近连续 3 篇都是订阅审计角度，内容同质化严重。

**规则**：
1. 同一大主题（订阅、预算、储蓄、旅行、投资等）连续出现 **≤2 篇**即需切换，禁止连续 3 篇同一主题
2. 每次执行前先检查最近 3 篇已发布博文的标题/主题（在博客后台或首页扫读），本篇主题必须与最近 2 篇都不同
3. 如果研究结果指向的交叉点与最近 2 篇主题重复，**重新找交叉点，不将就**

**主题库**（每篇生成前随机选一个不同方向）：
- Credit card audit：钱包卡片审计、年费与返现比对、卡片取舍策略
- Prime Day 复盘：哪些 deal 值得、哪些是坑、退货经验
- Travel budgeting：暑假旅行省钱策略、机票/住宿/餐饮的预算分配
- Midyear savings check：半年储蓄回顾、调整下半年预算、应急基金进度
- Loud budgeting / 大声预算：2026 流行语的新演绎
- Insurance review：跟着 NerdWallet 的 Kate Ashford 风格做保险审计
- Emergency fund building：给月光族的 6 个月基金计划
- Side hustle real talk：8 个现实副业的真实收入与时间投入
- Grocery budget：两周食材预算、meal prep、减少食物浪费

**每次执行 §3b 研究前，先检查最近 3 篇主题，从主题库中排除最近 2 篇已用的方向。**

### 标题公式多样性审计（v5.7 新增）

**规则**：
1. 在 Step 1 选标题前，列出最近 3 篇标题，标注每篇用的公式类型（从 §3 公式表 6 种中识别）
2. 本篇必须使用与最近 2 篇都不同的公式

---

## §4 文章模板（填变量）

### §3c 生文前字数预算（🔥 硬步骤，禁止跳过 — 防止写完才补写）

**§3c 字数指南**：
- 最低 1,800 词，上不封顶。目标最低线不是"刚好 1,800"——是写满内容需要的自然总量，远超最低线也无所谓。
- 每次写时问自己：这段是"刚刚够"还是"自然讲完了"？刚刚够就继续写，直到故事自然结束。
- 每段应有具体感：场景/数字/自嘲/情绪。空泛叙述不加词。

**预算公式**：
1. 直接写 6-8 段（intro），然后用 `grep -c '<p>'` + `sed wc -w` 算出段均词作为基准
2. 基准 = 总词数 ÷ 总段落数
3. 目标词数 ÷ 基准 = 最少段数。段数不够就加段，不拉长单段
4. 写一段、验一段累计

**精简骨架（52 段目标型，适配 2000-2500 词区间）**：
```
块            段数    累计  备
Intro         7 段     7    痛点→发现→数据→场景
4 × H3        7×4=28  35   每 H3 = 7 段（每段 35-45 词）
数字/拆解     5 段     40
How-to        8 段     48   引导+5步
结尾+3内链    4 段     52
```
合计 **52 段 × 35-45 词 ≈ 2,050 词。** 写一段验一段，段内 2-3 句。目标区间 2000-2500 词。若首次落笔 <2000，在现有段落中扩展细节（数据引用、具体数字、自嘲）。若首次就 >2500，砍段落数最少的 H3 的前 2 段。

**执行铁律**：
- 写之前先把上面骨架（含每个 H2/H3 的标题文字）落成注释/草稿，再填内容
- 首次 Write 后 `wc -w` 应直接 ≥2000；若仍 <2000，**只在已有段落扩细节（数据/数字/自嘲），不新建 H3、不新建 H2**
- 若首次就 >2500，砍段落数最少的 H3 的前 2 段，不重建
- 本步骤是 Step 2 的前置硬门槛，未做预算不得进 Write

### 模板 A（主力 · Personal Experiment + List · 1800-2200 词）

```
H1: {Title with number + hook — must grab attention in first 40 chars}

H2: {Personal story intro — 2-3 段}
  {1 sentence: pain point + scene (coffee in hand, Sunday afternoon)}
  {1-2 sentences: discovery — I found $X draining every month}
  {1 sentence: what this article covers}

H2: {Section 1 heading — e.g., "The Subscriptions I Completely Forgot About"}
  H3: 1. {Story 1 — vary opening angle}
    {2-3 sentences: from emotion OR from number OR from dialogue}
    {1 sentence: data ref or self-deprecating punchline}
  H3: 2. {Story 2 — different opening from H3#1}
    {2-3 sentences}
    {1 sentence: result + number}
  H3: 3. {Story 3 — different opening again}
    {2-3 sentences}
    {1 sentence: what I did about it}

H2: {Section 2 heading — e.g., "The Ones I Actually Kept"}
  H3: 4. {Story 4 — kept sub, why it's different}
    {1-2 sentences: usage story}
    {1 sentence: cost-per-use math}
  H3: 5. {Story 5 — another discovery}
    {2-3 sentences}

H2: {How to Run Your Own Audit in 30 Minutes}
  {3-4 steps, each 1-2 paragraphs. DO NOT make every step the same length}
  {End with a challenge or open question}

No Pro Tip section. Closing = 1-2 sentences, must be challenge or comment CTA.
```

### §4.1 段落级模板

每个 H3 的故事结构**必须变化切入角度**，禁止连续两个 H3 用同一句式。按固定轮换顺序使用以下 5 种切入角度：

| H3 序号 | 切入角度 | 段落 1 | 段落 2 | 段落 3 |
|---------|---------|--------|--------|--------|
| H3 #1 | **情感切入** | 羞愧/惊喜/尴尬 | 发现经过 | 结局+数字 |
| H3 #2 | **数字切入** | $XX 先亮出来 | 我当初怎么签的 | 我怎么处理的 |
| H3 #3 | **对话切入** | "I called to cancel…" | 对方怎么挽留 | 我坚持了/没坚持 |
| H3 #4 | **场景切入** | 某个下午/app上/账单里 | 回忆当初 | 如今怎么不同 |
| H3 #5+ | **反直觉切入** | "Judge subs by usage, not price" | 举我自己的反例 | 你的行动 |

**段落长度规则**（来自 §0a 规则 1 + 2026-07-07 复盘 + 2026-07-18 排版审计修复）：
- 每段 1-3 句，禁止超 3 句
- 🔥 **断段执行规则（v5.7 新增）**：写完一段后，若句子数 ≥4，必须在第 3 句后硬断为两个 `<p>`。**不要"合并成一句长话"——直接在第 3 句句号后开新 `<p>`**。例：
  ```html
  <!-- ❌ 错误：5 句塞进一个 p -->
  <p>I sat down on a Sunday. My bank account was open. The picture was not pretty. I'd been manually moving money for years. I kept telling myself I'd fix it next month.</p>
  
  <!-- ✅ 正确：在第 3 句后断开 -->
  <p>I sat down on a Sunday. My bank account was open. The picture was not pretty.</p>
  <p>I'd been manually moving money for years. I kept telling myself I'd fix it next month.</p>
  ```
- 每 3-4 句插入 1 个极短句（3-8 词）
- 整段只有 1 句可以——如果那句是强力定论或自嘲
- **碎片句融合规则**：同一段落内若有多个 3-8 词的碎片句，用 em dash `—` 或逗号合并为单句。禁止将碎片句各自独立成句导致段落超 3 句。例：`"Same plane, same seat, same destination, same airline. Just a different departure time."` ✅（2 句）vs `"Same plane. Same seat. Same destination. Same airline."` ❌（4 句）
- **🔥 碎片句不计入 3 句限额（2026-07-07）**：≤8 词的碎片句（如 "Dumb, right?" "In two weeks." "Total waste."）不占用本节的 3 句段落上限。理由是碎片句本质是同句语气停顿，非独立句。段落检查工具应忽略 ≤8 词的短段尾碎片句。此规则解决 §0a 规则 1（每 3-4 句插 1 个极短句）与本节段长规则之间的执行矛盾。
- **🔥 [v5.7] 字数校验工具**：生成正文后，用 evaluate 扫描段落长度分布，不允许 4+ 句段落超过总段落的 10%。超过则回修。
  ```javascript
  // 字数校验工具（Step 3 质量门前执行）
  const paras = document.querySelectorAll('article p, .post-body p');
  const over3 = Array.from(paras).filter(p => {
    const s = p.textContent.split(/[.!?]+/).filter(x => x.trim().length > 0);
    return s.length > 3;
  });
  const ratio = over3.length / paras.length;
  // ratio 应 < 0.10（10%），超过即需要拆分段落
  ```

**破坏平行结构检查**：
- 写完前 2 个 H3 后，检查开头句式是否雷同
- 如果都用了 "I signed up for [X] because…" → 改一个为 "You know what was the most painful one? [Y]."

---

## §4.2 排版规范（视觉风格）

### 标题层级（HTML 映射）
| 层级 | 标签 | 用途 | 数量限制 |
|------|------|------|---------|
| H1 | 由 Blogger 标题输入框管理 | 文章主标题 | 1 |
| H2 | `<h2>` | 大章节标题（intro / section 1-3 / closing） | 5-7 |
| H3 | `<h3>` | 每个 tip 标题 | 4-6（或标题实际承诺数字）|

### 内联格式
- 数字/金额：一律用 `<b>$540</b>` 或 `<b>65%</b>` 加粗（⚠️ 不用 `<strong>`，Blogger 编辑器转义方式特殊，`<b>` 更稳定）
- 专家引语：段落内用双引号 `"..."`，不单独用 `<blockquote>`（NerdWallet 风格是段落内引用，不单列引用块）
- **Pull quotes**：在关键 hook 句前后加 `<i>` 斜体，不用 `blockquote`——英文平台习惯段落内强调，不单独摘出
- 强调：偶尔用 `<i>`，每篇文章不超过 5 处
- 列表：只在真正需要对比的 3+ 项才用 `<ul>/<li>`，日常用段落
- **CTA 评论钩子**：结尾段落加入一句开放问题，格式：`<p><b>Drop a comment:</b> What's the dumbest subscription you're still paying for?</p>`

### 间距与可读性
- 段落之间必须有空行（HTML 中 `<p>...</p>` 天然带 margin，不要额外加 `<br>`）
- 每个 H3 前后各空一行
- 禁止使用 `<br>` 强行换行，用段落分割
- 所有内链前带 `» ` 符号：`<p>» <a href="...">Read more: ...</a></p>`

### 移动端适配
- 每段 ≤3 句（移动端长段会劝退读者）
- 所有 `<b>` 加粗的数字在移动端自动突出，无需额外样式
- 内链不堆砌，每篇 3-5 条就够

---

## §4.3 配图规范 · 可执行流程

### 原则

全部配图使用 Agnes API 生成真实图片，**禁止** Unsplash、stock photo URL 或任何占位图。

| 角色 | 必选 | 说明 |
|------|------|------|
| Hero 图 | ✅ 必选 | 文章顶部紧接第一个 H2 上方，1024×1024 |
| 内文插图 | ✅ 必选 | 每 400-600 词插入 1 张，打断文本墙，维持阅读节奏 |
| 数据图/信息图 | 推荐 | 将关键数字可视化（省钱 breakdown、百分比对比等）|

**🔥 [v5.8] 图片数量标准（基于 Buzzsumo/BrandGene/Orbit Media 调研）**：

| 文章长度 | 建议图片数 | 图片类型分配 |
|----------|-----------|------------|
| 1,200-2,000 词 | 3-5 张 | 1 hero + 2-4 内文 |
| **2,000-3,000 词** | **5-8 张** | 1 hero + 4-6 内文 + 可选数据图 |
| 3,000+ 词 | 8+ 张 | 1 hero + 5-7 内文 + 数据图 + 步骤图 |

**关键数据**（Buzzsumo 百万篇分析）：每 75-100 词一张图的文章，分享量是少图文章的 2 倍。每 400-500 词插入一张图是个人理财博客的甜区。

**图片位置规则**：
- Hero 图：文章顶部，第一个 H2 之前（当前做法 ✅）
- 内文图 1：在第一个 H2 后的 2-3 段（打破 intro 长墙）
- 内文图 2：在"数字拆解"或"对比"章节
- 内文图 3：在 How-to 章节开头或中间
- 内文图 4（如有）：在倒数第二个 H2 前（为结尾做视觉缓冲）

### §4.3a 图片生成（统一脚本 — v6.1 取代旧三步分散操作）

**一键脚本（唯一路径）：**
```bash
# 自动检测占位符 + 从 alt 取 prompt + 并行生成 + 替换 + 质检
python scripts/auto_blogger_images.py
```

### Prompt 工程规范（7 层次）— 每次写 prompt 逐层检查

#### 硬性规则：视觉风格轮换（核心新增）

**每次生成图片前，先确定本文的选题类型，从下表选出对应的视觉风格，禁止连续 2 篇使用同一风格。**

| 选题类型 | 视觉风格关键词 | 调色方向 | 构图范例 |
|----------|--------------|---------|---------|
| 订阅/账单审计 | flat lay, overhead shot, bird's eye view | 冷暖均可，木色/米白 + 点缀色 | 桌面俯拍：手机、信用卡、收据、咖啡杯平铺 |
| 个人实验/省钱故事 | environmental portrait, natural light, real moment | 暖调为主（golden hour, warm cream） | 人物在生活场景中看手机/电脑，中景 |
| 省钱技巧清单 | warm minimal, cozy corner, detail shot | 暖白/橄榄绿/奶油色 | 咖啡店一角、笔记本+计算器+笔，平铺或斜45° |
| 投资/财务分析 | clean professional, crisp, modern | 冷色调（navy, white, slate grey） | 办公桌：显示器显示图表、眼镜、键盘，近景 |
| 生活方式省钱 | candid street photography, urban life | 自然日光，城市色调 | 街边、通勤中、市场，人物抓拍感 |
| 购物/消费反思 | close-up, textured, tactile | 暖灰/驼色，微暗 | 手拿信用卡、购物袋、退货标签，特写 |
| 能源/固定费用 | documentary style, real home interior | 柔和自然光（overcast, soft white） | 客厅/厨房真实环境，温度计、电表等细节 |
| 副业/收入 | 创意俯拍或半俯拍 | 明亮（bright white, soft yellow） | 桌面：手机屏幕显示收入、电脑、笔 |

**强制执行规则**：
- 每次执行先看本文选题类型，在上表找到对应行，使用该行的视觉风格关键词
- 禁止连续 2 篇使用同一视觉风格（从 §9 版本历史中查看上篇使用的风格）
- 调色方向必须跟着风格走，禁止所有图片都暖调/amber

| 层次 | 要求与禁止 | 示例片段 |
|------|-----------|---------|
| ① 场景 | 具体人物+动作+环境，谁在哪做什么 | "a young woman at a kitchen counter scrolling through phone statements" |
| ② 视觉风格 | 从上方轮换表选取当前选题对应的风格 | "flat lay, overhead shot, bird's eye view" |
| ③ 光线与构图 | 光线色调 + 景别构图，跟随风格轮换 | "soft morning window light, centered composition, from above" |
| ④ 视觉元素 | 关键物件，不少于 2 个 | "iPhone with subscription charges, credit cards, coffee cup, receipts" |
| ⑤ 禁止元素 | 不能出现的 | "no text overlays, no watermarks, no cartoon, no AI art style, no hands in frame" |
| ⑥ 概念隐喻 | （可选）核心隐喻 | "financial audit, taking control of recurring payments" |

**Prompt 组装规则**：`①, ②, ④, ③, ⑤` → 合成一句，不超过 80 词。不包含"⑥ 概念隐喻"时无影响。

---

#### 场景随机化规则（防止千篇一律，第二道防线）

**核心问题**：即使切换了视觉风格，如果每次都写"person looking at phone/laptop"，Agnes 产出的人物/环境/构图仍然趋同。

**修复**：每次生成时①场景必须自由发挥，随机构思一个与前次完全不同的场景：

- **视觉风格 + 场景双重变换**：风格已经变过了（flat lay → environmental portrait），场景还要再变（厨房 → 阳台 → 地铁站 → 街角咖啡桌 → 客厅沙发）
- **人物+环境+动作三者至少换两个**：人物性别、年龄可随意，环境彻底换掉
- **不设固定场景池**，每次独立构思，越随机越好

---

#### 欧美视觉调性规则（第三层约束）

| 维度 | 要求 | 示例关键词 |
|------|------|-----------|
| 人物 | 欧美面孔白人/混血，自然皮肤纹理，无磨皮 | "Caucasian, natural skin texture, freckles, no smoothing" |
| 环境 | 典型纽约/伦敦/巴黎生活场景 | "Brooklyn apartment, London row house, Parisian café" |
| 摄影风格 | **跟随 §4.3a 视觉风格轮换表，不得固定** | 从轮换表对应行选择，flat lay / candid / documentary / clean professional 等 |
| 光线 | 自然光优先，拒绝过度打光 | "natural window light, overcast sky, soft golden hour" |

**强制执行**：每次组装 prompt 时，视觉风格轮换（②）和场景随机化（①）必须在场。prompt 格式：`①场景, ②视觉风格, ④视觉元素, ③光线与构图, ⑤禁止元素`，不超过 80 词。

---

### §4.3b HTML 嵌入流程（由 `auto_blogger_images.py` 自动完成 — 脚本从 alt 属性提取 prompt，并行调 API，替换占位符，无需手动操作）

生成正文 HTML 时，在每个图位插入占位符：
```html
<!-- Hero 图（第一个 H2 上方）-->
<img src="__HERO_IMG__" alt="{prompt 浓缩为 alt 文本}" style="max-width:100%;height:auto;border-radius:8px;margin:0 0 24px 0;" loading="lazy">

<!-- 内文图 1（第一个 H2 后 2-3 段）-->
<img src="__INNER_IMG_1__" alt="{alt 文本}" style="max-width:100%;height:auto;border-radius:8px;margin:24px 0;" loading="lazy">

<!-- 内文图 2（数字拆解章节）-->
<img src="__INNER_IMG_2__" alt="{alt 文本}" style="max-width:100%;height:auto;border-radius:8px;margin:24px 0;" loading="lazy">

<!-- 内文图 3（How-to 章节）-->
<img src="__INNER_IMG_3__" alt="{alt 文本}" style="max-width:100%;height:auto;border-radius:8px;margin:24px 0;" loading="lazy">
```

**🔥 [v5.8] 内文图 prompt 规则**：
- 每张内文图必须与上下文内容直接相关（如讲 groceries 时配超市/厨房场景）
- 内文图尺寸用 `width:100%` 自适应，不固定像素

当前正文 HTML 文件：`C:\Users\59314\claudework\blogger_article.html`

---

### §4.3c 验证  
由 `auto_blogger_images.py` 脚本内部自动完成：无 `images.unsplash.com`、`<img>` 标签数 ≥ 占位符数、存在 `agnes-ai.space` 域名。无需手动检查。

---

## §4.4 生成与发布流程

每次执行 `/blogger-publish` 的完整步骤：

```
Step 1 → 头部交叉研究（§3b）
  ├── 用 WebSearch 查 2-4 个头部博客最新文章
  ├── 提取标题 + 角度 + 数据
  ├── 找交叉点，定独特角度
  └── 选标题公式（§3），定标题

Step 1.5 → **生文前字数预算（硬步骤，禁止跳过）**
  ├── 定 H2/H3 骨架（套 §3c 标准骨架，不边写边改结构）
  ├── 按段落配额算字数：每 H3 90-150 词 + intro/拆解/How-to/结尾，骨架应 ≥1300 词
  ├── 规划每个 H3 和 How-to 段要塞进的数据引用 + 自嘲细节
  └── 目标：首次落笔即 1850-2050 词，避免写完再补写（第 32 篇教训：4 轮扩写全是浪费）

Step 2 → 生成文章正文 HTML（含 hero 图占位符 `__HERO_IMG__`）
  ├── 按 Step 1.5 骨架 + 模板 A（§4）填充·1800-2200 词
  ├── 每段 1-3 句 + 长短句混搭（§0a 规则 1）
  ├── 使用真人过渡词 + 自嘲（§0a 规则 2-3）
  ├── 破坏平行结构，每个 H3 换切入角度（§0a 规则 4）
  ├── 口语化词汇 + contractions（§0a 规则 5）
  ├── 禁止总结句（§0a 规则 6）
  ├── 嵌入 3 条 » 内链
  └── 在第一个 H2 上方嵌入 `<img src="__HERO_IMG__" ...>` 占位

  **→ 字数校验门禁（不可跳过）**：Write 后立即执行 `cat blogger_article.html | sed 's/<[^>]*>//g' | wc -w`
  - **首次即应 ≥2000**（走了 Step 1.5 骨架就该一次到位）；若 <2000，说明骨架没执行或填充不足——在现有段落中扩展细节（数据引用、具体数字、自嘲段），不新建 H3
  - **若 >2500 词**：砍段落数最少的 H3 的前 2 段
  - **若不通过**：修补后重新校验，通过后才进入 Step 2a
  - ⚠️ 禁止在未通过此门禁的情况下进入下一步。此校验不能用"之前测过"或"大概够"替代。

Step 2a → **一键配图脚本：`python scripts/auto_blogger_images.py`**
  ├── 脚本自动检测 HTML 中 `__HERO_IMG__`、`__INNER_IMG_1__` ~ `__INNER_IMG_3__` 占位符
  ├── 从每个 `<img>` 的 `alt` 属性提取场景描述作为 prompt 输入
  ├── 并行调用 Agnes API（4 张并发，非串行）
  ├── 替换全部占位符为真实 URL
  ├── 自动执行质检（无 Unsplash / img 标签数 ≥ 占位符数）
  ├── 503 重试：若脚本显示部分失败（FAIL），对失败图片 `python scripts/auto_blogger_images.py --retry-failed`（重试逻辑已内置于脚本，单图失败不中断其他图）
  └── 写回文件，打印每个 URL
  ⚠️ 脚本路径：`C:\Users\59314\claudework\scripts\auto_blogger_images.py`
  ⚠️ 前置：Step 2 字数门禁必须已通过，HTML 中已有占位符
  ⚠️ 执行前仍须按 §4.3a 规划好每张图的 prompt 并写入 alt 属性

Step 2d → **内容完整性校验**
  ├── 从标题中提取承诺数字：匹配标题中的 `[N] [名词]` 模式（如 "4 Moves" → 4, "6 Cards" → 6）
  │   正则：`/(\d+)\s+(Move|Tip|Way|Card|Question|Lesson|Number|Step|Thing)/i` — 匹配到则取数字
  │   若标题无数字承诺（如 "I Did a July Spending Freeze"），跳过此检查
  ├── 统计正文中 `<h3>` 标签个数
  ├── 若标题数字 > H3 数量，**熔断**：停止执行，必须补足 H3 段落
  └── 若标题含"4 Moves"但正文只有 1-2 个 H3，说明内容严重缺失，禁止进入下一步

Step 3 → 质量门自检（§5 + §0a 规则 1-6）
  ├── §5a 基础质量门
  ├── §5b Anti-AI Voice 专项 7 项检查
  ├── **段落长度分布检查**：evaluate 扫描，4+ 句段落不超过总段落的 10%；超过则拆分最长的段落
  ├── 数据引用段逐句对照 §0a 对照表
  └── **§5a 第 9、10 条硬性阻断**（见下方 §5a）

Step 4 → 执行发布脚本（HTTP server + CORS fetch 注入，不使用 [ref=]/has-text/getByRole）
  ├── 4.0 → 设置标签（在正文注入前或后均可）
  │   └── evaluate: `querySelectorAll('textarea[aria-label]')` 遍历 aria-label 含"标签"/"逗号"/"Label" → 设 value + dispatch input/change
  │       标签固定值：`saving money, personal finance, budgeting, savings goals`
  ├── 4.1 → 正文注入（方案 A）
  ├── 4.2 → 发布三步序列（精确化，无临场发挥空间）
  │   ├── Step A — 点击"发布"按钮：
  │   │   evaluate 遍历 `querySelectorAll('div[role="button"]')`，取 textContent.trim() 含"发布"且不含"时间"且 `!disabled && aria-disabled!=='true'` → click
  │   ├── Step B — 等待并确认对话框：
  │   │   1. browser_wait_for 3s（等待 alertdialog 渲染）
  │   │   2. evaluate 遍历 `querySelectorAll('div[role="button"]')`，取 textContent.trim() === '确认' 且 `offsetParent !== null` → click
  │   │   ⚠️ 对话框按钮是 `<div role="button">`，不是 `<button>`。不可用 `querySelector('button')` 匹配
  │   │   ⚠️ 必须同时检查 `offsetParent` 可见性——页面中可能有两个 textContent==='确认' 的 div（一个可见 + 一个隐藏）
  │   └── Step C — 等待跳转：
  │       browser_wait_for 3s → 检查 URL 是否回到 /blog/posts/ 列表页
  │       若未跳转 → 重试 Step B
  └── Playwright 全自动发布

Step 4a → **正文注入后内容抽样验证**
  ├── 注入 CodeMirror 后，提取 `cm.getValue()` 的前 500 字符和后 500 字符
  ├── 检查前 500 字符是否包含文章第一段的关键标志词（如 "kitchen"、"receipt" 等——每次按实际内容微调）
  ├── 检查后 500 字符是否包含结尾段落标志词
  │   ⚠️ "Drop a comment" 不一定在最后 500 字符（CTA 可能在 "How to Run" 等扩展章节前）。
  │   ✅ 用内链 URL 锚定（`nerdwallet.com` / `thepennyhoarder.com`）
  │   ✅ 次选结尾闭合标签 `</p>` 附近的关键 URL 参数
  ├── 若前后端缺失，视为内容截断，**熔断**：禁止点击发布/更新，必须重新注入
  └── ⚠️ H3 标签数检查不足以发现段落截断（2026-07-08 第 17 篇暴露：H3 全在但 H3 #1 的 4 个段落全部丢失，因 base64 分块边界数据损坏）

Step 5 → 验证发布结果
  ├── 检查博文列表确认状态（URL 含 /blog/posts/）
  ├── **首页浅验证**：导航到博客首页 → 检查最新文章标题出现在 feed 中（⚠️ 不做 `<article>` 内文本和 `<img>` 硬检查——Blogger 首页用 CSS excerpt 摘要加载，无真实 `<img>` 标签，正文内容检查必须走发布页面）
  ├── **字数/H3 硬验证**：导航到发布页面 → `document.querySelectorAll('article p')` 统计正文词数 ≥ 1800 + `article.querySelectorAll('h2, h3')` 数量 ≥ 标题数字。任意一项不通过 → 回退到编辑器修复，不得视为发布完成<br>  **⚠️ 坑：MCP browser_evaluate 中不能用 `split(/\\s+/)` 统计词数**。双反斜杠 `\\s` 经 MCP JSON 序列化被转义为单反斜杠 `\s`（正则含义丢失），导致返回 1。必须用 `split(' ')` 空格分割替代。
  └── **每个 H3 段落内容验证**：验证不仅仅是 H3 标签数量，必须验证每个 H3 后紧接的 `<p>` 段落中是否包含该 H3 独有的关键词（如 `Aldi`、`freezer`、`sales` 等）。例：对于 "Switched Stores" 的 H3，验证 `innerHTML` 中是否包含 `Aldi`。任意一个 H3 的段落内容缺失 → 回退到编辑器修复，不得视为发布完成。
```

## §5 质量门（必须全过）

**§5a — 基础质量门**
- [ ] 标题 60-80 字符，前 40 字符含数字/行动钩子
- [ ] 正文 2000-2500 词（首次落笔应 ≥2000；1800-2000 为不达标需补写；<1800 熔断）
- [ ] 每段 ≤3 句（碎片句不计；详见 §4.1 段落长度规则）
- [ ] 正文中 ≥20 个加粗数字（`<b>$540</b>`、`<b>65%</b>`、`<b>3,000</b>`）
- [ ] 数据有出处（引用 §1 或写明"According to X survey"）
- [ ] 有 2-3 条 `»` 内链
- [ ] 无禁止模式：定义开头（"In today's world"）、AI 过渡词（"Moreover" "Furthermore" "It is important to"）
- [ ] H3 数量 ≥ 标题承诺数字（如标题说"4 Moves"，H3 必须 ≥4 个；不足则熔断，禁止进入 Step 4）
- [ ] 字数门禁不可跳：未在 Step 2 通过 wc -w 校验的词数认定，不得以"已生成时就够了"替代，必须重新校验

**§5b — Anti-AI Voice 专项门（§0a 规则落地检查）**
- [ ] 每 3-4 句有 1 个极短句（≤8 词）—— §0a 规则 1
- [ ] 至少 2 个真人过渡词（honestly, you know, look, the funny thing is, I'll be honest…）—— §0a 规则 2
- [ ] 至少 1 处自嘲/自黑（self-deprecating humor）—— §0a 规则 3
- [ ] 连续 H3 开头句式不同（破坏平行结构）—— §0a 规则 4
- [ ] 全文 ≥5 个 contractions（I'm / I'd / it's / wasn't / didn't）—— §0a 规则 5
- [ ] 无总结句（禁止 "The lesson is" "This taught me" "What I learned"）—— §0a 规则 6
- [ ] 结尾 100 词内无抽象说教（必须是行动挑战 / 评论钩子 / 自嘲）—— §0a 结尾规则

---

## §6 发布脚本（完整可执行）

### 注入方案沿革

| 阶段 | 方案 | 状态 |
|------|------|------|
| v4.8+（当前） | HTTP server + CORS fetch | **主力方案** — 零分块、零数据损坏，19~41篇全部一次注入成功 |
| v3.6~v4.7 | base64 分块注入 | **已废弃** — MCP 工具边界数据损坏问题未根除 |
| v3.0~v3.5 | JSON 内联 / HTTP server 后台 / `[ref=]` 选择器 | **已废弃** — 参数编码冲突/进程隔离拒绝服务/选择器过期

### 编辑器视图确认

2026-06-29 实测确认：**Blogger 编辑器新建和编辑均默认在 HTML 视图（CodeMirror）**，而非 compose 视图（contentEditable iframe）。因此关闭 compose 注入路径，统一走 CodeMirror API。

### 正文注入标准化流程

```
读取 HTML 文件 → page.evaluate(cm.setValue(htmlStr)) → 触发 input/change → 验证发布按钮可用
```

### 正文注入（方案 A：HTTP server + CORS fetch，推荐 — MCP 环境主力方案）

**🔥 v4.8 新增：取代 base64 分块成为主力方案。**

**选择理由**：base64 分块注入（原方案 A）在 MCP 工具边界多次出现数据损坏问题（chunk 边界段落丢失、browser_run_code_unsafe JSON 序列化失败、browser_evaluate 大字符串 JSON 编码冲突）。HTTP server + fetch 一次性传递完整 HTML，无分块、无编码转换、零数据损坏。2026-07-09 第 19 篇实测 13,968 chars 一次注入成功，所有段落完整。

**操作流程**：

```bash
# Step 1 — 启动 CORS 临时 HTTP 服务器
# 🔥 推荐用 Bash(description, run_in_background: true) 而非 "python -c ... &"
# — 后者经后台进程隔离后可能拒绝服务（v3.5 已知问题）
cd "C:\Users\59314\claudework"
python -c "
import http.server
class CORSHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        super().end_headers()
http.server.HTTPServer(('localhost', 8890), CORSHandler).serve_forever()
"
```

```javascript
// Step 2 — 在 Playwright 中 fetch 并注入 CodeMirror
// 通过 page.evaluate 执行，async function 一次性获取 HTML 并写入
const result = await page.evaluate(async () => {
  const resp = await fetch('http://localhost:8890/blogger_article.html');
  const html = await resp.text();

  const cmEl = document.querySelector('.CodeMirror');
  if (!cmEl) return 'No CodeMirror element';
  const cm = cmEl.CodeMirror;
  if (!cm) return 'No CodeMirror instance';

  cm.setValue(html);
  cm.setCursor(cm.lineCount() - 1);

  const ta = document.querySelector('textarea.Fdco1c');
  if (ta) {
    ta.dispatchEvent(new Event('input', {bubbles: true}));
    ta.dispatchEvent(new Event('change', {bubbles: true}));
  }
  return 'OK: ' + cm.getValue().length + ' chars injected';
});
```

**⚠️ 关键约束**：
- **端口必须不被占用**：推荐 8890（已确认可用）。如果冲突换其他端口
- **CORS 头必须加**：`Access-Control-Allow-Origin: *`（不加会被 CORS 阻塞）
- **服务器路径**：必须在 `C:\Users\59314\claudework` 目录启动，因为 `blogger_article.html` 在那里
- **注入后杀掉服务器**：发布完成后用 `taskkill /f /pid <PID>` 杀掉特定进程（PID 从 Bash run_in_background 返回值获取），不要用 `taskkill /f /im python.exe`（会杀掉所有 python 进程）
- **端口冲突处理**：如果 fetch 失败（如端口冲突、CSP 阻挡），更换端口后重试

**验证**：注入后执行 Step 4a 内容抽样验证，抽取 `cm.getValue()` 的前 500 和后 500 字符检查关键标志词。

### ⚠️ 废弃方案（不删除，仅做对照参考）

`[ref=]` 选择器、`getByRole`/`has-text` 定位（Blogger ref 动态过期导致不稳定）、旧版 HTTP server 后台（进程隔离拒绝服务）、Base64 单次注入（JSON 序列化编码冲突）——以上方案已全部废弃。唯一正路为上方方案 A（HTTP server + CORS fetch）。

### 标题输入（唯一方案）

```javascript
// ⚠️ 不依赖 [ref=] — 用 evaluate 直接设 value
// ⚠️ 标题必须内联在函数体内，不能作为函数参数传递
// MCP browser_evaluate 的 function 参数不支持外部参数
await page.evaluate(() => {
  const input = document.querySelector('input[aria-label="标题"]')
  if (!input) throw new Error('标题输入框未找到')
  input.value = 'I Canceled $4,680 in Subscriptions in One Afternoon — What I Actually Missed'
  input.dispatchEvent(new Event('input', { bubbles: true }))
  input.dispatchEvent(new Event('change', { bubbles: true }))
})
```

### "新建博文"按钮点击（唯一方案）

```javascript
// ⚠️ 不依赖 [ref=] — 用 evaluate 遍历 textContent
await page.evaluate(() => {
  const els = document.querySelectorAll('div[role="button"], button')
  for (const el of els) {
    if (el.textContent.includes('新建博文')) {
      el.click()
      return
    }
  }
  throw new Error('新建博文按钮未找到')
})
```

---

## §7 硬阻断

1. Google 登录页出现
2. 连续 2 篇发布失败
3. 编辑器 15s 未加载
4. 发布按钮找不到
5. 正文注入验证失败（CodeMirror 内容 <500 字符）
6. 正文注入后「发布」/「更新」按钮未激活（注入触发失败）
7. 字数 < 2000 词：在任何阶段发现正文词数不足 2000，熔断停止，不得进入「更新」/「发布」操作
8. H3 数量 < 标题承诺数字：标题说"4 Moves"但正文 H3 < 4，熔断，停止执行
9. 修复类操作必须重走全部质量门：如果是对已发布文章的修复（非从头生成），也必须执行 §5 全部自检 + Step 2d 内容完整性校验，禁止"这是修复不用检查字数/H3"
10. Step 4a 内容抽样验证不通过：注入后检查前后端关键标志词发现内容截断——熔断，禁止点击发布/更新，必须重新注入
11. 发布后逐 H3 段落验证不通过：任意 H3 的专属关键词在文章 `innerHTML` 中缺失（如 "Switched Stores" H3 无 "Aldi"、"Freezer" H3 无 "freezer" 等）——熔断，回退编辑器修复
12. 标题前 40 字符不含数字或行动动词：标题前 40 字符必须含数字（如 "6 Cards", "$285"）或行动动词（如 "Reviewed", "Canceled", "Built"）。不含则熔断，重新选题/改写标题

### 段落丢失修复 SOP

如果 Step 5 验证发现某些 H3 的段落内容在发布后被截断（H3 标题在但下面 `<p>` 段落丢失）：

1. **立即回编辑器**：导航到 `https://www.blogger.com/blog/post/edit/{blogID}/{postID}`（URL 可从发布页面的博文列表获得）
2. **从本地 HTML 文件重新注入**：`cat blogger_article.html` 确认本地文件包含完整内容
3. 按 §6 方案 A（HTTP server + CORS fetch）重新注入
4. **执行 Step 4a 内容抽样验证**：验证前后端关键文本完整
5. **点击「更新」按钮**（非「发布」— 因为是已发布文章的修复）
6. **重新执行 Step 5 所有验证**含逐 H3 段落内容验证

---

## §8 选择器速查（v3.6 — 全部统一为 page.evaluate 方案）

⚠️ **不要用 `[ref=]` / `getByRole` / `has-text`** — 这些在 Blogger 页面重渲染后不稳定。
全部按钮和输入交互统一走 `page.evaluate` + `textContent`/`aria-label` 遍历匹配。

| 元素 | 选择器 | 注意点 |
|------|--------|--------|
| "新建博文"按钮 | `querySelectorAll('div[role="button"], button')` 遍历 textContent 含"新建博文" | 是 `<div role="button">`，非 `<button>`。含图标字符，不依赖 getByRole |
| 标题输入 | `input[aria-label="标题"]` | 获取后 `.value = title` + `dispatchEvent(new Event('input'))` |
| 正文注入 | 启动 CORS HTTP server（localhost:8890）→ `fetch()` 获取 HTML → `cm.setValue(html)` | 🔥 零分块零数据损坏；❌ 注入后立即做 Step 4a 内容抽样验证 |
| "发布"/"更新"按钮 | `querySelectorAll('button, div[role="button"]')` 遍历 textContent 含"发布"/"更新" | 都是 `<div role="button">`。`disabled` 属性检查 + `aria-disabled` 检查。无 disabled 时 textContent 含图标字符。必须排除"发布时间"（`!txt.includes('时间')`）|
| 标签输入 | `querySelectorAll('textarea[aria-label]')` 遍历 aria-label 含"标签"/"逗号"/"Label" | 是 `<textarea>`，非 `<input>`。设置 `value` + dispatch input/change |
| 确认对话框按钮 | evaluate 遍历 `querySelectorAll('div[role="button"]')`，取 textContent.trim() === '确认' 且 `offsetParent !== null` → click | 🔥 对话框按钮是 `<div role="button">`，不是 `<button>`。querySelectorAll('button') 无法匹配。<br>⚠️ 必须检查 `offsetParent`（可见性），页面中可能有两个 textContent===`确认` 的 div（对话框内一个可见 + 页面底部一个隐藏）。用 `browser_wait_for 3s` 等待 dialog 渲染再操作。 |
| 硬验证文章 | 发布页面 `article` 或 `.post-body`，检查 textContent > 500 + img 存在 | ⚠️ 不在博客首页做硬验证——Blogger 首页用 CSS excerpt 摘要，无真实 `<img>` 标签。必须导航到单篇发布页面做全文验证 |

---

## §9 版本历史（仅保留最近3版，v3.0~v6.2 已归档，git log 可查）

| 版本 | 日期 | 变更 |
|------|------|------|
| **v6.5** | 2026-07-22 | **第 42 篇发布（Grocery Budget 选题）**。1,700 词→扩写到 2,022 过字数门禁。4 图全部 Agnes 生成。HTTP server + CORS fetch 13,848 chars 一次注入成功。发布后逐 H3 段落验证通过。博文计数 42 篇。|
| **v6.4** | 2026-07-22 | **第 41 篇发布（Midyear Savings Goals 选题）+ 技能减法审计**。响应用户反馈：按五律全面减法——砍版本历史（35→3版）砍废弃注入方案表（4行→1句）砍§4.3时序B边缘路径砍§0a重复的标题优化长度控制删§4.3执行流程框解决§5a平均句长与§0a抗AI规则的矛盾清理§4.4流程中所有版本标记噪音压缩§6已知Bug表（6行→3行）。删除约 500 行死代码/冗余。博文计数更新为 41 篇。 |
| **v6.3** | 2026-07-21 | **第 40 篇发布（Side Hustle 真实时薪实验）+ 技能减法大修**。结尾三选一→固定评论钩子；标题公式表 4+2→6 合一；§4.1 切入角度固定轮换顺序；§4.4 砍最弱→砍段数最少；新增发布三步序列（点击→等待→确认→跳转）。博文计数 40 篇。|
| **v6.2** | 2026-07-20 | **第 39 篇发布（3 Budgeting Methods 实验选题）**。NerdWallet/Penny Hoarder/Financial Samurai 三源引用。HTTP server + CORS fetch 14,996 chars 一次注入。段落分布 9.3% 通过。博文计数 39 篇。|

> **复盘按 CLAUDE.md 技能修复标准流程执行**
