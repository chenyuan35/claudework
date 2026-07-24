---
name: bluesky
description: "Bluesky 发布技能 — 南美生活 @mnin74.bsky.social"
---

# /bluesky 技能

## PHASE 0：硬性去重（熔断级，不可跳过，必须先执行）

**执行时机**：每次启动本技能、写任何内容之前。必须先到个人主页提取所有已发布帖子内容。

### 步骤

1. 导航到个人主页（能看到已发布帖子的页面）
2. evaluate 提取所有可见帖子正文到数组用于比对：
```
evaluate：
  const postTexts = []
  const links = document.querySelectorAll('[role="link"]')
  links.forEach(link => {
    const anchors = link.querySelectorAll('a')
    const hasProfile = Array.from(anchors).some(a => {
      const href = a.getAttribute('href') || ''
      return href.startsWith('/profile/') && href.includes('@')
    })
    if (!hasProfile) return
    const text = link.textContent.trim()
    if (text.length > 20) postTexts.push(text)
  })
  return [...new Set(postTexts)]
```
3. 比对规则：
   - 待发布内容与 posts[] 中任一元素完全匹配 → **熔断，不发布，报告"已发布过相同内容"**
   - 待发布内容与 posts[] 中某元素高度重叠（同一主题/同一链接）→ **熔断**
4. 熔断后终止流程，不写任何新内容

### 铁律
- 每次启动技能必须先执行此事。不做就去写内容 = 流程违规。
- 不依赖记忆或历史记录——必须实时从页面提取。

---

## 永久规则

### 工具约束
本技能所有浏览器操作**只允许**使用 `mcp__playwright__*` 系列 MCP 工具。

**禁止（违反 = 用户暴怒，永久删除）：**
- ❌ playwright CLI（`npx playwright`, 独立浏览器进程）
- ❌ Puppeteer / Selenium
- ❌ 非 Playwright MCP 的浏览器自动化
- ❌ `fill()`、直接改 DOM innerHTML 注入

**允许工具（按可靠性排序）：**
| 场景 | 工具 | 备注 |
|------|------|------|
| 打开页面 | `mcp__playwright__browser_navigate` | |
| 读取页面 | `mcp__playwright__browser_snapshot` | 含完整 DOM |
| 点交互按钮 | `mcp__playwright__browser_evaluate` + JS | 比 `_click` 可靠（ref 会在页面切换后失效） |
| 键盘输入 | `mcp__playwright__browser_evaluate` + 原生 value setter | 用于编辑框 |
| 单键操作 | `mcp__playwright__browser_press_key` | Tab/Escape/Enter |

### 账号信息
- **Handle:** @mnin74.bsky.social
- **显示名:** Mini
- **Bio:** 南美 | AI/Tech | 每天一点新发现
- **密码/登录:** 用户浏览器已存凭据，不询问
- **Chrome 配置:** `C:\Users\59314` 默认用户，bluesky.app 已登录
- **对标已关注:** Kevin @musclelog.ca, 昨天 @yesterdaynews

### 发布红线
- 单次 run 只发 **1 条帖子**
- 每日上限：按 `§4 运营节奏` 中的**当前阶段**动态套用（养号期 1 条、跑通期 1 条、稳定期 1-2 条）
- 每次间隔 ≥ **2 小时**
- 禁止商业推广（除非用户明确下令）
- **阶段判定依据（双标准）：** ① 按周数：第1周养号、第2周跑通、第3周+稳定；② 按原创帖数（不含回复）：<5 养号、5-20 跑通、>20 稳定。个人主页显示的"帖文"数包含回复，不可直接用于阶段判定。以周数为准、帖数为辅。

---

## §0 账号定位与内容规则

### 定位：南美生活信息源

**差异化：中文互联网里，最真实的南美生活一手信息。**

用户画像：
- 对南美/拉美感兴趣的中文读者（想了解、想去、想移）
- 海外华人、数字游民、背包客
- 想看不同生活方式的人

### 内容原则：每一篇都值得被搜到

**铁律：不发碎碎念。每篇帖子发出去三个月后还能被人搜到、读到、转发，才算合格。**

