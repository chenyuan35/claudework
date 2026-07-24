---
name: threads
description: "Threads 发布技能 — 自动发帖到 @minonoig（热点评论/观点输出号）"
---

# /threads 技能

## PHASE 0：硬性去重（熔断级，不可跳过，必须先执行）

**执行时机**：每次启动本技能、写任何内容之前。必须先到个人主页提取所有已发布帖子内容。

### 🔴 铁律（执行前必读）

- 以下所有含 `browser_evaluate` 提取的步骤，**禁止用 Read snapshot 文件手动摘取代替**。必须跑 evaluate 拿到数组再分析。
- 每次 evaluate 提取后必须检查返回数组 `length > 0`。若为 0 说明选择器失效，调整后重跑，**不得降级为肉眼读文件**。
- "提取到 posts[]" 与 "用 posts[] 做比对" 是两件独立的事。必须先提取、再比对，不能一步做完。

### 步骤

1. 导航到个人主页（能看到已发布帖子的页面）
2. **`browser_evaluate` 提取所有可见帖子正文到数组 `posts[]`：**
   ```javascript
   // browser_evaluate — 返回清洗后的帖子文本数组 posts[]
   () => {
     const posts = [];
     const postLinks = document.querySelectorAll('a[href*="/@minonoig/post/"]');
     for (const link of postLinks) {
       // 向上遍历 8 层到帖子容器
       let container = link;
       for (let i = 0; i < 8 && container; i++) {
         container = container.parentElement;
       }
       if (!container) continue;
       // 清洗：去掉 "minonoig"、时间戳、"赞N"、"分享N" 噪音
       // 时间戳涵盖："1 天前""2天前""几秒前""N分钟前""约 1 小时前""N小时前"
       let text = container.textContent.trim();
       text = text.replace(/minonoig/g, '').trim();
       text = text.replace(/\d+\s*天前|几秒前|约?\s*\d+\s*(分|小?)钟?前/g, '').trim();
       text = text.replace(/赞\s*[\d,.]+\s*万?|赞\s*\d+/g, '').trim();
       text = text.replace(/(分享|回复|转发)\s*[\d,.]+\s*万?|(分享|回复|转发)\s*\d+/g, '').trim();
       if (text.length > 30) posts.push(text);
     }
     return posts;
   }
   ```
   **验证：** 看返回数组 `length`。若为 0 → 选择器失效 → 先用 snapshot 确认 DOM 结构，修正后重跑。**不得直接拿 snapshot 原文凑合。**

   **💡 有 `posts[]` 在手，后续 Step 6.5（内容模式去重）和 Step 3.5（健康度审计）都直接引用这个数组，不再重复提取。**

3. 比对规则：
   - 待发布内容与 posts[] 中任一元素完全匹配 → **熔断，不发布，报告"已发布过相同内容"**
   - 待发布内容与 posts[] 中某元素高度重叠（同一主题/同一链接）→ **熔断**
4. 熔断后终止流程，不写任何新内容

### 铁律
- 每次启动技能必须先执行此事。不做就去写内容 = 流程违规。
- 不依赖记忆或历史记录——必须实时从页面提取。

---

## 🔴🔴🔴 最高优先级：只允许 Playwright Extension (mcp__playwright__*)

本技能所有浏览器操作**只允许**使用 `mcp__playwright__*` 系列 MCP 工具。

**绝对禁止（违反 = 用户暴怒，永久删除）：**
- ❌ playwright CLI（`npx playwright`, 独立浏览器进程）
- ❌ Puppeteer / Selenium / 任何其他浏览器自动化工具
- ❌ `fill()`、直接改 DOM、innerHTML 注入（contenteditable 用 keyboard.type；配图走 MCP `browser_file_upload`，硬约束见 §4）

**启动即视为已连接（遵守全局 CLAUDE.md 规则2「不预检、不确认、不绕路」）：** `mcp__playwright__*` 为永久配置、默认已连。**直接像其他 MCP（exa / tavily / memory 等）一样调用，不做存在性预检、不设硬停、不报告"疑似未连"。** 仅当真实调用时返回连接错误才简短报告（且绝不退回任何独立/分身浏览器）。

---

## 账号信息

