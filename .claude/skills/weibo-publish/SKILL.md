---
name: weibo-publish
description: 微博发布全链路：算法策略、内容设计、热点追踪、三阶段运营（普通微博 Inline 模式已验证 ✅；头条文章/配图流程待补全）
version: 3.19
platform: 微博（weibo.com）
mode: 半自动 · 通过 Playwright Extension 操作
---

# 微博发布技能

## 0. 核心策略与认知（2026 版）

### 0.1 账号现状
- 用户名：金肛狼2003（UID 7072069544）
- 阶段：Phase 1 账号建设（粉丝/发布数/互动等动态数据去 weibo.com / 创作者中心现查，不在此留痕）
- 目标定位：消费/生活/副业观察者，带尖锐幽默感

### 0.2 微博算法关键规则
| 因素 | 说明 | 操作 |
|------|------|------|
| 首 2 小时互动 | 发布后 2h 互动(转/评/赞)越多越快，推送几率越高 | 发后 1h 内主动回复每条评论 |
| 黄金时段 | 7-9am / 12-14pm / 20-22pm | 在这三个窗口发布 |
| 图文权重 | 3 张以上图片 > 1 张 > 纯文字 | ⚠️ 当前无法程序化上传图片（见 §6），降级为纯文字帖。若手动配图，每条至少1张 |
| 话题标签 | 2-3 个，必须跟内容相关 | 超 3 个判引流降权 |
| 用户停留时间 | 浏览者停留越长，加分越多 | 内容要有信息密度 |
| 内容原创性 | 原创 > 搬运，转发率越高分越高 | 写自己的观点 |
| 账号权重 | 新账号权重低，需稳定输出积累 | 每周 3-5 条，不爆发式发帖 |
| 发布频率 | 1h 内连发多条判异常限流 | 间隔至少 30min |

### 0.3 三阶段运营策略

**Phase 1 — 账号建设（第 1-2 周）**

> ⚠️ **核心认知（2026-07-08）：一张有10万阅读的帖子如果0互动，在算法看来就是一条"没人关心的内容"。社区互动（去别人帖子下留评）让账号在平台上产生社交信号，纯发帖没有这个效果。**

- **优先级：社区互动 > 发新帖。** 每次先花时间在同话题大V热帖下留评至少2条，再考虑发新内容。
- 每天至少在同领域（消费/民生/打工人/汽车）大V的高互动帖子下留2-3条优质评论。
- **评论要有观点，不是表情包/签到级发言。** 好评论的标准：别人看到会想回复你。
- 每天 1 条热搜短评，带 #话题# + 结尾抛互动问题
- **不引流、不挂公众号**，先让账号积累社区存在感
- 对收到的每条评论必回复，培养互动习惯
- 目标：从 1 粉 → 有社区可见度 → 50-100 粉

**Phase 2 — 内容沉淀（第 3-4 周）**
- 根据 Phase 1 数据，加倍表现好的内容类型
- 每条评论必回；主动去同领域大号下刷存在感
- bio 加「公众号：远见副业笔记」
- 偶尔用头条文章写深度内容

**Phase 3 — 引流开启（第 5 周+）**
- 深度内容用头条文章，自然植入公众号
- 热点短评末尾加「完整版在公众号搜xxx」
- 常态化运营：每周 3-5 条，数据复盘驱动选题

### 0.4 内容结构公式（热搜短评模板）

```
首句吸睛（惊讶/问题/情绪/反常识）
中段核心观点（2-3 句尖锐点评，个人立场鲜明）
数据/事实支撑（1-2 句）
结尾互动引导（提问/投票/@好友）
#话题标签# 2-3 个
```

**示例结构**：
```
[反常识/情绪钩子][停顿]
[个人观点——不中立，有态度][事实依据]
[你认为呢？评论区聊聊]
#[话题1]# #[话题2]#
```

## 1. 平台认知