判断标准：
- 这条帖子一年后还有人会搜吗？→ 不会 = 不发
- 有人搜"厄瓜多尔""基多""南美"时能找到这条吗？→ 不能 = 不发
- 读完能带走一个具体认知吗？→ 不能 = 不发

**长青内容类型：**
| 类型 | 举例 | 搜索价值 |
|------|------|---------|
| 生活成本/实用信息 | 基多租房多少钱、菜市场物价 | 高，持续有人搜 |
| 文化差异观察 | 南美人为什么迟到、砍价文化 | 高，常青话题 |
| 具体办事指南 | 签证、银行、手机卡、交通 | 极高，刚需搜索 |
| 中国人常见误解 | "南美很危险""不安全"等认知纠正 | 高，好奇心驱动 |
| 有共鸣的生活片段 | 能引起"我也是"或"好想去"的真实细节 | 中高，转发驱动 |

**禁止：**
- 纯感慨型（"今天好热"）
- 自我报告型（"我运营了10个平台"）
- 时效性新闻（除非有独特南美视角）
- 任何读完就忘的内容

### 说话方式（避免 AI 味）
- **个人视角开头**：不要「大家都知道」「今天我们来聊聊」→ 要「今天发现一个事」「我试了下」
- **短句不工整**：不要三段式（观点+论据+结论）→ 就一句话一个观察
- **口语化**：用「试过」「翻车了」「同感」「发现一个事」→ 不用「值得深思」「从另一个维度」
- **有态度**：不是新闻搬运，要有自己的判断

---

## §1 主流程（一次 run）— 严格门控管道

```
GATE A (§1.1): 可发布？→ 否 → 仅学习+互动 → 结束
                → 是 → GATE B
GATE B (§1.2+1.3): 学习+互动完成 → GATE C
GATE C (§1.4): 创作+人性化检查通过 → 发布
GATE D (§7): 验收 → 复盘
```

> ⚠️ **铁则：每个 GATE 的检查项必须逐条验证，跳过任一检查 = SOP 违约。**

### §1.1 GATE A — 触发前检查（硬性）

```
STEP 1: 登录确认
  navigate → bsky.app → snapshot
  检查左下角"切换账户"按钮是否显示 @mnin74.bsky.social
  [  ] 已登录 → 继续
  [  ] 未登录 → 报用户 → 熔断

STEP 2: 今日已发条数检测
  navigate → /profile/mnin74.bsky.social
  evaluate（精确匹配，v8 - 2026-07-12 修复跨午夜误报）：
    const now = new Date()
    const todayStr = `${now.getFullYear()}年${now.getMonth() + 1}月${now.getDate()}日`
    // 计算昨天日期，用于跨午夜边界消歧
    const yesterday = new Date(now)
    yesterday.setDate(yesterday.getDate() - 1)
    const yesterdayStr = `${yesterday.getFullYear()}年${yesterday.getMonth() + 1}月${yesterday.getDate()}日`

    const links = Array.from(document.querySelectorAll('[role="link"]'))
    const todayPosts = links.filter(link => {
      // 收集该帖文容器内所有 <a> 的 aria-label（含绝对日期）
      const anchors = link.querySelectorAll('a')
      const ariaLabels = []
      for (const a of anchors) {
        const aria = a.getAttribute('aria-label') || ''
        ariaLabels.push(aria)
        if (aria.includes(todayStr)) return true  // 绝对日期匹配 → 今日帖
      }
      // 无绝对日期匹配，再检查相对时间
      for (const a of anchors) {
        const txt = a.textContent.trim()
        if (txt === '现在') return true            // 刚刚发布（Bluesky 特有的"现在"）
        if (/分钟前$/.test(txt)) return true        // 1小时内 → 肯定是今天
        if (/小时前$/.test(txt)) {
          // 跨午夜边界：如果该帖的 aria-label 含昨天日期，排除
          const hasYesterdayDate = ariaLabels.some(aria => aria.includes(yesterdayStr))
          if (hasYesterdayDate) return false
          return true  // 无昨天证据 → 算今天
        }
      }
      return false
    }).length
  → 返回今日帖文数（含回复）
  > ⚠️ v7 旧逻辑中仅用「小时前」匹配会导致跨午夜误报（如 11日 14:14 帖在 12日 02:57 显示"20 小时前"）。v8 修复：先收集该帖容器内所有 aria-label 的绝对日期，匹配到「小时前」时如果存在昨天日期则排除。
  > ⚠️ 跨时区风险（v9 - 2026-07-16）：`new Date()` 使用浏览器系统时区（通常 UTC+8），若系统时区与用户所在时区（Ecuador UTC-5）不一致，todayStr 可能偏移 ±1 天。好在 Bluesky 页面用相对时间显示（「现在」「分钟前」「小时前」），这些由服务器端时间计算，不受系统时区影响。绝对日期匹配（aria-label 中的"2026年X月X日"）也由 Bluesky 本地化渲染，与浏览器 locale 一致而非 UTC。因此时区偏差不影响判断结果。如果未来改动导致误报，优先改用页面中可见的「N 天前」/「昨天」等相对时间做判定。

STEP 3: 阶段判定
  当前日期: new Date()  // 时区偏移不影响周数计算（跨时区最多偏差1天不会改变周数）
  首帖日期: 2026-07-03
  第几周: Math.ceil((当前日期 - 首帖日期) / 7)  // 第1周=养号、第2周=跑通、第3周+=稳定
  原创帖数: 个人主页总帖数 - 目测回复量（粗略，以周数为准）
  
STEP 4: 门控决策
  [  ] 距上次 < 2h → 不可发布 → 跳 §1.2（仅学习+互动）→ 结束
  [  ] 今日已达日限 → 不可发布 → 跳 §1.2（仅学习+互动）→ 结束
  [  ] 可发布 → 继续执行完整流程
```