- **Handle:** @minonoig
- **显示名:** Mini
- **首页:** https://www.threads.com/@minonoig
- **密码/登录:** 用户浏览器已存凭据，不询问

## 赛道定位

**热点评论 / 观点输出号**

基于 Threads 繁中版生态研究（2026-07-03 采样）：
- 最火内容：一句话共鸣吐槽（6,611👍）、热点评论（2,760👍）、消费吐槽（3,572👍）
- 英文内容在繁中生态几乎没热度（3👍）
- 中文为主（繁中/简体都可）

**2026-07-15 实测验证：** 同一推荐流中，中文共鸣帖 2.3 万赞 vs 英文励志帖最高 1,769 赞。英文内容在繁中版推荐流的热度差距巨大，延续 2026-07-03 结论。

**人设：** 像朋友随手甩一个观点。不是写专栏，不是卖课。

---

## §0 端到端执行路径（完整坐标清单，按顺序）

**一次 run 必须按以下 Step 1→2→3→3.5→4→4.5→5→6→6.5→7→8→9 顺序执行，每步完成再进下一步。**

### Step 1：导航到个人主页
```
browser_navigate → https://www.threads.com/@minonoig
```
等待 3 秒。

### Step 2：确认登录状态
取 snapshot，检查：
- 页面存在「@minonoig」标题
- 左侧底部「主页」链接存在
- ❌ 如果页面是登录弹窗 → 报用户重新登录

### Step 3：频率检查

SESSION_STATE.md 已弃用（2026-07-05）。频率直接通过个人主页已有帖子判断：

```
browser_snapshot → 查看个人主页已有帖子
```

- **今天已发 ≥3 条** → 终止发布，本次只做学习不发
- **今天已有帖子（"几秒前""N 分钟前"）且距上次发布 <2 小时** → 终止发布，本次只做学习不发

**判断方法：** 用 `browser_evaluate` 自动化检查今日是否发过帖，不靠肉眼读 snapshot：
```javascript
// browser_evaluate — 检查个人主页是否有今日帖子（"几秒前""分钟前""小时前"）
() => {
  const timeLinks = document.querySelectorAll('a[href*="/@minonoig/post/"]');
  for (const link of timeLinks) {
    const text = link.textContent.trim();
    if (text.includes('几秒前') || text.includes('分钟前') || text.includes('小时前')) return { postedToday: true, timeText: text };
  }
  return { postedToday: false };
}
```
**返回 `postedToday: true`** → 今天已发过，还需判断距上次是否 <2 小时（若只有"小时前"标签，提取数字判断）。  
**返回 `postedToday: false`** → 今天未发，频率检查通过。

### Step 3.5：内容健康度审计（必须执行）

**执行时机：** 频率检查通过后、选题决策之前。不跳过、不省略。

**步骤：**
1. 取 PHASE 0 已提取的 `posts[]` 最近 8 条。用这些文本（不是 snapshot 肉眼分析）检查以下 **5 个维度**：

| # | 维度 | 检查问题 | 阈值 |
|---|------|---------|------|
| 1 | **开头句式** | 最近 5 帖是否 ≥3 条以相同句式开头？ | ≥3 → 模式化 |
| 2 | **结构骨架** | 最近 5 帖是否 ≥3 条使用相同结构？（数据观察三段式 / 对比法 / 纯观点 / 故事流） | ≥3 → 模式化 |
| 3 | **话题簇** | 最近 5 帖是否 ≥3 条属于同一话题域？（平台规律 / 职场 / 消费吐槽 / 情感共鸣） | ≥3 → 区域过密 |
| 4 | **口吻姿态** | 最近 5 帖是否 ≥3 条以相同姿态说话？（分析总结 / 吐槽抱怨 / 分享感悟 / 反问读者） | ≥3 → 口吻同调 |
| 5 | **视觉节奏** | 最近 5 帖是否长度接近（都在 250-300 字之间）或结构段落数相同？ | ≥4 → 视觉单调 |

2. 任一项命中阈值，**必须强制改**——不是"尽量改"，是 Step 5 选题时避开该维度。

3. 审计结果写入当前 session 笔记，供 Step 5 选题和 Step 6 创作时对照。

