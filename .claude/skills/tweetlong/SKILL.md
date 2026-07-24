---
name: tweetlong
description: "发布 1 篇 X Articles 长文章到 @Eveacry（独立于短推文的管道）"
---

# /tweetlong 技能

## PHASE 0：硬性去重（熔断级，不可跳过，必须先执行）

**执行时机**：每次启动本技能、写任何内容之前。必须先到个人主页提取所有已发布 Articles 标题。

### 步骤

1. 导航到个人主页 Articles 标签页（能看到已发布文章标题的页面）
2. evaluate 提取所有可见文章标题到数组 titles[]
3. 比对规则：
   - 待发布标题与 titles[] 中任一元素完全匹配 → **熔断，不发布，报告"已发布过：[重复标题]"**
   - 待发布标题关键词与 titles[] 中某元素高度重叠（同一事件/同一模型名/同一主题）→ **熔断**
4. 熔断后终止流程，不写任何新内容

### 铁律
- 每次启动技能必须先执行此事。不做就去写内容 = 流程违规。
- 不依赖记忆或历史记录——必须实时从页面提取。

---

用途：触发后在 X 独立编辑器 `/compose/articles` 发布 **1 篇长文章**。和 `/tweet`（短推文）是**两套完全独立的内容管道**——不同入口、不同编辑器、不同展示位置。

一次 /tweetlong 只发 **1 篇** Article。不发短推文、不批量连发。

## 人设：哥们分享（同 /tweet）

**@ChenY4761 的唯一人设：像朋友随手甩给你一个好东西。**

写长文章仍然不是写专栏。区别只是篇幅更长，语调不变：

- **开头**：仍然是"发现一个事""最近试了 X""之前踩过一个坑""整理了一份清单"。不用"本文将介绍""在当今...""随着..."这类教科书/论文开头
- **正文**：短句、短段。有时候一句一段。空行比标题更能让读者在移动端读下去
- **哥们感**：自言自语式的评论（"第 3 个真是没想到""这个我用了半年才敢推荐""第 2 个踩过坑"）比客观描述好得多
- **干货优先**：整篇文章核心是"送东西"——送工具清单、送配置模板、送避坑经验。不是输出观点，是交付价值
- **收尾**：不提"关注我"。用"试试看，有问题评论区聊""拿去用，好用告诉我"

## 选题范围：白嫖+干货优先

**核心原则：文章是资源交付，不是观点输出。** 写长篇的目的是让读者看完觉得"这波赚了"，而不是"这人说得对"。

### 写前必做（两步，缺一不可）

**Step A — 历史数据复盘**
打开 Analytics（`/i/account_analytics`），看上篇 Article 的数据。

**Step B — 学习头部账号排版/字数/风格**
打开 2-3 个热门 X Articles 账号（如 X Explore 里 Articles 高互动文章的作者），逐篇分析：
- **排版**：段落长度（一行一段还是多行一段）、标题使用频率、是否有列表/引用块
- **字数**：头部文章通常多少 words（看 X word counter）——中文 articles 一般在什么量级
- **风格**：开头方式、干货密度、人称视角、收尾方式

每篇记录 1-2 个可借鉴的具体点。然后决定"这篇要用什么排版和节奏"。

**判断方向**：
- 上一篇数据好 → 同样的题材类型再来一篇（换具体工具/案例）
- 上一篇数据差 → 换选题方向（清单→教程，或反方向）
- 如果还没有发过 Article → 选最稳的第 1 梯队选题（工具实测清单）

### 优先选题（按价值排序）

**第 1 梯队 — 免费工具实测**
- "我测了 8 个免费 AI Agent，第 3 个让我换掉了 Copilot"
- "5 个开源的 MCP Server，直接部署就能用"
- "2026 免费 AI 编程助手横评，都在用的就这几个"
- 每个工具 1-2 句真实使用感受 + 适用场景，不写说明书

**第 2 梯队 — 免费资源/模板**
- "我的 CLAUDE.md 完整配置，复制即用（附详解）"
- "GitHub 上 5 个星标过万的免费 AI 项目"
- "MCP 服务端搭建教程，全免费工具链"