### §1.2 学习环节

切换 Following feed 看对标号最新内容：
```
navigate → https://bsky.app（首页，默认 Discover）

切换到 Following 标签（坐标 v2 - 2026-07-05 验证）：
  evaluate：
    const divs = document.querySelectorAll('div')
    for(const d of divs) {
      if(d.textContent.trim() === 'Following' && d.getAttribute('aria-label') === 'Following' && d.offsetParent !== null) {
        d.click()
        break
      }
    }

snapshot → 阅读最新帖子，记录：
  - Kevin @musclelog.ca 的配图和文案风格
  - 昨天 @yesterdaynews 的标题写法（如果当日未发帖可能不出现）
  - 地雷魚 @jiraygyo 的技术观点表达
  > 如果对标号当日未发帖不在 feed 中，跳过该对标号，继续阅读 feed 中实际可见的其他内容。
  > 不从历史记录中找对标号的旧帖——学习环节只看当前动态。

> ⚠️ 如果 feed 内容过多导致 snapshot > 100KB 无法直接阅读，改用 evaluate 提取关键帖文信息：
>   ```
>   evaluate：
>     const posts = document.querySelectorAll('[role="link"]')
>     const results = []
>     posts.forEach(p => {
>       const links = p.querySelectorAll('a')
>       let handles = []
>       links.forEach(a => {
>         const href = a.getAttribute('href') || ''
>         if (href.startsWith('/profile/') && href.split('/').length === 3)
>           handles.push(href.replace('/profile/', ''))
>       })
>       results.push({ handles: [...new Set(handles)], preview: p.textContent.substring(0, 200) })
>     })
>     return results.filter(r => r.handles.length > 0).slice(0, 15)
>   ```
```
> 注意：Following feed 除了已关注用户外，也可能包含算法推荐内容。如果某个对标号当天未发帖，不会出现在 feed 中。

浏览 Discover feed 看当天热点趋势（点「Discover」标签，坐标同上改 text 为 "Discover"）。如果推荐内容太单一（如全是日系/动漫），滚屏加载更多内容发现多样化帖子及用户：`window.scrollBy(0, 800)`，等待 1s 后用 evaluate 提取帖文列表。

### §1.3 互动环节

从 Following feed 和 Discover feed 选内容互动：

**点赞 3-6 条：**
- 选有意思的帖文点赞（不限于对标号）
- 坐标见 §2.1