**铁律：**
- 这是熔断级检查，不是参考信息。命中阈值不调整就写新内容 = 流程违规。
- 维度判定要严格（实事求是，不要替自己找理由"不算模式化"）。
- Step 8.3（每次 run 末）复盘时回头看审计结果的预测是否准确。

**示例：** 今天执行时如果跑了这个审计：
- 开头句式：5/5 以"刷"开头 → ❌ 模式化
- 结构骨架：4/5 是"数据观察→总结规律"三段式 → ❌ 模式化
- 话题簇：3/5 是"Threads 平台规律" → ❌ 区域过密
- 三项命中，Step 5 必须选非平台观察类话题 + 非"刷"开头 + 非三段式结构

### Step 4：学习环节（浏览推荐流）

```
browser_navigate → https://www.threads.com/（首页推荐流）
```
等待 4–5 秒（推荐流异步加载，直接取 snapshot 会得到"正在加载..."）。
取 snapshot。如果仍大量"正在加载..."，再等 2–3 秒重取。
逐个阅读帖子，记录：
- 帖子文本、点赞数（"赞 X"格式）、评论数
- 识别赞数 >1000 的帖子 = 当前热点
- 识别推荐流中相互矛盾/可对比的帖子对（如"批奏折帖高赞 vs AI剧帖讨论热度"），用于生成非共识观察
- 记录热点话题的关键词和出现次数

**点赞数解析：** Threads 显示格式为「赞 2,760」「赞 3.1 万」，需解析为数字对比。
**注意：** snapshot 中点赞数在 `button "赞 N"` 的文本里。

### Step 4.5：互动（点赞+评论，推荐执行）

**目的：** 养号期算法看社区参与度。推荐流刚刷完，趁热互动——谁出现在推荐流里就点谁，不用挑人。社区互动优先级不低于发帖。

**步骤：**

1. **点赞 1-2 篇** — 从当前推荐流里随手点（注：赞按钮为 `div[role="button"]`，非 `<button>` 元素）：
   ```javascript
   // browser_evaluate — 点赞推荐流里第一篇可见的他人帖子
   // 首次运行 target=1，再跑改 target=2
   // Threads 点赞按钮 DOM 结构：<div role="button"> 文本以"赞"开头（如"赞15"）
   // ❌ 不要用 button 标签或 img[alt="赞"]，它们不在实际 DOM 中
   (target = 1) => {
     const roleBtns = document.querySelectorAll('[role="button"]');
     let idx = 0;
     for (const btn of roleBtns) {
       const text = btn.textContent?.trim() || '';
       if (!text.startsWith('赞') || text === '赞') continue;
       // 跳过自己的帖子
       let parent = btn.parentElement;
       for (let i = 0; i < 10 && parent; i++) {
         if (parent.textContent?.includes('minonoig')) break;
         parent = parent.parentElement;
       }
       if (parent && parent.textContent?.includes('minonoig')) continue;
       idx++;
       if (idx === target) { btn.click(); return 'Liked'; }
     }
     return 'No unlike post found';
   }
   ```

2. **评论 1-2 篇**（有想法就写，没有不强求）— 打开推荐流里的某条帖子，写一句像朋友聊天的话就行，不用想太多。
   ```javascript
   // browser_run_code_unsafe — 点回复图标 → 打字 → 发送
   async (page) => {
     // 找到推荐流里第一条他人帖子的回复按钮
     const replyBtns = page.getByRole('button').filter({ hasText: /回复\s/ });
     const count = await replyBtns.count();
     for (let i = 0; i < count; i++) {
       const btn = replyBtns.nth(i);
       const text = await btn.textContent().catch(() => '');
       if (text.includes('minonoig') || text === '') continue;
       await btn.click();
       break;
     }
     await new Promise(r => setTimeout(r, 1500));
     const textbox = page.getByRole('textbox');
     await textbox.click();
     await page.keyboard.type('你这条太真实了 我上次也遇到', { delay: 5 });
     await new Promise(r => setTimeout(r, 500));
     const sendBtn = page.getByRole('button', { name: /发送|发布/ }).last();
     await sendBtn.click();
   }
   ```
   把 `type()` 里的文字换成你实际想说的，像兄弟聊天一样自然就行。

**铁律：** 社区互动是养号期的优先动作。今天如果选了不发帖只互动，也算一次有效 run。