**第 3 梯队 — 避坑/复盘**
- "0 粉做 X 账号 30 天，这些坑浪费了我两周"
- "用了半年 AI agent 写代码，实话实说哪些好用哪些翻车"
- 诚实讲结果。数据好的写为什么好，不好的写为什么翻车

**禁止选题**：付费工具推广、软文式评测、纯观点输出、政治/币圈/娱乐。

### 三问决策法
1. 读者一周后还想回来翻吗？（是 → Article）
2. 需要图片/代码块/分段才能说清吗？（是 → Article）
3. 价值在深度（教程/清单）还是序列（续集/故事弧）？（深度 → Article）

## 推荐的文章结构（约 3,000 字）

3000 字左右才能提供真正完整的资源交付。太短就成了"带链接的帖子"而不是文章。

**常用骨架之一（可用，但不得连续两篇同骨架）：**
```
1. H1 标题 — 60 字符内，做具体承诺（不是"X 介绍"，是"我试了 8 个 X，发现..."）
2. 引语（2-3 行）— 谁应该看、看了有什么好处
3. 背景/痛点（200-400 字）— 开门见山，不铺垫背景
4. 正文 4-6 个小节（每个 400-600 字）— 每个工具/要点有清晰小标题+具体使用场景
5. 对比/总结（200-400 字）— 什么时候用哪个，横向对比
6. 收尾（100-200 字）— "试试看"，不写"关注我"
```

**⚠️ 结构多样性规则（2026-07-17 统一修复新增）：**
- 不得连续两篇使用相同骨架。
- 可替换骨架示例：
  | 骨架类型 | 适用场景 | 结构 |
  |---------|---------|------|
  | 问题解决型 | 教程/指南 | 痛点→方案分步→效果对比→注意事项 |
  | 叙事复盘型 | 经验分享 | 背景→做了什么→踩了什么坑→学到了什么 |
  | 清单盘点型 | 资源汇总 | 分类→逐项介绍（每项格式一致）→一句话总结 |
  | 对比辩论型 | 选型建议 | 选项 A → 选项 B → 对比表 → 建议 |
- 每篇选定骨架后，在发布记录中标注使用类型。

正文小节推荐：6 个点比 5 个好（备 6 选 5），让内容更有厚度。
每个工具/资源配 1-2 句真实使用感受 + 适用场景 + 简单装法/用法说明，不写说明书。

发布的文章自动生成一条推文卡片到时间线（含标题+封面+简介），不用额外发推宣传。

## Agnes API 配图（封面 + 正文插图）

文章需要两种配图：**封面图**（必选）和**正文插图**（可选，增强可读性）。

### 封面图
- 比例：5:2（推荐 1200×480 或 1500×600 px）
- 生成方式：Agnes API（同 `/tweet` §16.1）
- 提示词风格：文章主题相关的视觉场景，抽象概念图或场景插画，不加文字

### 正文插图
Articles 支持在正文中穿插图片。以下情况推荐加图：
- 教程步骤：截图说明关键操作
- 工具对比：截图展示界面
- 数据/效果："before/after" 对比

正文插图用 Agnes API 生成（同封面），或截取真实使用截图。

### Agnes API 配置

```
Endpoint: POST https://apihub.agnes-ai.com/v1/images/generations
API Key: sk-37fc8R90O1p5YQy7py4vQpmbWywfsnqg3qLJxxJg2cO8y3Ui
Model: agnes-image-2.1-flash
Size 封面: 1024x1024 → 裁剪为 5:2，或用 1792x716（如果支持横版）
```

请求格式同 `/tweet` §16.1.1。拿到图片 URL 后，按上传流程注入编辑器。

### 上传流程
封面/正文图片的上传路径：

**核心规避策略**（同 `/tweet` §16.2）：在一个 `browser_run_code_unsafe` 调用内完成全部操作——React onChange 注入一次完成，MCP modal state 锁不影响同一调用内的执行。

#### 前置条件
- HTTP server 已在本地端口提供服务：`python -m http.server 18765 --bind 127.0.0.1`（在 claudework 目录下运行）
- 封面图片在 claudework 根目录，命名 `tweetlong_cover{N}.png`
- 确认 `document.querySelector('input[type=file]')` 存在（Articles 编辑器默认已有，不需要点击任何按钮创建）