**回复 2-4 条：**
- 选自己能写出有意思回复的帖文（不勉强，没好内容回宁缺毋滥）
- **回复对象分散约束：同一轮互动中，回复不能集中到同一个人。至少覆盖 2 个不同用户。如果 Following feed 里只有地雷魚发了可回内容，切换到 Discover feed 找其他用户回。**
- 回复风格：
  - 不端不装，像朋友之间接话
  - 有梗/幽默/吐槽优先——看到好笑的就笑，看到离谱的就吐槽
  - 可以分享个人相关经历接话茬
  - 日语/繁体帖用对方语言风格回
  - 英文帖用英文回，口语化
- **短！** 10-30 字最佳，一句话说一个点。Bluesky 不适合长回复，写长了对回复对象也不礼貌。
- **禁止：** 通用话术（"好帖""说得好""同意""学到了"）、三段式结构、AI 感
- 对标号的母语帖优先回，但不要全回同一个对标号
- 坐标见 §2.2

**关注 0-1 个新账号：**
- 互动中遇到有趣的人 → 查看其 profile → 值得就关注
- 坐标见 §2.3

### §1.4 GATE C — 创作发布（硬性配方）

> ⚠️ **发布前必须走完以下配方，跳过任何一步 = SOP 违约。**

```
STEP 0: 内容模式审计（2026-07-17 统一修复新增，不可跳过）
  navigate → /profile/mnin74.bsky.social
  evaluate：取最近 5 条帖文，检查：
    [  ] 开头句式：是否 ≥3 条以相同句式开头？
    [  ] 结构骨架：是否 ≥3 条使用相同结构（实用信息/差异观察/生活片段）？
    [  ] 话题域：是否 ≥3 条属于同一话题？
  任一项命中 → 本次选题必须避开被命中的维度，不能继续选同类话题
  ── 通过 → 进入 STEP 1**

```
STEP 1: 选定选题（三选一，按优先级）
  [  ] 实用信息 → 生活成本、办事指南、具体地址/价格/流程
  [  ] 文化差异观察 → 南美人怎么做事、跟中国有什么不同、为什么
  [  ]（以上都不适合才选）有共鸣的生活片段 → 但必须有具体细节，不是纯感慨
  → 选定后，问自己：这篇一年后还有人搜吗？→ 不会 → 返回重选

STEP 2: 写草稿（铁序）
    2a. 开头 = 个人场景一句话（「我试过」「踩过这个坑」「实测发现」）
    2b. 正文 = 可执行信息（具体方法/对比/数据/步骤）
    2c. 态度 = 自己判断（「我选了方案B，因为…」），不中立搬运
    2d. 收尾 = 不强制，但可留钩子（「下次说怎么解决」）
    2e. 标签 = 按 §4 标签策略打 2-3 个精准标签
  字数：不硬限制，但一条不能 >300 字

STEP 3: 人性化检查清单（硬性通过/不通过）
  ⬜ 开头是个人视角？（「我试过」✓ / 「大家都知道」✗）
  ⬜ 没有三段式结构？（观点→论据→结论结构 ✗）
  ⬜ 口语化？（「翻车了」✓ / 「值得深思」✗）
  ⬜ 有态度，不是新闻搬运？（有自己判断 ✓）
  ⬜ 没有 AI 常用句式？
    ✗「从另一个维度来看」
    ✗「在当今这个…的时代」
    ✗「值得注意的是」
    ✗「我们需要思考的是」
    ✗「综上所述」
  ⬜ 读一遍像人写的？（像朋友聊天 ✓ / 像公众号文章 ✗）
  → 任一 ✗ → **禁止发布，重写草稿再检**
  → 全部 ✓ → 进入 §3 发布操作

### §1.5 人性化铁律（覆盖所有输出：帖文、回复、互动）

以下规则不可协商，违反一条 = 整次操作终止：

