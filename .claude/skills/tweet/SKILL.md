---
name: tweet
description: "自动执行一次完整的 @Eveacry 账号运营 run（选题→配图→发布→回复→复盘→回写）"
---

# /tweet 技能

## 工具链（唯一，合并自旧版三条重复规则）

本技能所有浏览器操作**只允许**使用 `mcp__playwright__*` 系列 MCP 工具。直接调用，不做存在性预检。仅当真实调用返回连接错误时简短报告，绝不退回任何独立浏览器进程。

**禁止：** playwright CLI、Puppeteer、Selenium、nodriver、fill()、locator .type()。

**X 交互固定方案：** `browser_run_code_unsafe` + Playwright locator API（getByRole/getByTestId）。CSS 选择器不可靠，禁止使用。

**输入方式：**
- 主推：`navigator.clipboard.writeText()` → 首页 composer Ctrl+V 粘贴 → 读回校验
- 回复：`page.keyboard.type(text, { delay: 20 })` — 禁止剪贴板

**X 元素定位：**
- Post 输入框：`getByRole('textbox', { name: 'Post text' })`
- 主推 Post 按钮：`getByTestId('tweetButtonInline')`
- 回复 Post 按钮（composer 弹层内）：`getByTestId('tweetButton')`
- 回复 Post 按钮（详情页 inline）：`getByTestId('tweetButtonInline')`
- 配图媒体按钮：`getByRole('button', { name: 'Add photos or video' })`
- beforeunload 弹层：`browser_handle_dialog({ accept: true })`

**路径：** 首页 `https://x.com/home`。禁止 `https://x.com/compose/post`。

---

## 唯一主管道（每次 /tweet 严格执行此顺序，不跳过、不重排）

### PHASE 0：硬性去重（熔断级，不可跳过）

**输入：** 无
**动作：** 打开个人主页 `/Eveacry`，evaluate 提取所有可见推文正文到 posts[]
**成功标准：** 获得 posts[]
**执行判断：** 待发布内容与 posts[] 中任一元素 **完全匹配或高度重叠**（同主题/同链接）→ **熔断终止**，报告"已发布过相同内容"。
**失败处理：** posts[] 为空时记录 `dedup_skipped=true`，继续执行（可能页面未加载完，主推仍有预检保护）。
**不依赖记忆或历史记录**——必须实时从页面提取。

### Step 1：选题取数

**输入：** 无（或用户指定的主题）
**动作：**
1. 内容模式审计：取主页最近 5 条推文的开头句式/帖子类型/话题域。任一维度 ≥3 条同模式 → 本轮避开该维度。
2. 热点搜索（仅 3 层，逐层下降）：
   - **第 1 层** — `https://www.nodeloc.com/latest`，找白嫖/免费/工具角度
   - **第 2 层** — `https://x.com/explore` 或 X 搜索（模板见下）
   - **第 3 层** — 外部搜索（Exa/Tavily/WebSearch）

   搜索到的热点必须标明"发现于 NodeLoc/X/外部"。NodeLoc 内容不受"必须当天"约束；X 热点必须当天（"h"/"m"时间戳可用，"昨天"/"≥24h"/"Jun X"丢弃）。
3. 选题输出：1 个热点角度 + 内容类型（资源帖/观点帖）。agent 自行决策，不抛给用户选择。
4. 如果启用了推广模式（用户明确说「发广告/推广/宣传」），跳过搜索，直接创作推广推文。

**成功标准：** 获得 1 个可用角度
**失败处理：** 所有搜索通道失败 → 生成通用观察（run log 记 hot_search_failed=true，不声称"最近/今天"）

**X 搜索模板（第 2 层用）：** `https://x.com/search?q=AI+tool+OR+free+tool+OR+productivity&src=typed_query&f=live`
每次抽样 1-2 个搜索页，搜索总时长 ≤3 分钟。

### Step 2：配图生成

**输入：** 主推文本
**动作：** 调 `generate_image.py`（OpenAI 库封装）用 Agnes API 生图，风格根据推文类型选择（见配图流程）。文件保存到本地 disk。
**成功标准：** 图片文件 ≥10KB 且带 `.png` 扩展名
**失败处理：** 失败 → 重试 1 次。仍失败 → 跳过，记 `image_generation=failed`。不影响主推发布。

### Step 3：发布主推

**输入：** 推文正文 + 配图文件（可选）
**动作：**
1. 首页 composer 点击 → 剪贴板粘贴（Ctrl+V） → 读回校验（检测重复则清空重试）
2. 上传配图：`browser_run_code_unsafe` 点击媒体按钮 → `browser_file_upload` 传入本地文件 → 确认 composer 出现 Media 组
3. **Preflight（逐项确认）：**
   - 字数合理，无超限警告
   - Post 按钮可用（非 disabled）
   - 配图已上传（如有）
   - 未使用 fill()，未进入 /compose/post
   - 非推广模式时不含推广内容
   - 没有敏感/金融/医疗法律内容
4. 点击 Post，等待 ≥3 秒

**成功标准（两层核验，缺一不可）：**
1. 发布信号：toast 含 "was sent" 或 composer 清空
2. 可见性核验：打开 `/Eveacry` 个人主页，确认目标文本真实出现

**失败处理：** 仅第 1 层通过 → 状态记 `post_clicked_unverified`，先查重，**不得再次点击 Post**。60 秒内无法确认 → 停止报告，不盲目重发。同一条文本在同一轮中最多提交一次。

### Step 4：涨粉互动