微博（weibo.com）是中国的 Twitter 式社交平台：
- **短内容**：普通微博，正文上限约 2000 字
- **长内容**：头条文章，适合深度长文
- **热点发酵快**：微博热搜是天然选题库
- **引流路径**：Phase 3 开启，微博摘要 → 公众号导流
- **算法导向**：首 2h 互动、图文结合、原创观点、高频稳定输出

## 2. 准备工作流

### 2.0 工具硬校验（不可跳过，先于任何网站操作）

> 🔴 **唯一合法浏览器工具 = `mcp__playwright__browser_*`。** 凡操控真实网站（微博），第一个工具调用必须是 `browser_navigate`，且**动手前先核对工具名前缀是 `browser_` 而非 `preview_`**。
>
> - `mcp__Claude_Browser__preview_*` 是 **dev server 预览窗格**（preview_start 只从 launch.json 起本地服务，只有 pixel/juejin 等本地 dev 项目，**根本没有网页浏览能力、没有 preview_navigate**），**不是浏览器工具、不是 playwright 别名**。参数里出现 `"playwright"` 字样只是命名巧合，误导不得。
> - **硬止损**：若误用 preview_* 返回 `No server named "..."` 或列出本地 dev server，立即判定"这不是浏览器工具"，**停、切 Playwright**，不许重试 preview_*。
> - 本步骤把"打开网站"这个意图**唯一锚定到 `browser_navigate`**，不给挑工具的余地。CLAUDE.md 规则2与本步骤冲突时以本步骤为准（本步骤是规则2在微博技能内的落地锚点）。

### 2.0 自主选题：微博热搜驱动

**原则：从微博热搜取材，不发问、不请示。**

```javascript
// 提取热搜 TOP 15（从 main 区域提取，缩小范围避免全场扫描）
const main = document.querySelector('main') || document.querySelector('[class*="main"]') || document.body;
const items = [];
main.querySelectorAll('a, span').forEach(el => {
  const text = el.textContent.trim();
  if (/^[0-9]{1,3}\s/.test(text) && text.length < 120 && !items.includes(text)) {
    items.push(text);
  }
});
// items = ["1热搜话题名1 热度数", "2热搜话题名2 热度数", ...]
```

**选题红线**：
- ❌ AI 相关（用户红线）
- ❌ 政治敏感
- ✅ 民生/消费/品牌（例：#物价# → 消费观察）
- ✅ 科技趋势/消费电子（例：#新手机发布# → 消费价值观）
- ✅ 教育/社会（#10 什么是文科能力 → 观点输出）
- ✅ 体育/娱乐（有讨论度的可以做）

**选题筛选流程**：
1. 提取热搜 top 15
2. 排除 AI + 政治 + 无实质内容的话题
3. 优先选「人人都有话说的」：消费、民生、教育
4. 确定角度：不蹭热度，要有**自己的尖锐观点**

### 2.1 登录与导航

```python
# 账号已在浏览器登录
page.goto("https://weibo.com")
```

### 2.2 发布普通微博

**模式选择**：走 **Inline 模式**（§2.2.1），无需打开弹窗。

#### 2.2.1 Inline 模式（已验证 20 次 ✅）

从首页 timeline 顶部内置发布框直接发布，无弹窗残留问题。

```javascript
// ⚠️ 关键：所有 Playwright click 必须用 evaluate 执行 DOM click
// browser_evaluate 的 function 参数接收完整函数体，内容内联在模板字符串中

// 1. 填充正文（MCP: browser_evaluate → function 参数传入整段函数）
// ⚠️ 必须用原生 setter 绕过 React 受控组件拦截（普通 value= + dispatchEvent 间歇性失败）
page.evaluate(() => {
  const ta = document.querySelector('textarea');
  if (!ta) return;
  
  // 原生 setter — 2026-07-09 #14 发现问题：直接赋值在某些页面状态下 content 不生效
  const nativeSetter = Object.getOwnPropertyDescriptor(
    Object.getPrototypeOf(ta), 'value'
  ).set;
  nativeSetter.call(ta, '');
  
  const content = `微博正文内容\n\n#话题#`;
  nativeSetter.call(ta, content);
  ta.dispatchEvent(new Event('input', { bubbles: true }));
  ta.dispatchEvent(new Event('change', { bubbles: true }));
});