#### 执行（单次 browser_run_code_unsafe）
```javascript
async (page) => {
  const imgUrl = 'http://127.0.0.1:18765/tweetlong_cover4.png';

  // 1. 用 page.request.get() 在 Node.js 端取图（绕过 CSP mixed content 限制）
  const resp = await page.request.get(imgUrl, { timeout: 15000 });
  const buf = await resp.body();
  const b64 = buf.toString('base64');

  // 2. 在浏览器端解码 → File → DataTransfer → React onChange 注入
  const result = await page.evaluate((imgb64) => {
    const input = document.querySelector('input[type=file]');
    if (!input) return 'ERROR: no file input';

    const binaryStr = atob(imgb64);
    const bytes = new Uint8Array(binaryStr.length);
    for (let i = 0; i < binaryStr.length; i++) bytes[i] = binaryStr.charCodeAt(i);

    const file = new File([bytes], 'cover.jpg', { type: 'image/jpeg' });
    const dt = new DataTransfer();
    dt.items.add(file);

    // Inject via React __reactProps.onChange
    const reactKey = Object.keys(input).find(k =>
      k.startsWith('__reactProps') || k.startsWith('__reactEventHandlers')
    );
    if (reactKey && typeof input[reactKey]?.onChange === 'function') {
      input[reactKey].onChange({ target: { files: dt.files } });
      return 'ok: react, size=' + file.size;
    }

    return 'ERROR: no injection method';
  }, b64);

  return result;
}
```

返回 `"ok: react, size=xxxxxx"` 或 `"ok: setter, files=1"` 代表注入成功。

#### 上传后确认
1. **等待 2-3 秒**让 React 处理上传
2. 检查 `document.querySelectorAll('img[src*="blob:"]').length ≥ 1` 或 `button "Remove photo"` 是否存在
3. **关键：弹出 "Edit media" 裁剪对话框 → 必须点击 Apply 确认**
   - 用 `page.getByRole('button', { name: 'Apply' }).click()` 点击
   - 等待封面预览出现（看到 `Remove photo` 按钮 = 上传成功）
4. 若未出现 blob: img，重新执行一次（注入时机问题，React 可能在挂载 handler）

#### 上传后坐标定位（供后续验证使用）
```
确认上传成功：document.querySelector('img[src*="blob:"]') !== null
点击 Apply 确认裁剪：page.getByRole('button', { name: 'Apply' }).click()
确认封面已设置：[...document.querySelectorAll('button')].some(b => b.textContent.includes('Remove photo'))
```

## 防封策略（Articles 特有）

Articles 的防封风险点和短推文不同，需区别对待：

### ✅ 低风险行为
- **频率**：Articles 不存在"刷屏"问题，一天发多篇也不触发 spam（但质量优先，建议 ≤2 篇/天）
- **链接**：免费资源链接完全允许，蓝 V 无链接惩罚
- **内容长度**：越长越安全（X 算法更认可长内容的原创性）

### ❌ 高风险行为（严格禁止）
- **商业推广链接**：带 affiliate 链接、付费产品链接 → 高频封号原因
- **抄袭/洗稿**：搬运他人博客/教程 → X 会降权甚至封号
- **夸大承诺**："用了这个收入翻倍""保证涨粉 X" → 触发内容审核
- **敏感内容**：政治、金融投资建议、医疗建议、色情

### 内容红线
- 所有推荐的工具/资源必须是**免费**或**有免费档**的
- 如果提到付费工具，必须有免费替代方案的对比
- 推荐工具时要注明是免费/开源/有免费额度
- 不承诺效果，只说"我用了觉得好用"

## 发布流程

### 入口
`https://x.com/compose/articles` → 点 `create` 按钮（⚠️ `/compose/articles/edit/new` 会 302 跳转到管理页，不可用）
或左侧导航栏 Articles → 同上管理页 → create

### 编辑器结构
```
文章管理页：/compose/articles
  → Drafts / Published 标签切换
  → "create" 按钮打开新编辑器

编辑器结构（/compose/articles/edit/{id}）：
  → 标题输入框：textbox "Add a title"
  → 正文区域：textbox (placeholder="Start writing")
  → 格式化工具栏：
    - 粗体/斜体/删除线/代码块
    - 标题层级（H1/H2/H3）
    - 有序/无序列表、引用块、Emoji
    - 媒体插入（图片/视频）
    - 字符/词计数器
  → 封面图片：5:2 比例，Add cover → Choose File
  → 作者署名：Echo Verified account @ChenY4761
  → Publish 按钮（内容为空时 disabled）
  → Preview / Focus mode
```