### Step 5：选题决策（具体SOP）

**话题筛选标准（按优先级）：**

| 优先级 | 话题类型 | 判断依据 | 示例 | 数据参考 |
|--------|---------|---------|------|---------|
| 1 | 独特视角/反常识观察 | 自己有一个非共识的观点，能一句话说清 | "vibe coding不是取代程序员而是消灭了找人那堵墙" | 🏆 **1天 → 1,000+浏览/15赞/3回复**（0粉丝号实测） |
| 2 | 热点事件/争议 | 推荐流出现 ≥2 条相似话题且合计赞数 >3000 | 茉莉奶白×LV | ⚠️ 仅2赞/2天（新号在小热点上难出头） |
| 3 | 消费/品牌吐槽 | 单一帖子 >2000 赞的社会现象 | 中国移动话费 | 尚待验证 |
| 4 | 情感/职场共鸣 | 评论率高（回复/赞 >3%）的帖子 | 求职、生日帖 | 尚待验证 |
| 5 | 日常反常识 | 用自己生活中的小观察 | 任何 | 尚待验证 |

**2026-07-06 实测结论：** 养号期的 Threads 算法更倾向推荐"独特观点/非共识观察"类内容，而非跟随已有热点。**选题时优先选"自己真有话要说"的角度。**

**确定话题后，找到具体切入点：**
- 避免泛泛而谈 "这事很过分"
- 找到一个具体角度：品牌观/制度/执行层/文化心理
- 一句话先写出核心观点

**开头句式的硬约束（熔断级，违反即重写）：**
1. 不以"刷了/刷到/刷了半天/刷完"开头
2. 整体开头前 8 字不与 posts[] 最近 3 篇 >60% 句式重叠（Step 6.5 会检查）
3. posts[] 最近 3 篇中 ≥2 篇使用了对比法结构（"一条帖说A...另一条说B..."），则当前帖子禁止对比法

**推荐流无热点时的处理方案：**
- 收集点赞 TOP 3 帖子的共同情绪关键词
- 用这个情绪 + 自己的生活观察写一条"情绪共鸣帖"
- 格式：「[一个具体场景]，[一个反常识的观察]」

**选不出话题时的硬性 fallback（熔断级）：**
读完整条推荐流后仍无法确定选题 → 强制走日常反常识（优先级 5）：
- 体裁：一个具体的生活观察/小故事（不是总结规律）
- 开头前 8 字必须是一个名词短语（如"家里绿萝""小区保安""楼下咖啡店"）
- 不允许以"刷""发现""最近"开头
- 如果连这个也写不出来 → **终止本次 run，只做互动不发帖**

### Step 6：创作帖子内容

**反AI味创作规则（强制执行）：**

| ❌ 禁止（AI味） | ✅ 要（人话） |
|----------------|-------------|
| "值得深思""值得关注""在我看来" | 直接说结论 |
| 三段式：爆论+论据+结论 | 可以只给故事不给结论 |
| "在这个信息爆炸的时代" | 开头第一句进主题 |
| bullet points 列因素/维度 | 用口语：「第一个...」「第二个...」 |
| "综上所述""总而言之" | 说完就停 |
| 成语堆砌、排比句 | 用口头词：「试过」「翻车了」「说白了」 |

**字数：** 500 字符以内。写完数 `text.length`，超过 490 就截断重写。
**自检：** 写完读一遍，问自己"这是人说话吗？"

### Step 6.5：内容模式 + 开头自检（熔断级，不可跳过）

**执行时机：** 写完帖子后、发布前。基于 PHASE 0 提取的 `posts[]`。

**步骤：**