1. **禁用句式（看见就删）：**「在当今这个数字时代」「随着AI技术的不断发展」「值得注意的是」「从某种角度来看」「综上所述」「值得我们深思」
2. **禁用结构：** 三段式（观点→论据→结论）、总分总、引言+论证+升华
3. **开头必须多样化（2026-07-17 统一修复）：** ▸ 最近 3 条帖文如果都用同一类开头（如全部「我试过」或全部「今天发现」），本条必须换不同类型。参考样式（轮换使用，不重复）：
   - 数据/事实式：「Bluesky 上搜 Ecuador 的结果…」
   - 场景切片式：「在基多街头等公交时发现…」
   - 观点断言式：「南美最被低估的生活技能是…」
   - 反问钩子式：「你知道厄瓜多尔用什么App买菜吗？」
   - 日常切口式：「今天在菜市场被坑了5刀。」
   ▸ **连续 3 条不得以同一句式开头**，写完后检查个人主页最近 3 条确认
4. **字数上限：** 单条回复 ≤30 字。单条帖文 ≤300 字。超了停。
5. **自然呼吸：** 写完后读一遍。读着像「文章」而不是「说话」→ 删了重写。
6. **零AI感：** 如果有人看到会说「这是AI写的吗」→ 删了重写。

> 例外规则：英文/日语帖不必完全遵守句式禁用，但结构和字数限制仍然适用。

---

## §2 互动操作坐标

### §2.1 点赞

在一篇帖文上点「喜欢」：
```
坐标：帖文底部按钮栏「喜欢（N 次喜欢）」button，文字在 aria-label 而非 textContent（v2 - 2026-07-05）
evaluate（在当前可见范围内点赞 3-6 条）：
  const likeBtns = Array.from(document.querySelectorAll('button'))
    .filter(b => {
      const label = b.getAttribute('aria-label') || ''
      return label.includes('喜欢') && !b.disabled && b.offsetParent !== null
    })
  const pick = likeBtns.sort(() => Math.random() - 0.5).slice(0, Math.min(5, likeBtns.length))
  pick.forEach((b, i) => { setTimeout(() => b.click(), i * 600) })
  return `已点赞 ${pick.length} 条`
```
注意：已经点过的「喜欢」按钮会变成实心状态且再次点击会取消。执行前不重复点。

### §2.2 回复

在一篇帖文上点「回复」：
```
坐标：帖文底部「回复（N 则回复）」button，文字在 aria-label（v2 - 2026-07-05）
evaluate — 从 feed 中找到目标帖文后点其回复按钮：
  // 先用显示名找（feed 中显示的是显示名而非 handle），找不到再换 handle
  const links = document.querySelectorAll('[role="link"]')
  for(const link of links) {
    const txt = link.textContent
    if((txt.includes('目标显示名') || txt.includes('目标用户handle')) && txt.includes('目标关键词')) {
      const replyBtn = link.querySelector('button[aria-label*="回复"]')
      if(replyBtn) { replyBtn.click(); break }
    }
  }
  > 优先匹配显示名（如「醒醒吧你沒有天友」），因其在 feed 中直接可见；handle 做第二匹配条件。
```

**回复流程（一次一条）：**
1. 从 feed 中找到目标帖文 → 点其「回复」按钮（会打开回复编辑器）
2. ⚠️ **回复短而精：** Bluesky 是短内容平台，回复不要写长段落。一句话最好，10-30 字足够，说一个点就收。长回复显得不熟/不给面子。
3. **回复区域：** 点回复按钮后编辑器在 dialog 中，直接在 dialog 中回复即可。
4. 等待回复编辑器出现（`.ProseMirror` 在 dialog 中，最多等 2s）
5. 写入回复内容（短！）
6. 点「发布」按钮（同 §3.2 回复发布坐标）
7. **验证：** 发布后回复 dialog 关闭即表示成功 → 处理下一条。不需要验证回复计数+1（feed 中可能不立即更新）。

```
回复编辑器写入坐标（同 §3.1 编辑器方案，使用 DOM 创建 `<p>`）：
  // 等待编辑器出现（可能延迟）
  const editor = document.querySelector('.ProseMirror')
  if(!editor) { await new Promise(r => setTimeout(r, 2000)); /* 再次查找 */ }
  editor.focus()
  editor.innerHTML = ''
  const p = document.createElement('p')
  p.textContent = '回复文本'
  editor.appendChild(p)
```

### §2.3 关注