### 操作顺序（实测可用路径）
```
入口方式 A（推荐）：https://x.com/compose/articles → browser_run_code_unsafe 点击 create 按钮
  page.getByRole('button', { name: 'create' }).click()
  → 等待跳转到 /compose/articles/edit/{id} 编辑器

→ 【封面图】: Agnes API 生成 5:2 比例图片 → 本地 HTTP server 提供 → 单次 browser_run_code_unsafe 内 page.request.get() 取字节 + page.evaluate DataTransfer 注入（不点击 Add photos 按钮）
   关键：上传后会弹出 "Edit media" 对话框 → 必须点击 Apply 确认 → 看到 Remove photo 按钮 = 成功
→ 输入标题：getByRole('textbox', { name: 'Add a title' }).fill('标题')
   标题用 fill() 直接输入即可，不必 keyboard.type
→ 输入正文：clipboard writeText 写入 → 点击正文 textbox 聚焦 → Ctrl+V 粘贴
→ 【可选】正文插图：在对应段落位置 → 媒体插入按钮 → 上传
→ Preflight：Publish 可用 + 本地统计中文字数 ≥ 2500
→ 点击 Publish（getByRole('button', { name: 'Publish' })）
→ 【关键：确认对话框】弹出 "Publish Article" 对话框，含 audience/reply 设置和 Timeline preview
→ 在对话框内再次点击 Publish（dialog.getByRole('button', { name: 'Publish' })）
→ 等待页面跳转（URL → /ChenY4761/status/{id} 推文卡片页）
→ 核验：/ChenY4761 的 Articles 标签页确认新文章出现（封面 + 标题 + 时间戳）
```

### ⚠️ 入口陷阱（实测踩坑）
`/compose/articles/edit/new` 这个 URL **不直接打开编辑器**，而是 302 跳转到管理页。必须：
1. 进管理页 `/compose/articles`
2. 点击 `button "create"` 创建新草稿
3. 才会跳转到 `/compose/articles/edit/{id}` 编辑器

### 输入方式
长内容不逐字 type。使用 clipboard writeText 写入整段 → Ctrl+V 粘贴。

注意粘贴前 **必须先点击正文 textbox 使其聚焦**，再按 Ctrl+V。如果光标在标题输入框或其他位置直接 Ctrl+V，内容会粘贴到错误位置。

**🔴 正文必须一次性整体粘贴（2026-07-02 #4 实测修正，禁止分批）**：分批粘贴时 contenteditable 光标定位不可靠（End / Enter 定位不生效），会导致内容顺序错乱。正确路径：clipboard writeText 全文 → 聚焦正文 → Ctrl+V 一次贴完。若粘贴结果异常（缺段/乱序）：Ctrl+A → Delete 清空 → 重新一次性粘贴全部，不要在已有内容上修补。
格式化暂不处理（纯文本+换行分段，标题单独输入）。

### ⚠️ X word counter 实际表现（2026-06-30 实测，很重要）
X 编辑器的 word count **不是字符数，也不是真实分词数**。
实测：2984 中文字的文章，X 显示 **272 words**。

所以：
- **不要用 word counter 判断字数是否达标**
- 中文字数判定方法：粘贴前把正文复制到本地统计工具数中文字数
- 技能目标仍是 **~3000 中文字**，但不是让 X word counter 显示这个数
- 发布前核验清单中的字数检查改为：**确认本地统计的中文字数 ≥ 2500**（因为有去除 markdown 语法后的缩水）

### 发布前核验
- [ ] 本次只发布 1 篇 Article
- [ ] 写前已学习 2-3 个头部账号的排版/字数/风格（有笔记）
- [ ] 选题是资源交付类（非纯观点输出）
- [ ] 推荐的工具/资源全部免费或有免费档
- [ ] 封面已上传（5:2 比例，Agnes 生成，Edit media 弹框已 Apply）
- [ ] Publish 按钮可用
- [ ] 字数达标：本地统计中文字数 ≥ 2500（不用 X word counter 判断，实测 2984 中文字仅显示 272 words）
- [ ] 正文至少有 4-6 个清晰小节
- [ ] 风格符合哥们闲聊人设，不是专栏腔
- [ ] 没有商业推广链接
- [ ] 没有夸大承诺/虚假信息
- [ ] 如果含链接，链接指向的是免费资源