**输入：** 无
**动作（总量固定，不多不少）：**
1. 读取运营记忆中的 `daily_reply_YYYY-MM-DD`。当天累计已达 15 条 → 跳过本步，记 `daily_reply_cap_reached=true`。
2. 点赞：X live search 搜今日热点 → 随机点赞 **3-5 条**帖子
3. 回复：选 **4-7 条**帖，在时间线/搜索页用 `browser_run_code_unsafe` 完成回复（不外导航到详情页）：
   - testid 定位帖子 → 点击 reply → 聚焦输入框 → `page.keyboard.type(text, { delay: 20 })` → 验证按钮 `aria-disabled` → 点击提交 → 校验 `was sent`
4. 主推发布后检查评论区：有人回复 → 必须回复回去（最高杠杆）
5. 每条间隔 30-90 秒。同一帖只回 1 条，同一作者一天不连续回 2 条以上。每 3 条一轮，不一次性连发。

**成功标准：** 全部回复确认 `was sent`
**失败处理：** rate limit 提示 → 立即停止当轮，记 `rate_limited=true`。下次降低 30% 量。

### Step 5：复盘

**方法：** 按 CLAUDE.md「技能修复标准流程」执行。检查本次执行有无堵塞/模糊点。
**产出：** 有修改 → 直接改 SKILL.md 已有章节（diff）。无修改 → 声明即可。
**禁止：** 运行日志、待处理列表、自我表扬。
**前置数据检查：** Analytics 页 <50 粉无详细指标 → 跳过，改用个人主页目测 views 数。

### Step 6：回写状态

更新 `twitter_account_management.md`，记录：本轮主推内容、配图风格（如有）、回复数、点赞数、当日累计回复数、异常标志。

---

## 人设（贯穿主推与回复）

**一句话：像朋友随手甩给你一个好用的东西。** 不在写专栏、不在卖课。

- 口语化，不书面：用"试过""翻车了""发现一个事""整理了一份"
- 观点帖：直接说结论，不写三段式。一个反问/一个观察就行。
- 资源帖：写清楚怎么拿到、怎么操作，不只报喜。抓 1-2 个最实用的点。
- **核心自检：读者看到这条推能立刻去操作吗？**
- **每条推写完自检：前 15 字让人想继续看吗？**
- 中文为主，英文穿插。不中英混写。
- 禁止：商业推广（除非用户明确下令）、金融/医疗/法律建议、传播未经核实的信息。

**回复风格：有梗玩梗，离谱吐槽，有经历就分享，没话说就闭嘴。** 简单一句「谢谢分享」比硬写分析更自然。三大禁句：好帖、学到了、从另一个维度。

---

## 账号约束

| 约束 | 规则 |
|------|------|
| 字数 | 无蓝 V 280 字符上限。字数由内容决定，禁止凑字数。写完后问：一半字能说清吗？ |
| 频率 | 每次只发 1 条主推。同日可多次触发。主推间隔 ≥30 分钟。 |
| 回复上限 | 单日累计 ≤15 条（所有 run 合计）。每轮 4-7 条。 |
| 点赞 | 每轮 3-5 条。 |
| 内容 | 保持在 AI 工具 / 效率工具 / 开发赛道。 |

**推广模式**：仅用户明确说「发广告/推广/宣传」时启用。推广推文只推一个项目，不夸大，不承诺收益，不使用"颠覆/暴富/稳赚"。

**免费资源链接（默认允许）：** GitHub 链接、免费在线工具 URL、自己整理的免费模板/指南。CTA 允许"需要的直接拿→链接""关注我持续整理"。禁止"点赞转发让更多人看到"及任何付费引导。

---

## 中断恢复

发布中断重启后：
1. 读取运营记忆中的状态枚举（`planned → drafted → post_clicked_unverified → posted → blocked`）
2. `posted` → 不得重发
3. `post_clicked_unverified` → 检查个人主页，同文本已出现则标记成功；未出现且 composer 保留文本则继续核验后发布
4. `planned`/`drafted` → 正常执行
5. 状态不明 → 停止报告，不盲目点击

---

## 配图流程

**位置：** 配图准备在 Step 2（选题取数阶段）完成，不在 Step 3（发布阶段）执行。推文文本写入 composer 后**不得触发 `browser_navigate` 离开首页**。

**生成：** `python generate_image.py "<prompt>" "tweet_img" "1024x1024"`
- Prompt 模板：`{构图/镜头}, {主体+动作}, {场景环境}, {光线物理}, {风格/媒介}, {配色}, {材质细节}, {隐含排除短语}`
- 英文书写，每张图讲一个视觉概念。不加图片上的文字。
- 使用 `generate_image.py`（OpenAI 库）调用 Agnes API，禁用 urllib/curl/Node.js

**上传：** `browser_run_code_unsafe` 点击 `getByRole('button', { name: 'Add photos or video' })` → `browser_file_upload` 传入本地文件 → 确认 composer 出现 "Media"。
- 文件必须带扩展名（`.png`）。上传前 `cp <file> <file>.png`。

**失败处理：** API 连接失败或上传失败 → 跳过配图，记 `image_generation=failed` 或 `image_upload=failed`。不加替代路径。不影响主推发布。

**风格规则：** 每轮选一种风格（产品摄影/微距/水彩/等距/杂志/微型模型/日式极简/复古/矢量/长曝光）。与前两轮不同。配色与前一轮不同。不连续两轮用同一主体类别。具体风格的 prompt 示例参考 `references/prompt_examples.md`（不在本技能文件）。
