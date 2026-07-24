---
name: blogger-publish
description: Blogger「WealthWiseDaily」全自动发布。单管道 v7.1 — 审计减法。8步固定路径，固定5 H3，去重融合。
---

# Blogger · WealthWiseDaily · 全自动发布 v7.0

**触发**：`/blogger-publish` 或「发一篇 WealthWiseDaily」

## 博客信息

| 字段 | 值 |
|------|-----|
| 博客名 | WealthWiseDaily / https://aineedhelpfromotherai.blogspot.com |
| 后台 | https://www.blogger.com/blog/posts/2611555253226715248 |
| Google 账号 | chenyuan19920509@gmail.com（已登录）|
| 博主资料名 | SmartMoneyMoves |
| 定位 | 个人理财 · 省钱攻略 · 英文，2,000-2,500 词 |
| 目标受众 | Gen Z / Millennials，美式中产焦虑 |
| 当前博文 | 46 篇（最新: 2026-07-24 第46篇） |

---

## §0 主管道（唯一执行顺序）

**本技能是具备硬阻断条件的全自动执行流程。任何确认式停顿都视为偏移。**

```
Phase 0 → Step 1 → Step 2 → Step 2a → Step 2d → Step 3 → Step 4 → Step 5
```

四条熔断线贯穿全程：字数<2,000（Step 2）、H3<5（Step 2d）、注入偏差>5%两次仍失败（Step 4）、发布后逐H3段落验证失败（Step 5）。任一条触发即停止，回退修复。

---

### Phase 0：硬性去重

**输入**：Blogger 后台列表页 URL
**动作**：`evaluate` querySelectorAll(`[role="listitem"]`) 提取所有已发布标题，按 `\n` 分割后取第一行（长度 10-200 字符）
**验证**：待发布标题不在 titles[] 中，且无关键词高度重叠
**失败**：匹配到任一重复 → **熔断**，不写新内容
**恢复点**：无（熔断即终止）

**铁律**：每次启动必须执行，不依赖记忆或历史记录。

---

### Step 1：头部交叉研究

**输入**：无
**动作**：用 Exa 搜索 NerdWallet + The Penny Hoarder 最新文章，提取标题/角度/数据 → 找交叉点 → 确定选题角度 → 选标题公式（从 §1a 6 种中轮换，最近2篇禁用）
**验证**：角度与最近2篇主题不同
**失败**：交叉点与最近2篇重复 → 重新深翻页面，不将就
**恢复点**：Step 1 入口

**独创约束**：NerdWallet 用数据 → 你用 personal experiment。Penny Hoarder 用列表 → 你用故事串联。从不直接抄结构。

**可引用数据源**：
- NerdWallet: 夏季旅行平均 $3,940；89% 旅行者省钱；45% 想减少非必要支出；$30-80/mo 订阅浪费
- Penny Hoarder 2026 Financial Anxiety Barometer: 65% 最大焦虑源为生活必需品；48% 只存剩的钱
- 通用：应急基金目标 $500-$1,000 / 3-6个月；HYSA 当前 APY 约 3.5-4.5%

---
### Step 2：生成文章正文 HTML

**输入**：§2 骨架 + 标题
**动作**：按 §1b 去 AI 味规则填充。每段 1-3 句 + 长短句混搭 + 真人过渡词（≥2）+ 自嘲（≥1）+ 平行结构破坏 + contractions（≥5）+ 无总结句。嵌入 3 条 » 内链 + `<img src="__HERO_IMG__">` 占位。每个 H3 按固定顺序换切入角度（情感→数字→对话→场景→反直觉）
**验证**：`wc -w` ≥ 2,000（Write 后立即执行，<2,000 进入失败分支）
**失败**：<2,000 → 在现有段落扩细节后重新验证
**恢复点**：Step 2 入口，重写后再次 `wc -w`

---

### Step 2a：生成图片

**输入**：HTML 含 `__HERO_IMG__` / `__INNER_IMG_1__` ~ `__INNER_IMG_4__` 占位符，alt 属性已写好 prompt
**动作**：`python scripts/auto_blogger_images.py`（自动检测占位符 → 从 alt 取 prompt → 并行调 Agnes API → 替换 URL → 质检无 Unsplash → 写回）
**验证**：5 张图全部成功（URL 含 `agnes-ai.space`），无占位符残留
**失败**：部分失败 → 重新运行 `python scripts/auto_blogger_images.py`（脚本容错，单图失败不中断其他图；重跑会用 alt 文本重新生成本轮失败图；若 Agnes 503 持续，传入 `--prompts "hero text|inner1 text|inner2 text|inner3 text"` 跳过 alt 提取环节）
**恢复点**：重新运行脚本

**Prompt 规则（三步合一，不拆三段）**：
1. **视觉风格轮换**：从下表选对应选题的行，禁止连续2篇用同一风格