// 2. 发送（填内容后 React 自动启用按钮）
page.evaluate(() => {
  const buttons = document.querySelectorAll('button');
  for (const btn of buttons) {
    if (btn.textContent.includes('发送') && !btn.disabled) {
      btn.click(); break;
    }
  }
});
// textarea 自动清空，无弹窗残留，不需关闭步骤
```

**通用注意事项**：
- 正文最多 2000 字
- 话题格式：`#话题名#`
- 首条不要带链接，新账号带链接权重低
- 发布后 1h 内主动回复评论
- 配图：❌ 已知限制无法程序化上传（见 §6 图片上传拦截），降级为纯文字帖

### 2.3 发布头条文章（长文）

```javascript
// 1. 打开快捷发布框（⚠️ evaluate 绕过 overlay）
page.evaluate(() => {
  const btn = document.querySelector('button[title="发微博"]');
  if (btn) btn.click();
});

// 2. 在工具栏点击"头条文章"
page.evaluate(() => {
  const items = document.querySelectorAll('[class*="toolbar"] [class*="item"], [class*="toolbar"] button, [class*="toolbar"] div');
  for (const item of items) {
    if (item.textContent.includes('头条文章')) { item.click(); break; }
  }
});

// 3. 头条文章编辑器在新页面打开（⚠️ 该流程未完全验证，见 §6）
// 标题 input：标题输入框
// 正文编辑器：富文本编辑器（支持图文混排）
```

### 2.4 内容声明

```javascript
page.evaluate(() => {
  const items = document.querySelectorAll('*');
  for (const item of items) {
    if (item.textContent.includes('内容声明')) { item.click(); break; }
  }
});
```

## 3. 热点追踪与选题

```javascript
// 1. 打开热搜页
page.goto("https://weibo.com/hot/search");
// 提取逻辑见 §2.0

// 2. 点击话题链接转到话题页看讨论内容
page.goto("https://s.weibo.com/weibo?q=话题名");

// 3. 确定角度 → 写出内容
```

## 4. 创作者中心

Phase 1 期间（粉丝 < 1万）只能访问创作者中心首页的概览数据（近7日总阅读/总互动/总涨粉），详细指标和细分报表未开放。

```python
# 创作者中心首页（含近7日概览数据）
page.goto("https://me.weibo.com")

# 数据中心（需粉丝 ≥ 1万才显示详细指标，Phase 1 可用性有限）
page.goto("https://me.weibo.com/data/overview")

# 内容管理
page.goto("https://me.weibo.com/content/video")

# 收益中心（Phase 1 不可用）
page.goto("https://me.weibo.com/income/overview")
```

## 5. Selector 参考表