0. **自动化检查：开头前 8 字去重（熔断级）** — 从 textbox 提取当前帖子文本，与 posts[] 最近 3 条比对开头前 8 字：
   ```javascript
   // browser_evaluate — 检查当前帖子开头前8字是否与最近3篇 >60% 重叠
   () => {
     // 从 textbox 提取当前帖子正文
     const textbox = document.querySelector('div[role="textbox"]') ||
                     document.querySelector('[contenteditable="true"]');
     if (!textbox) return { pass: false, reason: 'textbox not found' };
     const draftText = textbox.textContent.trim();
     const first8 = draftText.slice(0, 8);
     if (first8.length < 2) return { pass: false, reason: 'content too short' };

     // 重新提取 posts[] 用于比对
     const posts = [];
     const postLinks = document.querySelectorAll('a[href*="/@minonoig/post/"]');
     for (const link of postLinks) {
       let container = link;
       for (let i = 0; i < 8 && container; i++) container = container.parentElement;
       if (!container) continue;
       let text = container.textContent.trim();
       text = text.replace(/minonoig/g, '').trim();
       text = text.replace(/\d+\s*天前|几秒前|约?\s*\d+\s*(分|小?)钟?前/g, '').trim();
       text = text.replace(/赞\s*[\d,.]+\s*万?|赞\s*\d+/g, '').trim();
       text = text.replace(/(回复|转发|分享)\s*[\d,.]+\s*万?/g, '').trim();
       if (text.length > 30) posts.push(text);
     }
     if (posts.length < 1) return { pass: true, reason: 'only 1 post, skip comparison' };

     // 检查 #0/#1：开头前8字重叠
     const recent3 = posts.slice(0, 3);
     const bannedPatterns = /^(刷了|刷到|刷了半天|刷完)/;
     if (bannedPatterns.test(first8)) {
       return { pass: false, reason: `开头"${first8}"以"刷"开头，违反硬约束` };
     }
     for (const p of recent3) {
       const pStart = p.slice(0, 8);
       let overlap = 0;
       for (let i = 0; i < Math.min(first8.length, pStart.length); i++) {
         if (first8[i] === pStart[i]) overlap++;
       }
       if (overlap / Math.max(first8.length, 1) > 0.6) {
         return { pass: false, reason: `开头"${first8}"与已有帖"${pStart}"重叠率 ${Math.round(overlap/first8.length*100)}% > 60%` };
       }
     }
     return { pass: true, reason: `开头"${first8}"无冲突`, posts };
   }
   ```
   **返回处理：** `pass: false` → 熔断，重写开头再回来。`pass: true` → 继续，`posts` 用于后续检查。

1. 用上一步返回的 `posts` 数组（若上一步没返回则重新提取一次），取最近 5 条，检查每个的开头前 8 字
2. ≥3 条以相同句式开头（"刷了/刷到/刷了半天"等模式）→ **当前帖子不能以该句式开头**
3. ≥3 条使用相同结构（数据观察三段式 / 对比法 / 纯观点 / 故事流）→ **当前帖子结构不得与此重叠**
4. 任一项命中即熔断：重写开头或结构后再发布

### Step 7：发布帖子

#### 7.1 打开发布框

**主路径（个人主页）：**
```javascript
// browser_run_code_unsafe 内执行
// ⚠️ 必须用 browser_run_code_unsafe，不可用 browser_click 工具直接定位！
// button name="文本栏为空白。请输入内容，撰写新帖子。"
// 该文本含中文标点和空格，browser_click 的 target 解析会报 CSS 选择器错误
// 坐标：profile 内嵌 textbox 的「有什么新鲜事吗？」按钮
const composeBtn = page.getByRole('button', { name: /文本栏为空白/ });
await composeBtn.click();
await page.waitForTimeout(1500);
```

**若主路径未打开发布框**（snapshot 中 textbox 不可见）→ **切备用路径（首页导航）：**
```javascript
// 坐标：左侧导航「新建串文」button
// 注意会被 __fb-light-mode div 遮挡，必须 force
const newPostBtn = page.getByRole('button', { name: '新建串文' });
await newPostBtn.click({ force: true });
await page.waitForTimeout(1500);
```

#### 7.2 写入正文（关键：换行失效 → 必须 type 逐行）
```javascript
// ⚠️ Threads 编辑器是 contenteditable div，不是 textarea！
// textbox.fill() 的 \n 会丢失成空格
// 正确方式：keyboard.type() + Enter
const textbox = page.getByRole('textbox', { name: /文本栏为空白/ });
await textbox.click();
await page.waitForTimeout(300);
const lines = text.split('\n');
for (let i = 0; i < lines.length; i++) {
  if (i > 0) {
    await page.keyboard.press('Enter');
    await page.waitForTimeout(50);
  }
  await page.keyboard.type(lines[i], { delay: 5 });
}
await page.waitForTimeout(500);
```