| 选题类型 | 视觉风格关键词 |
|----------|--------------|
| 订阅/账单审计 | flat lay, overhead shot |
| 个人实验/省钱故事 | environmental portrait, natural light |
| 省钱技巧清单 | warm minimal, cozy corner |
| 投资/财务分析 | clean professional, crisp |
| 购物/消费反思 | close-up, textured |
| 副业/收入 | 创意俯拍 |

2. **Prompt 组装**：`①场景, ②视觉风格, ④元素, ③光线, ⑤禁止`，≤80 词。场景每篇随机（厨房→阳台→地铁站→街角咖啡桌，人和环境至少换两个）。调色跟随风格（不固定暖调）
3. **欧美视觉调性**：欧美面孔、自然皮肤纹理、Brooklyn/London 环境、自然光优先

---

### Step 2d：内容完整性校验

**输入**：正文 HTML
**动作**：统计 `<h3>` 数量
**验证**：H3 数量 ≥ 5
**失败**：不足 → **熔断**，补足 5 个 H3 段落后重新校验
**恢复点**：Step 2 入口

---

### Step 3：质量门自检

**输入**：正文 HTML
**动作**：逐项自检 §1a 标题公式要求（含数字、60-80字符、连续2篇不同）+ §1b 规则 1-7（极短句≥1/每3-4句、过渡词≥2、自嘲≥1、H3开头句式不同、contractions≥5、无总结句、结尾无抽象说教）
**验证**：每项标记 ✅/❌，全部 ✅ 才能进入 Step 4
**失败**：任一项 ❌ → 修复后重新自检
**恢复点**：Step 2 入口

---

### Step 4：注入与发布

**输入**：`blogger_article.html` 完整 HTML
**动作序列**：
1. 启动 CORS HTTP 服务器（localhost:8890）→ Bash background
2. **新建博文**：evaluate `querySelectorAll('div[role="button"]')` 遍历 textContent 含"新建博文"→ click
3. **标题**：evaluate `querySelector('input[aria-label="标题"]')` → `.value = 标题` + dispatch input
4. **标签**：evaluate `querySelectorAll('textarea[aria-label]')` 遍历含"标签/逗号/Label" → `.value = 'saving money, personal finance, budgeting, savings goals'` + dispatch
5. **正文注入**：evaluate async → fetch(`http://localhost:8890/blogger_article.html`) → `cm.setValue(html)` → dispatch input/change
6. **发布**：evaluate 遍历 `div[role="button"]` → textContent 含"发布"且非"时间"且 !disabled → click
7. **确认对话框**：browser_wait_for("确认") → evaluate 遍历 `div[role="button"]` → textContent==='确认' 且 offsetParent!==null → click
8. **等待跳转**：browser_wait_for 3s → URL 回到 /blog/posts/

**验证**：URL 含 /blog/posts/
**失败**：未跳转 → 重试 Step 7。注入偏差 >5% → 自动重新 inject（最多2次），仍截断则报告异常停在编辑器
**恢复点**：Step 4 入口（未跳转）/ Step 4 入口（注入截断）

### Step 5：验证发布结果

**输入**：发布页 URL
**动作序列**：
1. **首页浅验证**：导航到博客首页 → 最新文章标题出现在 feed 中
2. **发布页硬验证**：导航到发布文章页 → `article.querySelectorAll('p').textContent.split(' ').length` ≥ 1,800 + `article.querySelectorAll('h2, h3').length` ≥ 5 + `article.querySelectorAll('img').length` ≥ 4
3. **逐 H3 关键词验证**：每个 H3 的专属关键词在 article.innerHTML 中存在（如 "Convenience Store" → "convenience"、"App Store" → "Google Play"、"Quick Dinner" → "frozen pizza" 等）

**验证**：以上全部通过
**失败**：任一项不通过 → 回编辑器（`/blog/post/edit/{blogID}/{postID}`）→ 重新注入（Step 4 #5）→ 点击"更新"→ 重跑 Step 5 全部验证（含逐 H3 关键词）
**恢复点**：Step 5 入口

---

## §1 写作规则

### §1a 标题公式

| 公式 | 模板 | 示例 |
|------|------|------|
| Question + Hook | `[Question]? Plus [Angle]` | "Is an Annual or Monthly Subscription Better?" |
| Number + Action | `[N] Ways to [Goal]` | "9 Ways to Cut Your Monthly Bills" |
| Mistake + Cost | `[N] Mistakes Costing You $X` | "7 Subscription Mistakes Costing $3,200" |
| Experiment | `I [Action] for [Time]` | "I Tracked Every Dollar for 30 Days" |
| 数据冲击 | `$[N] [Thing] I Found When I [Action]` | "$2,400 in Waste I Found When I Opened My Bank Statement" |
| 反直觉 | `What [Common Thing] Actually Costs You $X` | "What Your 'Small' Daily Coffee Actually Costs You $1,825" |