### 发布后核验
判定 "published" 必须同时满足两层：
1. **发布信号**：确认对话框关闭，页面跳转到 `/ChenY4761/status/{id}` 推文卡片页（Articles 发布后自动生成一条推文卡片到时间线）
2. **可见性核验（强证据）**：打开 `/ChenY4761` 个人主页 → Articles 标签页，确认新文章标题、封面和时间戳真实出现

### 编辑注意事项
Articles 的"编辑"= **取消发布 → 改 → 重新发布**。编辑后原文章 URL 可能变化，互动可能丢失。
所以发前检查比发后改更重要。小错（错别字）在生成的文章推文卡片下回复更正即可。

## 中断恢复
- 如果状态是 `published`，不得重发
- 如果状态是 `post_clicked_unverified`，先检查 Articles 标签页
- 若同文章已出现，标记成功
- 若未出现且编辑器仍有内容，可继续核验后发布
- 若编辑器为空且未发现已发布，停止报告

**状态枚举：** `planned → drafted → editor_loaded → content_typed → preflight_passed → post_clicked_unverified → published`

## 防重复
发布按钮点击后：
1. 等待 ≥3 秒
2. **不得立刻二次点击**
3. 不确定时先检查 Articles 标签页
4. 同内容已出现即标记成功
5. 60 秒内无法确认则停止报告，不盲目重发

## 工具链
同 `/tweet` 固定工具链：Playwright MCP 独占，x.com 已登录浏览器会话。
入口路径：`/compose/articles` → 点 create 按钮
数据分析（可选回顾）：`/i/account_analytics` 或 Creator Studio

## 推广红线
同 `/tweet` §2：默认不推广用户项目。用户说「发广告/推广/宣传」时才启用推广模式。

## 内容模式审计（2026-07-17 统一修复新增）

**前置检查：** 取 Articles 标签页最近 2 篇已发布文章，检查：

| 维度 | 检查内容 |
|------|---------|
| 骨架类型 | 是否连续两篇用了同一骨架？（问题解决/叙事复盘/清单盘点/对比辩论） |
| 开头方式 | 是否都以同类型开头？（痛点/背景/数据/故事） |

连续 2 篇同骨架或同开头 → 本篇必须换。

## 复盘与回写（2026-07-17 升级为检查清单）

每完成一次发布，记录到运营记忆（`twitter_account_management.md`）：
- 发布时间、标题、字数（中文字数 + X word counter 两个值）
- 封面图（Agnes 生成 ✓ / 失败跳过）
- 正文配图数量
- 发布状态（published / failed）
- 选题类型（工具清单/教程/复盘/模板）
- 包含的免费资源类型
- 🟡 所选骨架类型？（不连续两篇同骨架）
- 🔴 字数是否达标（~3000 中文字）

> **复盘按 CLAUDE.md 技能修复标准流程执行**

## 技能进化记录（每次执行后更新本文件）
每次执行遇到堵塞点或发现优化点，**当场修改本文件**对应章节。不改记忆，改技能。
- 2026-06-30: 修正入口路径（/edit/new 不直接打开编辑器）; 修正 word counter 认知（实测中文显示极低）; 补充封面上传后 Apply 确认步骤; 新增"写前学习头部账号排版/字数/风格"步骤
- 2026-07-01: 封面图上传流程重写：弃用 setInputFiles（被 X.com React 屏蔽），改用 page.request.get() + base64 + page.evaluate DataTransfer 注入方式，无需点击 Add photos 按钮防文件选择器阻塞
- 2026-07-02: 封面图上传流程从 nativeInputValueSetter 精确为 React __reactProps.onChange 完整可执行脚本；contenteditable 正文粘贴方式从分批粘贴改为一次性 Ctrl+A → Delete → 全部（clipboard）解决定位不准问题；更新点击 Publish 位置为 browser_run_code_unsafe 优先（browser_click CSS 选择器解析失败）