#### 7.2.5 配图上传（可用能力）

**能力说明：** Threads 支持上传图片到帖子。以下为操作流程——当帖子有现成配图时使用，不想配图直接跳过到 7.3。

**正确路径 = MCP 自带 `browser_file_upload` 工具，不可用 run_code 手调 setFiles（那才是 Not allowed 的死路，硬约束见 §4）。**

**操作流程（两步必须紧接，点附件会立即弹 File chooser 模态）：**

步骤 A — 用 `browser_run_code_unsafe` 点击附件入口，触发 Modal：
```javascript
// 坐标：button name="附加影音内容"
const attach = page.getByRole('button', { name: '附加影音内容' });
await attach.click();
await page.waitForTimeout(1200);
// 点击后弹出 File chooser 模态，系统提示 "can be handled by browser_file_upload"
```

步骤 B — 紧接着（同一 run 内，不嵌在 run_code 里）调用 MCP 工具 `browser_file_upload`：
```
browser_file_upload → paths: ["C:\\绝对路径\\图片.jpg"]   // Windows 反斜杠；可传多张
// 传完后发布框内出现「移除」+「附件操作」按钮 = 图片已进入草稿预览
```

**坐标：**
- 附件入口按钮：`button name="附加影音内容"`
- 图已入草稿标记：dialog 内出现 `button "移除"` 与 `button "附件操作"`

**注意：**
- 仅图片路径已实测验证；视频入口同名但**未实测，禁止**本次使用。
- 上传后若想取消：点「取消」→ 弹「存为草稿？」→ 点「不保存」丢弃。
- 配图帖同样受 §1 频率红线约束（每次 run 只发 1 条）。

#### 7.3 发布
```javascript
// 坐标：dialog 底部的「发布」button（有多个"发布"button，取最后一个）
const publishBtn = page.getByRole('button', { name: '发布' }).last();
await publishBtn.click({ timeout: 5000 });
await page.waitForTimeout(3000);
```

### Step 8：验证 + 状态更新

#### 8.1 验证发布成功
```
browser_snapshot → 检查"新建串文"dialog 是否关闭
  ✅ 关闭 → 发布成功
  ❌ 未关闭 + 发布按钮可见 → 进入 8.2 失败处理

browser_navigate → https://www.threads.com/@minonoig
browser_snapshot → 检查「串文」tab 下第一帖
  ✅ 内容匹配 → 成功
  ❌ 不匹配 → 检查是否未发出或内容被修改
```

#### 8.2 失败处理
| 现象 | 原因 | 处理 |
|------|------|------|
| dialog 还在，发布按钮可见 | 空内容或超字数 | 截断到 490 字符重发 |
| 页面错误提示 | 提交报错 | 点「取消」关 dialog，报告用户 |
| 异常未知 | 未知 | 点「取消」关 dialog，关标签页重开 |

**取消 dialog：** 找 `button "取消"` 并 click，或按 Escape（无模态时可用）。

#### 8.3 状态记录 + 交付检查

> **复盘按 CLAUDE.md 技能修复标准流程执行**

**✅ Step 8 完成标记：** 发布成功已确认。本次 run 核心流程结束。如有余力回 Step 4.5 补点赞/评论。

#### 8.5 24 小时回看——运营数据闭环（非强制，但推荐执行）

浏览量是否 >100？浏览/赞比是否合理？之前对选题的判断被验证了还是被否了？→ **以数据反向修正 Step 5 选题优先级表**

### Step 9：互动收尾（可选）

发布完了如果还有余力，回到推荐流再按 Step 4.5 补 1-2 个点赞或评论。不影响发布流程，走到这算整轮 run 完成。

## §1 发布红线

- 单次 run 只发 **1 条帖子**
- 每日 ≤ **3 条**（新号频率太高触发风控）
- 每次间隔 ≥ **2 小时**
- Threads 支持最多 **500 字符**
- 禁止商业推广（除非用户明确下令）
- 配图可用：走 MCP `browser_file_upload`（流程见 §0 Step 7.2.5，硬约束见 §4）

## §2 运营节奏

### 养号期（第1周）
- 每天 1 条帖（文字为主；配图帖可替代，仍算 1 条，走 §0 Step 7.2.5）
- 观察推荐流，熟悉平台内容调性
- **目标：** 被推荐算法收录