**检查**：标题必须含至少一个数字（金额或数量均可）/ 60-80 字符 / 个人角度或问句 / 1 个情感钩子。不含数字则熔断。**连续 2 篇禁止使用同一公式。**

### §1b 去 AI 味（写作时逐条对照）

| # | 规则 | 强制 |
|---|------|------|
| 1 | **长短句混搭**：每 3-4 句插 1 个极短句（3-8 词）| ✅ |
| 2 | **真人过渡词**：≥2 处（Honestly / Look / You know / I'll be honest / Long story short）| ✅ |
| 3 | **自嘲**：≥1 处 self-deprecating humor | ✅ |
| 4 | **破坏平行结构**：连续 H3 开头句式不同（情感→数字→对话→场景→反直觉轮换）| ✅ |
| 5 | **口语化词汇 + Contractions**：≥5 个（I'm / it's / wasn't / didn't / that's）| ✅ |
| 6 | **禁止总结句**：不出现 "The lesson is" / "This taught me" / "What I learned" / "In conclusion" / "The problem with X isn't Y" / "The pattern is universal" / "But here's the thing" / 双重情感并列表述 | ✅ |
| 7 | **结尾无抽象说教**：最后 100 词必须是行动挑战或评论钩子。固定格式 `<p><b>Drop a comment:</b> What [topic] have you tried? I'd love to compare notes.</p>` | ✅ |

**检测方法**（写完全文后执行，不边写边修）：
- 扫描全文找 6 类禁止句式
- 某段找不到更好替代 → 删段换完全不同的话说
- 某段只有 1-2 处但其他 OK → 改该句即可，不必整段重写

---

## §2 字数与骨架

### 骨架（2,000-2,500 词，固定 5 H3）

```
块           段数  累计
Intro         7段    7
5 × H3       30段   37    每 H3=6 段（变切入角度）
数字拆解      5段   42
How-to        6段   48
结尾+内链     3段   51
```

H3 标题必须包含 5 个分类数字（如"5 Categories"），与 Step 2d 的 h3≥5 一致。

### 段落长度规则

- 每段 1-3 句。≥4 句则在第 3 句后硬断为新 `<p>`，不合并为长句
- 碎片句（≤8 词）不计入 3 句限额——它们本质是同句语气停顿
- 同一段内多个碎片句用 em dash `—` 或逗号合并为单句，不各自独立
- 每 3-4 句插入 1 个极短句（3-8 词）
- 整段只有 1 句可以——如果那句是强力定论或自嘲

**段落分布检查（可选）**：`python -c "import re; html=open('blogger_article.html').read(); ps=re.findall(r'<p>(.*?)</p>', html, re.DOTALL); over=sum(1 for p in ps if len([s for s in re.split(r'[.!?]+',p) if len(s.split())>8])>3); print(f'超限: {over}/{len(ps)} ({over/len(ps)*100:.1f}%')"`，允许 <10%。

### 排版

- 数字/金额用 `<b>$540</b>`（不用 `<strong>`）
- 引语段落内用双引号，不用 `<blockquote>`
- 偶尔用 `<i>`，全文不超过 5 处
- 对比 3+ 项才用 `<ul>/<li>`
- 内链前带 `»`：`<p>» <a href="...">Read more: ...</a></p>`，每篇 3-5 条
- 不额外加 `<br>`、不空行

---

## §3 注入与发布技术细节

### HTTP 服务器启动

```bash
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

端口 8890 已确认可用。冲突时换端口。注入后 `taskkill /f /pid <PID>` 杀掉（PID 从 Bash background 返回获取，不要 `taskkill /f /im python.exe`）。
------

## §4 选择器速查

⚠️ **不用 `[ref=]` / `getByRole` / `has-text`** — 全部 `page.evaluate` + textContent/aria-label 遍历。

| 元素 | 选择器 | 注意点 |
|------|--------|--------|
| "新建博文" | `querySelectorAll('div[role="button"]')` 遍历 textContent 含"新建博文" | `<div role="button">` |
| 标题 | `input[aria-label="标题"]` | `.value = title` + dispatch input |
| 正文注入 | fetch(localhost:8890/blogger_article.html) → `cm.setValue(html)` | 注入后验证 cm.getValue().length |
| 标签 | `textarea[aria-label]` 遍历含"标签/逗号/Label" | value = 'saving money, personal finance, budgeting, savings goals' |
| "发布"/"更新" | `div[role="button"]` 遍历 textContent 含"发布/更新"且不含"时间"且 !disabled | 排除 textContent 含"时间" |
| 确认对话框 | `div[role="button"]` 遍历 textContent==='确认' 且 offsetParent !== null | 非 `<button>`。可能有隐藏同名元素 |
| 发布页验证 | `article` 元素 | 不在首页做硬验证 |
