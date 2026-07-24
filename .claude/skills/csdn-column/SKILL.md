# CSDN 专栏管理技能

**触发**：`/csdn-column` 或「管理 CSDN 专栏」
**账号**：deepseek23（https://blog.csdn.net/deepseek23）
**版本**：v1.1（2026-07-05）

## §0 专栏策略（参考头部账号）

### 账号定位
AI 工具 / LLM 应用 / MCP 协议 中文技术博主

### 头部账号的专栏规律（调研了 CSDN资讯、way_more、谙忆 等）

| 策略 | 说明 | 参考 |
|------|------|------|
| **按技术栈拆分** | 不把所有内容塞一个分类，每个专栏聚焦一个知识点 | way_more 有 30 个专栏：springboot、redis、k8s 各一个 |
| **专栏即目录** | 读者进博客先看专栏，找到主题直接翻阅 | CSDN资讯用"资讯(1275篇)"、"AI(113篇)" 聚合 |
| **命名简短直接** | 一两个词，不写长句子 | "AI"、"java"、"redis" |
| **系列化产出** | 同主题文章 ≥5 篇就开专栏聚合 | 谙忆有 97 个专栏，付费专栏 11 个 |
| **付费专栏** | 源码解析、项目实战类设专栏定价 | 谙忆的"SSM深入解析(110篇)" 等 |

### 推荐专栏规划

根据我们已发布的内容：

| 专栏名 | 包含文章 | 状态 |
|--------|---------|------|
| MCP 协议实战 | MCP Server 全系列 10 篇（压测/手写/排坑/协议拆解/鉴权等） | ✅ 建立，含 10 篇 |
| AI 编程经验 | Codex 幻觉实测、Claude Code 子智能体、从 Copilot 到 Agent | ✅ 建立，含 3 篇 |
| LLM 应用开发 | AI Agent 入门实战：Function Calling | ✅ 建立，含 1 篇 |

## §1 完整流程

### 页面
- 管理列表：`https://mp.csdn.net/mp_blog/manage/column/allColumnList`
- 新建专栏：从管理页点击「新建」按钮进入（直接访问 columnAdd 会 404）
- 专栏管理：`https://mp.csdn.net/mp_blog/manage/column/columnManage/{id}`

### Step 1：进入专栏管理列表

```javascript
// 工具：browser_navigate
await page.goto('https://mp.csdn.net/mp_blog/manage/column/allColumnList');
await page.waitForTimeout(2000);
```

验收：页面标题为 "专栏管理-CSDN创作中心"，可见现有专栏列表

### Step 2：点击「新建」

```javascript
// 工具：browser_click — 选择器 a:has-text("新建")
await page.locator('a:has-text("新建")').click();
await page.waitForTimeout(2000);
```

验收：页面显示新建表单（专栏名称/简介/配图/付费开关/提交）

### Step 3：填专栏名称

```javascript
// 填名称
await page.locator('input[placeholder*="请输入分类专栏名称"]').fill('专栏名称');
await page.waitForTimeout(300);

// 填简介（150 字上限）
await page.locator('textarea[placeholder*="例，以实战为线索"]').fill('专栏简介...');
await page.waitForTimeout(300);
```

### Step 4：提交

```javascript
// 工具：browser_click
await page.locator('button:has-text("提交")').click();
await page.waitForTimeout(2000);
```

验收：提交后跳转回专栏列表，新专栏出现，"全部"计数 +1

### Step 5：查看文章列表 → 专栏验证

创建后专栏会出现在博客主页（`https://blog.csdn.net/{账号}`）的专用栏目区。

```javascript
// 验证专栏可见
await page.goto('https://blog.csdn.net/deepseek23');
const columns = document.querySelectorAll('.special-column-name');
// 应能看到新专栏名称
```

### ⚠️ 文章归入专栏

CSDN 有两种编辑器，归入专栏的流程不同：

**新编辑器（富文本）`/mp_blog/creation/editor/{articleId}`**

1. 打开文章编辑器
2. 右侧栏找到「分类专栏」→ 点击「新建分类专栏」按钮
3. 弹出列表面板中选择已有专栏（可多选，上限 3 个）
4. 点击「发布博客」重新发布保存

```javascript
// 展开专栏选择器
await page.locator('button:has-text("新建分类专栏")').click();
await page.waitForTimeout(500);
// 选择专栏
await page.locator('text="MCP 协议实战"').click();
await page.waitForTimeout(500);
// 保存
await page.locator('button:has-text("发布博客")').click();
```

**旧编辑器（MD）`editor.csdn.net/md/?articleId={id}`**

1. 打开文章编辑器
2. 点击底部的「发布文章」按钮
3. 在弹出的发布对话框中找到「分类专栏」区域
4. 从列表面板中选择已有专栏
5. 点击对话框底部的「发布文章」按钮保存

```javascript
// 打开发布对话框
await page.locator('button.btn-publish').click();
await page.waitForTimeout(1000);
// 选择专栏（对话框内文本选择器可用）
await page.locator('text="MCP 协议实战"').click();
await page.waitForTimeout(500);
// 对话框内的「发布文章」按钮在 micro-app 中，用 CSS 类名定位最后一个按钮
await page.locator('.el-dialog__footer button:last-of-type').click();
```