| 元素 | Selector | 备注 |
|------|----------|------|
| 发微博按钮 | `button[title="发微博"]` | 顶部导航栏右侧，SVG 图标，必须 evaluate click |
| 正文输入框 | `textarea[placeholder*="新鲜事"]` | ⚠️ 页面上两个 textarea（feed+弹窗），用 placeholder 区分。**必须用原生 setter 赋值**：`Object.getOwnPropertyDescriptor(Object.getPrototypeOf(ta), 'value').set` + `dispatchEvent(new Event('input', {bubbles:true}))`；普通 `ta.value=content` 间歇性不触发 React 状态更新（见 §6） |
| 评论输入框 | `textarea[placeholder*="评论"]` | ⚠️ **优先用 Playwright 原生 `fill()`** 自然触发 React 状态（比 native setter + DOM click 更可靠）。2026-07-11 验证：`browser_type(fill)` 自动触发 React 启用按钮，Playwright click 提交无报错 ✅；同场景 native setter + `btn.disabled=false; btn.click()` 返回 400 ❌ |
| 评论按钮 | 遍历 `button` 匹配 textContent="评论"，确保按钮 enabled 后用 Playwright click | ⚠️ 用 Playwright `fill()` 自然触发 React 启用按钮，再用 Playwright click 提交。不要手动 `btn.disabled = false`（React 内部状态与 DOM disabled 不同步时，强制 enabled 提交触发后端 400） |
| 发送按钮 | 遍历 `button` 匹配 textContent="发送" && !disabled | React 拦截 Playwright locator.click，必须 evaluate DOM click；不限于弹窗 overlay（Inline 模式也需 evaluate） |
| 话题按钮 | 工具栏 `"话题"` | 点击后搜索添加话题 |
| 图片按钮 | 工具栏 `"图片"` | 点击后打开 file chooser |
| 头条文章 | 工具栏 `"头条文章"` | 头条文章编辑器 |
| 定时微博 | compose 底部 `"定时微博"` | 定时发布 |
| 内容声明 | compose 中 `"内容声明"` | AI 声明等 |
| 热搜榜单 | `/hot/search` | top 50 实时热榜 |

## 6. 已知问题与对应

| 问题 | 现象 | 适用范围 | 解决方案 |
|------|------|----------|----------|
| 按钮定位失败 | SVG button textContent="" | 弹窗模式 | 用 `button[title="发微博"]` 定位 |
| 发送按钮 disabled | 内容为空时 | 两种模式 | 先用 evaluate 填内容（value+dispatchEvent），React 自动启用按钮 |
| 发送按钮 overlay 拦截 | woo-modal-wrap 覆盖层阻挡 Playwright click | 仅弹窗模式 | 用 evaluate 执行 DOM click（Inline 模式无此问题） |
| 两个 textarea | 页面上存在两个 textarea（首页 feed 内置发布框 + 快捷发布弹窗） | 两种模式 | 用 `placeholder.includes('新鲜事')` 区分，evaluate 赋值 |
| React 受控 textarea 值不同步 | 直接 `ta.value = content` + dispatchEvent 后 `ta.value.length = 0`，React 未注册内容变更，按钮保持 disabled | 两种模式 | 用 `Object.getOwnPropertyDescriptor(Object.getPrototypeOf(ta), 'value').set` 原生 setter 绕过 React 受控组件：先 `nativeSetter.call(ta, '')` 清空，再 `nativeSetter.call(ta, content)` + dispatch input/change |
| 图片上传被拦截 | `browser_file_upload` 返回 "Not allowed"，`setInputFiles` 超时 30s，DataTransfer 不触发 Weibo Vue 响应 | 两种模式 | **当前无解**：Weibo Vue 组件拒绝程序化文件注入。推荐降级为纯文字帖或由用户手动上传。后续尝试方向：Clipboard paste 图片后 Ctrl+V |
| 头条文章详情 | 编辑流程未完全探索 | — | 首次使用时手动走一遍补全 |
| 弹窗模式：发布后弹窗不自动关闭 | 发送成功后"快捷发布"弹窗仍打开，text 保留、按钮 disabled | 仅弹窗模式 | 在发布流程末尾加一步：evaluate 查找"快捷发布"父容器并点击关闭按钮 |
| Inline 模式：无弹窗残留 | 发送后 textarea 自动清空，按钮恢复 disabled | 仅 Inline 模式 | 无额外步骤，正常行为 ✅ |
| 评论无法提交 | `ta.value = content` + dispatchEvent 后评论按钮仍 disabled；native setter + dispatch + `btn.disabled=false; btn.click()` 后端 400；`execCommand('insertText')` 返回 length=0、后端 400 | 评论功能 | **优先用 Playwright 原生 `fill()` + `click()`**：`browser_type(fill)` 能自然触发 React 状态跟踪（自动启用按钮），再用 `Playwright click` 提交。native setter + DOM click 在部分场景下因 React 内部状态不同步导致 400。2026-07-11 验证：Playwright fill + click 方案 200 ✅（2/2 次），同场景 native setter 方案 400 ❌ |
| 大V帖子评论 400 | 1000万+粉大V帖子（如陈震同学）下评论被 Playwright fill + click 返回 400 | 评论功能 | 2026-07-13 验证：同一账号在同一话题下，中小博主帖 fill+click 200 ✅，大V帖返回 400 ❌。推测需先关注博主才能通过反垃圾校验，或大V帖有额外风控。方案：先点击关注按钮再从评论框发表 |
| 品牌/企业号评论 400 | 品牌蓝V帖（如戎美 R8PTWe57s）评论区 `ajax/comments/create` 返回 400，即使 fill+click 正常、文本 ≤66 字也不进库 | 评论功能 | 2026-07-16 验证：戎美品牌号下 fill+click 两次（66字、58字）均 400 ❌，同话题林诗文/谢小斌中小博主帖 fill+click 各 200 ✅。结论：品牌/企业蓝V评论区有独立风控（非字数问题，66字内仍失败），留评优先选普通个人/中小博主帖，避开品牌号。⚠️ 微博评论历史字数上限约 140 字，留评建议压到 140 字内规避风险（超长是否必 400 未单独验证，不列为已知问题） |