**场景 A：在 feed 中发现想关注的用户（直接在当前 feed 中操作）**
```
evaluate（在 feed 中关注当前看到的用户）：
  const followBtn = Array.from(document.querySelectorAll('button'))
    .find(b => b.textContent.trim() === '关注' && b.offsetParent !== null)
  if(followBtn) {
    followBtn.click()
    return '已关注'
  }
  return '无可关注按钮'
```

**场景 B：查看用户 profile 后关注（已进入该用户个人资料页）**
```
evaluate：
  const btn = Array.from(document.querySelectorAll('button'))
    .find(b => b.textContent.trim() === '关注' && b.offsetParent !== null)
  if(btn) { btn.click(); return '已关注' }
```

---

## §3 发布操作坐标（精确）

### §3.1 打开发布框与写入内容

```
browser_navigate → https://bsky.app（首页 Discover feed）
```

等待页面加载后，打开发布框。**只使用以下唯一定位方案：**

```
坐标：左侧导航栏底部「新帖文」按钮

第一顺位：左侧导航栏底部「新帖文」按钮（含 img + 文字"新帖文"）
evaluate：
  document.querySelectorAll('button').forEach(b => {
    if(b.textContent.trim() === '新帖文' && b.offsetParent !== null) b.click()
  })

备用（首顺位失效时）：页面顶部居中「发生了什么新鲜事？」按钮（同一功能入口）
evaluate：
  Array.from(document.querySelectorAll('button')).find(b =>
    b.textContent.trim().includes('新鲜事')
  )?.click()
```

> 注意「发生了什么新鲜事？」按钮 publish 后不会关闭发布框，需要手动关 dialog；而「新帖文」按钮会正确开关发布 dialog。因此首顺位指向「新帖文」。

**写入正文（含换行）（v2 - 2026-07-05）：**
由于 browser_evaluate 的 JS 字符串嵌套导致 `\n` 被双转义，**只使用** DOM 创建 `<p>` 元素的方案插入换行：
```
evaluate：
  const e = document.querySelector('.ProseMirror')
  e.focus()
  e.innerHTML = ''
  const p1 = document.createElement('p')
  p1.textContent = '第一段文字'
  const p2 = document.createElement('p')
  p2.textContent = '第二段文字'
  const p3 = document.createElement('p')
  p3.textContent = '#标签1 #标签2'
  e.appendChild(p1)
  e.appendChild(p2)
  e.appendChild(p3)
```

> 单段文本同样用此方案（创建一个 `<p>` 即可）。不再使用 `execCommand('insertText')` 方法。

### §3.2 发布

写入内容后，发布按钮变为可用：

```
坐标：dialog 内「发布帖文」button（aria-label="发布帖文"）（v2 - 2026-07-05）
evaluate 方案：
  const btns = Array.from(document.querySelectorAll('button'))
  for(const b of btns) {
    const label = b.getAttribute('aria-label') || ''
    if(label === '发布帖文' && !b.disabled && b.offsetParent !== null) {
      b.click()
      break
    }
  }
```

**回复发布**（回复编辑器中的发布按钮）：
```
坐标：回复 dialog 内「发布回复」button（aria-label="发布回复"，v5 - 2026-07-08 验证）
evaluate：
  const btns = Array.from(document.querySelectorAll('button'))
  for(const b of btns) {
    if(b.getAttribute('aria-label') === '发布回复' && !b.disabled && b.offsetParent !== null) {
      b.click(); break
    }
  }
```

**验证：** 发布后编辑器关闭，页面停留在原 feed。跳转个人资料页确认帖文：
```
browser_evaluate: window.location.href = '/profile/mnin74.bsky.social'
browser_snapshot → 确认新帖文出现在列表
evaluate → 确认个人资料页 header 中帖文计数增加 // 帖文计数位于 profile header 区域，非左下角
```

---

## §4 运营节奏

### 核心原则
**宁可不发，不发废帖。一篇长青帖顶十篇碎碎念。**

### 养号期（第1周）
- 每天 1 条，全部是长青内容
- 先积累 7 篇高质量帖子，建立账号调性
- 每条带 2-3 个精准标签（被搜索到的关键）
- **目标：** 个人主页点进去，每篇都值得读