### 跑通期（第2周）
- 每天 1-2 条，找高互动话题
- 推荐流浏览后执行 Step 4.5（点赞/评论别人帖子）

### 稳定期（3周+）
- 固定每天 1-2 条
- 定型内容风格

## §3 故障恢复

| 故障 | 处理 |
|------|------|
| 发布按钮灰色 | 内容超出 500 字符 → 截断重写 |
| 登录失效 | 报用户：Threads 登录过期，请重新登录 |
| 找不到编辑器 | 发布框未打开 → 重新点击「有什么新鲜事吗？」按钮 |
| 文件上传报错（Not allowed） | 你走了 run_code 手调 setFiles 的死路 → 改用 §0 Step 7.2.5 的 MCP `browser_file_upload` |
| fileChooser 模态意外卡住 | 仅手调 setFiles 才会卡；正常点附件交 MCP 不卡。若真卡：关标签页重开（browser_tabs close → navigate） |
| 连续两次失败 | 熔断，报用户 |
| getRole('发布') 匹配多个 | 用 .last() |

## §4 已知限制（硬约束）

1. **配图上传可行** — 用 MCP 自带 `browser_file_upload`（流程见 §0 Step 7.2.5）。**硬约束：禁止在 `browser_run_code_unsafe` 里手调 `fileChooser.setFiles()`**（那条路径才报 Not allowed，配图死路唯一来源）。
2. **CSS 选择器不可靠** — Threads 是 Meta React 应用，DOM 动态变化，只用 locator
3. **contenteditable 换行** — 必须用 keyboard.type()+Enter，不能用 fill()
4. **browser_press_key 在模态下不可用** — File chooser 模态下按 Escape 无效；取消草稿走「取消」→「不保存」
5. **browser_click 不支持带中文标点的按钮名** — 其 `target` 参数解析为 CSS 选择器，含中文标点/长时间会报错。涉及 Threads button 交互必须走 `browser_run_code_unsafe` 用 locator

## §6 选择器表

| 用途 | 定位器 | 位置 |
|------|--------|------|
| 帖子内容提取 | `a[href*="/@minonoig/post/"]` → 向上8层 container | PHASE 0 |
| 登录状态验证 | snapshot `heading "minonoig"` + link "主页" 存在 | Step 2 |
| 个人主页 | `browser_navigate → https://www.threads.com/@minonoig` | Step 1 |
| 推荐流 | `browser_navigate → https://www.threads.com/` | Step 4 |
| 发布框（主路径） | `page.getByRole('button', { name: /文本栏为空白/ })` | Step 7.1 |
| 发布框（备用路径） | `page.getByRole('button', { name: '新建串文' }).click({ force: true })` | Step 7.1 |
| 正文编辑器 | `page.getByRole('textbox', { name: /文本栏为空白/ })` | Step 7.2 |
| 发布按钮 | `page.getByRole('button', { name: '发布' }).last()` | Step 7.3 |
| 点赞按钮 | `[role="button"]` textContent 以"赞"开头且不等于"赞" | Step 4.5 |
| 回复入口 | `page.getByRole('button').filter({ hasText: /回复\s/ })` | Step 4.5 |
| 附件入口 | `page.getByRole('button', { name: '附加影音内容' })` | Step 7.2.5 |
| 取消 dialog | `button "取消"` 或 `Escape` | §3 |

## §7 发布门（前置检查清单，确认后发布）

每次发布前必须完成以下检查。任意项未通过 → 熔断不发布：

- [ ] PHASE 0 去重：待发布内容不匹配 posts[] 中任意元素
- [ ] Step 3 频率：今日 <3 条且距上次 >2 小时
- [ ] Step 3.5 审计已执行：命中阈值的方向已在选题中避开
- [ ] Step 6.5 自检：开头不重复、结构不重复、不"刷"开头
- [ ] 字数 ≤ 500 字符
- [ ] 发布后 dialog 关闭，个人主页出现新帖

## §5 对标账号（学习）

- **@koommong_** — 热点评论，2,760赞/帖
- **@sal_sololane** — 留英博主，长帖+人设
- **@rosie____0211** — 一句话共鸣，6,611赞