## 7. 执行检查清单（每次发布前必过）

```
选题阶段：
□ 热搜 top 15 内，热度 ≥ 60 万（新账号阈值可适当放低）
□ 非 AI，非政治
□ 有个人尖锐观点角度（不蹭热度不中立）

内容阶段：
□ 首句吸睛（情绪/反常识/扎心提问）
□ 中段观点鲜明（不中立）
□ 结尾互动引导（提问/投票/@好友）
□ 话题标签 2-3 个，相关
□ 正文 ≤ 2000 字

配图阶段：
□ 至少 1 张配图（算法图文权重） — ⚠️ 当前因 Weibo Vue 组件限制无法程序化上传
□ 如无法上传，降级为纯文字帖，后续跟进上传方案

发布阶段（默认 Inline 模式）：
□ 时间窗口（7-9am / 12-14pm / 20-22pm）— 非窗口也可发布，算法加分略低
□ Phase 1：不引流、不放公众号链接
□ **路径（§2.2.1 Inline 模式）**：打开首页 → evaluate 填充 timeline 顶部 textarea → evaluate 点击发送 ✅ 无需关闭弹窗
□ 发布后确认时间线第一条可见

社区互动阶段（⚠️ 2026-07-08 新增——新号死于零互动，这条比发布优先级更高）：
□ 去该话题下找 Top 热帖，至少留 2 条优质评论
□ **评论标准**：有观点、有论据，能引发别人回复你。签到级评论（"顶""666"）不如不发
□ 关注热帖博主以便在仅粉丝可见的情况下也能互动
□ 留评方法：打开热帖详情页 → 找到 `textarea[placeholder*="评论"]` → **Playwright 原生 `fill()`**（自动触发 React 状态跟踪启用按钮）→ **Playwright `click()`** 提交。⚠️ 避免 native setter + `btn.disabled=false` + DOM click（React 内部状态不同步时提交可能返回 400）。❌ `document.execCommand('insertText')` 不可靠
□ **留评选帖红线**：① 优先选普通个人/中小博主帖；② ❌ 避开品牌/企业蓝V帖（评论区独立风控，fill+click 仍 400，见 §6）；③ ❌ 避开 1000万+粉大V帖（需关注博主，见 §6）；④ 评论正文压到 140 字内规避字数风险（超长是否必 400 未单独验证）
□ 留评后验证：提交后确认 textarea 清空 + 评论出现在列表（body 含评论片段）
□ 发帖后 1h 内回来看自己的帖子有没有评论，有则回复
```