> ⚠️ 旧编辑器的对话框按钮在 micro-app 沙箱中，部分选择器可能不直接命中。如有条件切到新编辑器操作。

## §2 专栏管理（列表现有操作）

## §2 坐标总表

| # | 元素 | 选择器 | 编辑器 | 状态 |
|---|------|--------|--------|------|
| 1 | 专栏管理列表页 | `https://mp.csdn.net/mp_blog/manage/column/allColumnList` | — | ✅ 有效 |
| 2 | 新建按钮 | `a:has-text("新建")` | — | ✅ 有效 |
| 3 | 专栏名称输入框 | `input[placeholder*="请输入分类专栏名称"]` | — | ✅ 有效 |
| 4 | 专栏简介输入框 | `textarea` 新建表单中（150 字限制） | — | ✅ 有效 |
| 5 | 配图上传区域 | 120x120 上传区 | — | 待测 |
| 6 | 付费专栏开关 | `.el-switch` | — | ✅ 有效（默认关） |
| 7 | 提交按钮 | `button:has-text("提交")` | — | ✅ 有效 |
| 8 | 返回链接 | `a:has-text("返回分类专栏")` | — | ✅ 有效 |
| 9 | 专栏管理链接（列表页） | `link "管理"` | — | ✅ 有效 |
| 10 | 专栏编辑链接（列表页） | `link "编辑"` | — | ✅ 有效 |
| 11 | 专栏列表中的名称 | `.special-column-name` | — | ✅ 有效 |
| 12 | 专栏篇数 | `.special-column-num` | — | ✅ 有效 |
| 13 | 专栏状态 | 审核未通过 / 回收站 tab | — | ✅ 有效 |
| 14 | 展开专栏选择器 | `button:has-text("新建分类专栏")` | 新编辑器 ✅ | ✅ 有效 |
| 15 | 选择专栏名称 | `text="专栏名称"` | 新编辑器 ✅ | ✅ 有效 |
| 16 | 发布博客（保存） | `button:has-text("发布博客")` | 新编辑器 ✅ | ✅ 有效 |
| 17 | 打开发布对话框 | `button.btn-publish` | 旧 MD ✅ | ✅ 有效 |
| 18 | 发布对话框确认按钮 | `.el-dialog__footer button:last-of-type` | 旧 MD ✅ | ⚠️ micro-app 沙箱内 |

## §3 已知坑

| 坑 | 现象 | 原因/修复 |
|----|------|----------|
| ⚠️ **columnAdd 直接访问 404** | 直接 browser_navigate 到 columnAdd 页面白屏 404 | **必须从管理页点击「新建」链接进入**（跨子域名 cookie 问题） |
| ⚠️ **columnManage 无批量添加** | columnManage 页面的「批量操作」不是添加文章 | columnManage 只用于管理已有文章（排序/删除），添加文章必须通过文章编辑器 |
| ⚠️ **beforeunload 弹窗** | 在已发布文章的编辑器中操作时会弹出"离开此页面？"确认框 | 每次点击前先 `browser_handle_dialog({accept: true})` 处理；发布后也会触发一次，需立即 accept |
| ⚠️ **micro-app 沙箱** | 旧 MD 编辑器的发布对话框按钮在 micro-app 内部，普通 CSS 选择器可能不命中 | 用 `.el-dialog__footer button:last-of-type` 或 evaluate 遍历按钮按文本匹配 |
| ⚠️ **文章数不即时更新** | 发布成功后专栏文章数可能仍显示旧数字 | 审核通过后才会更新计数，无需重试 |
| ⚠️ **两种编辑器 URL 不同** | 部分文章在新编辑器（`/mp_blog/creation/editor/{id}`），部分在旧 MD（`editor.csdn.net/md/?articleId={id}`） | 旧文章用 MD 编辑器，新文章用富文本编辑器。注意选择器差异 |
| ⚠️ **发布会触发审核** | 重新发布已发布文章会进入"发布成功！正在审核中" | 不影响文章在线状态和专栏归属；审核期间文章仍在线上 |
| 专栏名双击编辑 | 在列表页双击专栏名可直接改名 | 不需要用表单修改，直接双击 |
| "#" 子分类 | 名称以 "#" + 空格 开头显示为二级分类 | 用于层级分类 |

## §4 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| v1.1 | 2026-07-05 | 修正文章归入专栏流程（废弃方案B，补充新旧编辑器双流程）；更新坐标表 14-18；新增批量归类步骤与已知坑（beforeunload、micro-app 沙箱、两种编辑器、审核状态） |
| v1.0 | 2026-07-04 | 初始版：新建专栏流程 + 头部账号策略 + 坐标表 |


---

## 收尾核验（强制末步）

- 回看核心规则①（`~/.claude/CLAUDE.md` 永久原则第一条）：平台技术细节（DOM/API/坐标/SOP/已知问题）只进本技能文件，不进内置记忆；本次修正与复盘已直接编入本 SKILL.md，未写多余记忆文件。
- 反馈即修技能——若本次暴露新堵塞点/选择器/绕过方案，当场写入对应章节（留版本号），不依赖记忆回看。