### 跑通期（第2周）
- 每天 1 条，保持长青标准
- 观察哪类内容被转发最多（搜索 + Feed 推送）
- 回复评论，带动互动权重

### 稳定期（3周+）
- 质量优先，不追求数量
- 深挖高转发话题方向，做系列化内容
- 可考虑创建自定义 Feed 聚合同类内容

### 标签策略
- 每帖带 2-3 个标签，贴近内容本身
- 南美相关：`#南美生活` `#厄瓜多尔` `#拉美`
- 不用泛标签（`#日常` `#生活`）
- 参考对标号的标签密度：Kevin 每帖 5-7 个标签

---

## §5 记忆与状态

每次执行完毕，通过个人主页自我验证状态：
- 今日已发帖: 使用 §1.1 精确方案检查
- 总帖数: 个人资料页显示的帖文数量（**含回复**，不能直接用于阶段判定）
- 当前阶段: 按周数判定（§1 发布红线）

---

## §6 故障恢复

| 故障 | 处理 |
|------|------|
| 发布按钮灰色 | 内容超出 300 字 → 截断重试；或编辑器为空 → 检查文本是否写入成功 |
| 登录失效 | 报用户：Bluesky 登录过期，请重新登录 |
| 发布后帖文不可见 | 刷新页面重试确认；二次失败报用户 |
| 找不到编辑器（.ProseMirror） | 发布框可能未打开 → 重新点击「新帖文」|
| 点赞按钮点不了 | 可能在 dialog 遮挡下 → 先关闭 dialog 再试；或 textContent 无"喜欢"→ 改为 aria-label 匹配 |
| 回复后无反馈 | 回复按钮点击后等待 2s 检查编辑器是否弹出；若未弹出重试 |
| 回复对话框被 feed 滚动带跑 | feed 中嵌入的回复 dialog 可能随滚动偏移 → 改用 navigate 到该帖文独立页（/profile/{user}/post/{id}）再回复 |
| 关注按钮找不到 | feed 中可能没有「关注」按钮 → 跳过关注步骤 |
| 帖子发布时间检查 | 读个人主页帖文列表确认今日帖文 |
| 今日帖文检查误报 | v7 旧逻辑用「小时前」匹配跨午夜边界误判（如 11日 14:14 帖在 12日 02:57 被算为今日帖）。v8 修复：匹配「小时前」时交叉检查该帖 aria-label 绝对日期，含昨天日期则排除。|
| 编辑器换行不生效 | `\n` 被双转义 → 改用 createElement('p') + appendChild 插入分段 |
| 发布按钮不在 textContent | Bluesky 按钮文字在 aria-label → 用 `b.getAttribute('aria-label')` 匹配 |
| 回复发布按钮 label 不同 | 回复 dialog 的发布按钮 aria-label 是"发布回复"不是"发布帖文" → 用 `'发布回复'` 匹配（v5 - 2026-07-08 验证） |
| 回复目标用户在 feed 中用 handle 找不到 | feed 中显示的是显示名而非 handle → 优先用 txt.includes('显示名') 找，找不到再换 handle |
| 年龄验证通知遮挡 | Discover/Following feed 顶部可能出现"你所在地的相关法律要求需要验证你已成年"横条 →
  不影响操作，但 snapshot 内容中会混入该通知文本，阅读时注意忽略 |
| 连续两次失败 | 熔断，报用户 |

---

## §7 执行后自动验收

每次执行完发布/互动后，跳转个人主页自动完成以下验收（非手动清单）：

```
browser_evaluate: window.location.href = '/profile/mnin74.bsky.social'
```

**硬性验收项（缺一不可）：**

1. **帖文是否成功发布：** snapshot 检查最新帖文是否是刚发布的（内容匹配 + 时间戳为"现在"或当天日期）。
2. **帖文计数自增：** 比较执行前后的帖文数变化。如果发了新帖，计数应增加 1-2（1 帖 + 可能的回复）。
3. **今日点赞数：** 互动时已用 evaluate 确认点赞数量，无需单独验证。
4. **阶段判定：** 按周数判定当前阶段（首帖 2026-07-03），更新 §4 的阶段心态。

> **复盘按 CLAUDE.md 技能修复标准流程执行**