## 8. 复盘→技能转化（必须执行）

> **复盘按 CLAUDE.md 技能修复标准流程执行**

**原则：每次执行完毕，必须把卡点、数据、新选择器、绕过方案当场写回 SKILL.md，不留待下次。**
**不依赖记忆：洞察进技能文件，不进记忆。记忆只存状态事实。**

### 8.1 转化检查清单（执行后五问）

```
□ 是否有新的报错/异常？ → 写入 §6 已知问题表（含错误码、报错信息）
□ 是否有新的选择器/坐标？ → 写入 §5 Selector 参考表（注明 ⚠️ 事项）
□ 是否有步骤代码需修正？ → 替换 §2.x 代码块（必须用验证通过的代码替换）
□ 是否有步骤顺序/前置条件需补充？ → 补充到对应 §2.x 说明
□ 是否有运营策略/算法洞察需更新？ → 更新 §0 策略
```

### 8.2 数据复盘维度（发布后 24h 采集）

> 🔴 **状态不落地**：发布数、阅读、互动、粉丝等动态数据**不写发布记录、不建日志文件**。需要时去 weibo.com / 创作者中心现查（扫一眼即得），不在本地留痕。本维度仅用于"本次效果判断是否要调选题策略"，判断完即弃，不留档。

| 维度 | 说明 | 用途 |
|------|------|------|
| 发布时间 | 精确到分钟 | 验证黄金时段效果 |
| 首 30min 阅读 | 发布后短时曝光 | 判断初始流量池大小 |
| 24h 阅读 | 最终阅读量 | 评估选题热度 |
| 互动数 | 转+评+赞 | 判断内容质量 |
| 粉丝增长 | 新关注数 | 评估涨粉效率 |
| 是否配图 | 有/无 | 验证图文权重规则 |

### 8.3 转化执行流程

```
Step 1: 回顾本次执行的完整日志
        - 工具调用记录（报错、超时、绕过方式）
        - 浏览器控制台错误
        - 发布后 30min 数据快照

Step 2: 对照 §8.1 检查清单逐项标记

Step 3: 编辑 SKILL.md
        - 报错/绕过 → §6 已知问题
        - 新 Selector → §5 Selector 表
        - 代码修复 → §2.x 代码块
        - 流程变更 → 对应 § 说明
        - 策略更新 → §0 策略/算法
        - 🔴 不写发布记录、不建日志（状态去平台现查，见 §8.2）

Step 4: 三表一致性确认
        □ §5 Selector表、§6 已知问题表、§2.x 代码块三者一致
        □ 改一处不更新另一处 = 下次还得踩坑
```

### 8.4 典型转化场景速查

| 本次发现 | 转化到 | 示例 |
|---------|--------|------|
| 按钮定位失败 | §5 + §6 | SVG button textContent="" → 用 title 属性 |
| overlay 拦截点击 | §2.2 + §5 + §6 | woo-modal-wrap → evaluate DOM click |
| textarea 二义性 | §2.2 + §5 | 两个 textarea → placeholder 前缀+内容内联 |
| React 状态不同步（正文） | §2.2 + §6 | native setter 绕过 React 受控组件，Playwright fill 不触发 React 状态 |
| React 状态不同步（评论） | §5 + §6 + §7 | Playwright fill 自然触发 React 状态跟踪 ✅；native setter + DOM click 部分场景 400 ❌ |
| 算法新规则 | §0 | 图文权重/黄金时段/新账号限频 |
| 数据表现差 | §0 + §2.0 | 同一类型内容持续低互动 → 换选题方向 |
| 内容模板优化 | §0.4 | 首条不吸引人 → 更新模板结构 |
