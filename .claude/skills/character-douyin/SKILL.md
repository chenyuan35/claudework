---
name: character-douyin
description: 全自动管线：项目类型自动检测 → 视频录制/导出 → 上传发布（含抖音内置卡点 BGM）
version: 4.1
platform: 抖音创作者平台（creator.douyin.com）
mode: 全自动（需用户预登录浏览器，其余全自动执行）
browser: Playwright Extension (mcp__playwright__*)
entry: `/character-douyin [项目路径]` — 省略路径则自动检测 gsap-character-template
related: douyin-image-ops（抖音图文号管线：内容选题 → 图片生成 → 发布）
---

# 角色动画 -> 抖音发布技能 v4.1（全自动管线）

> ⚡ 此技能是 **[douyin-viral-video](../douyin-viral-video/SKILL.md) 融合管线子模块**。
> 如需端到端爆款视频（选题门控→AI生成→上传→质量复查），请用 `/douyin-viral-video`。

> 一次调用，全链路自动执行：检测项目 -> 录制/导出 -> 上传发布（含抖音内置卡点 BGM）

## 管线总览

```
项目路径参数 / 自动检测
  |
  +- 检测项目类型
  |    +- gsap-character-template -> npm run export:video（GSAP 视频导出）
  |    +- 其他（含 arcade-fight/pixel-fight）-> Vite dev server -> 浏览器录制 WebM
  |
  +- Playwright Extension 自动上传发布
  |    +- 导航抖音 -> 检查登录 -> 高清发布
  |    +- 拖放上传 -> 等转码完成
  |    +- AI封面首张 -> 填标题 -> 填简介
  |    +- 添加音乐 -> 卡点 -> 第一首 -> 使用（抖音内置音乐，非 ffmpeg 混音）
  |    +- 发布 -> 确认跳转
  |
  +- 清理本地视频
```

## 前提条件

- 抖音浏览器登录有效（cookie 持久化）
- Playwright Extension (mcp__playwright__*) 连接正常

## 核心变更（v3 -> v4.1）

- **[已移除]** ffmpeg 预混合 BGM 阶段已彻底删除。视频不预加音频音轨。
- **[抖音内置音乐]** 上传后在发布页通过「添加音乐」-> 卡点 -> 第一首，使用抖音平台内置音乐。
- **[纯视频上传]** 上传的是无音轨的纯视频（录制或导出的原始视频），音频由抖音平台添加。

---

## 执行流程（全自动，逐步骤执行不需要问用户）

### Phase 0：检测项目

1. 检查传入的 `args` 参数：如果有路径且目录存在，使用该路径
2. 无路径则检查 `C:\Users\59314\claudework\gsap-character-template\` 是否存在
3. 根据目录特征判断项目类型：
   - 有 `package.json` + `"gsap"` 依赖 -> GSAP 类型（走 Phase 1A）
   - 有 `src/engine/` + `src/project/` -> arcade-fight 类 Canvas 引擎项目（走 Phase 1B）
   - 有 `pixel-fight` 特征 -> 像素大战纯 Canvas 项目（走 Phase 1B）
   - 其他 -> 走 Phase 1B（执行通用 Canvas 录制流程）

### Phase 1A -- GSAP 导出（自动执行）

```bash
# 确保 dev server 运行 -> 导出视频
cd <项目路径>
npm run export:video
```

输出：`<项目路径>/exports/animation.mp4`

### Phase 1B -- Canvas 录制 + 转码（自动执行）

1. 检查 `index.html` 是否基于 Vite / 纯静态
2. 启动预览（Vite 用 launch.json，纯静态用 Python http.server）
3. 浏览器导航到页面，检查 Canvas 和控制按钮
4. 检查录制按钮是否存在：
   - 有 `#record` 按钮 -> 点击录制，等 duration+2s 后检查下载
   - 无录制按钮 -> 用 `captureStream + MediaRecorder` JS 注入录制
5. 获取下载的 WebM 文件（从 downloads 移过来或用 JS 提取）
6. 关闭预览服务器

### Phase 1C -- 转码统一（仅格式转换，不加音频）

```bash
# WebM -> MP4（h264，纯视频，不加音频流）
ffmpeg -i input.webm -c:v libx264 -crf 28 -preset fast -pix_fmt yuv420p -an <项目路径>/exports/animation.mp4
```

> 注意：使用 `-an` 确保不添加任何音频流。音轨在抖音发布页通过「添加音乐」添加。

### Phase 2 -- [已删除] 不再需要 ffmpeg 预混合 BGM

> 视频上传时不预加音频。BGM 全部在抖音发布页通过内置音乐库添加。

### Phase 3 -- Playwright Extension 自动发布（防封版）

> 防封铁律：每步之间必须有随机延迟（1-3s），总流程 >= 45s。
> 禁止 browser_evaluate 点元素；禁止 browser_drop 上传；禁止 browser_fill_form。
> 全部改用：hover->click 链、browser_file_upload、browser_type slowly:true。

#### 3.1 导航 -> 检查登录

```
browser_navigate("https://creator.douyin.com")
browser_wait_for(time=3)                     // 等页面完全加载
browser_snapshot() -> 检查是否有头像/昵称
// 如未登录 -> 向用户报告 cookie 失效，不继续
if not logged_in -> abort
browser_wait_for(time=2)                     // 人类会停顿看一下页面
```

#### 3.2 点击「高清发布」

```
browser_hover(button[class*="douyin-creator-master-button"])
browser_wait_for(time=0.5-1.2)              // 鼠标悬停后再点
browser_click(button[class*="douyin-creator-master-button"])
browser_wait_for(time=2-4)                  // 等页面跳转/弹窗
```

#### 3.3 处理草稿弹窗（如有）

```
browser_snapshot() -> 检测 text=放弃
// 有弹窗才点
if found:
  browser_hover(button:has-text("放弃"))
  browser_wait_for(time=0.3-0.8)
  browser_click(button:has-text("放弃"))
  browser_wait_for(time=2-3)
```

#### 3.4 上传视频

> 不用 browser_drop（非人类操作）。改用：点击上传区域 -> 文件选择器。

```
browser_click([class*="container-drag"])
browser_wait_for(time=1-2)
browser_file_upload(paths=["<项目路径>/exports/animation.mp4"])
```

**等待转码（长等待，不可跳过）：**

```
for attempt in 1..30:
  browser_wait_for(time=3)
  // 每轮检查前，做一个小幅滚动，模拟人类刷页面
  browser_evaluate(() => { window.scrollBy(0, 30); })
  // 检查标题输入框出现 = 转码完成
  snapshot = browser_snapshot()
  if "作品标题" in snapshot -> break
  if attempt % 5 == 0:
    // 每隔 5 轮做一次大幅滚动
    browser_evaluate(() => { window.scrollBy(0, -150); })
```

转码完成后，browser_wait_for(time=2-4) 再继续（人类会停顿检查画面）。

#### 3.5 选封面

> 禁止 browser_evaluate 直接点元素。改用 browser_click + 合理选择器。

```
// AI 推荐封面区域，点击第一张
browser_wait_for(time=1-3)
browser_click([class*="recommendCoverContainer"] > :first-child img)
browser_wait_for(time=1-2)
// 点击确定
browser_hover(button:has-text("确定"))
browser_wait_for(time=0.5-1)
browser_click(button:has-text("确定"))
browser_wait_for(time=1-2)
```

#### 3.6 填标题 -- 逐字输入

> 用 browser_type slow:true 模拟逐字打字，禁止 fill_form。

```
// 先点击标题框
browser_click(input[placeholder*="作品标题"])
browser_wait_for(time=0.3-0.7)
// 逐字输入（工具支持 slowly 参数）
browser_type({
  target: "input[placeholder*='作品标题']",
  text: "自动生成的中文标题（<=30字）",
  slowly: true
})
browser_wait_for(time=1-2)
```

**标题规则：** 概括项目内容，<=30 字，不包含"测试""草稿"等词。

#### 3.7 填简介

```
browser_click(div[contenteditable="true"][data-placeholder*="简介"])
browser_wait_for(time=0.5-1)
browser_type({
  target: "div[contenteditable='true'][data-placeholder*='简介']",
  text: "简介文本 #话题1 #话题2",
  slowly: true
})
browser_wait_for(time=1-2)
```

话题：点击推荐话题标签中的相关标签（非强制）。要点的话先 hover 再 click。

#### 3.8 添加音乐 -- 抖音内置卡点 BGM（唯一音频源）

> **重要变更（v4.1）：** 视频本身不预加音频音轨。
> 在此步骤通过抖音发布页的「添加音乐」-> 卡点 -> 第一首，添加抖音平台内置音乐。
> 这是整条管线中 唯一 给视频添加音频的步骤。

```
// 点击「添加音乐」按钮
browser_click([class*="preview-button"]:has-text("添加音乐"))
browser_wait_for(time=2-3)                  // 等面板弹出

// 切换到「卡点」tab
browser_click(text=卡点)
browser_wait_for(time=1-2)                  // 等列表加载

// 选第一首
browser_click([class*="card-wrapper"]:first-child)
browser_wait_for(time=0.5-1.5)

// 点击使用/确认按钮
browser_click([class*="apply-btn"])
browser_wait_for(time=1-2)

// 验证音乐已添加：检查页面是否出现音乐名称
browser_snapshot()
// 成功添加后，页面底部「添加音乐」按钮区域会显示已选歌曲名
```

> 注意：抖音面板原文说明「仅影响作品底部音乐信息显示,不影响作品声音」，
> 但对于无音轨视频，这里添加的音乐就是实际播放的音频。

#### 3.9 发布前最终检查

```
browser_snapshot()
// 人类特征：发布前滚动预览一遍
browser_evaluate(() => { window.scrollBy(0, 200); })
browser_wait_for(time=1-2)
browser_evaluate(() => { window.scrollBy(0, -200); })
browser_wait_for(time=1-2)
```

#### 3.10 发布

```
browser_hover(button:has-text("发布"))
browser_wait_for(time=0.8-2)               // 悬停犹豫
browser_click(button:has-text("发布"))
// 注意：可能有多个「发布」按钮，不要用 nth=1
// 用上下文定位：不在上传区的发布按钮
```

#### 3.11 确认结果

```
browser_wait_for(time=3-5)                  // 等跳转
browser_snapshot()
// 检测 URL 跳转到 /content/manage 或 toast「发布成功」
if published: 成功
else: 报告错误，不重试
```

### Phase 4 -- 清理

```bash
rm -f <项目路径>/exports/animation.mp4
```

> 注意：v4.1 管线只产出 animation.mp4；final.mp4 / bgm_temp.wav 是旧版 ffmpeg 混音管线产物，已不再生成。

---

## 关键选择器（动态 hash 类名必须模糊匹配）

| 操作 | 选择器 |
|------|--------|
| 高清发布按钮 | `button[class*="douyin-creator-master-button"]` |
| 拖放上传区域 | `[class*="container-drag"]` |
| 标题输入 | `input[placeholder*="作品标题"]` |
| 简介编辑 | `div[contenteditable="true"][data-placeholder*="简介"]` |
| AI 封面首张 | `browser_click` → `[class*="recommendCoverContainer"] > :first-child img`（⚠️ 铁律：不用 evaluate 点击） |
| 封面确认 | `button:has-text("确定")` |
| 添加音乐 | `[class*="preview-button"]:has-text("添加音乐")` |
| 卡点 tab | `text=卡点` |
| 歌单第一首 | `browser_click` → `[class*="card-wrapper"]:first-child`（同上，不用 evaluate） |
| 使用按钮 | `browser_click` → `[class*="apply-btn"]`（同上，不用 evaluate） |
| 发布按钮 | `button:has-text("发布")` |

## 常见问题

### Q: 视频没有音轨，是否需要加音轨才能上传？
不需要。抖音平台接受无音轨视频。音轨完全在平台上通过「添加音乐」添加。

### Q: 「添加音乐」不影响作品声音，那加来干嘛？
该提示针对已有音轨的视频。对于无音轨视频，添加的音乐即为实际播放音频。官方提示的意思是它不会覆盖已有的视频原声。

---

## 反馈经验（AutoMemory 迁移 2026-07-03）

以下内容从 AutoMemory feedback 文件搬入技能，作为永久约束。源文件可删除（见迁移表）。

### feedback_no_zhichang_in_animation → 核心红线

**规则**：动画/像素项目（含 gsap-character-template、arcade-fight、pixel-fight 及抖音发布）中，**严格禁止使用"职场"相关文字、标签、描述**。

**Why:** 用户强烈纠正——"谁让你加职场的""离了职场会死吗""不要加入职场"。动画/像素内容是游戏/视觉类，跟职场毫无关系。

**如何应用：**
- 给动画/像素项目写代码、SVG、精灵图文字、标题、简介、标签时，聚焦游戏类型/视觉风格/内容趣味本身
- 精灵图的像素文字**只使用英文**（因 FONT 字库只支持 A-Z/0-9/?）
- 即使平台推荐话题（如抖音话题标签推荐）中有职场相关也不要点
- 标题/简介示例聚焦：游戏角色、视觉技术、动作设计、对战玩法 — 不涉及任何现实工作、职业成长、办公室话题
- 违规检查：每次发布前快照检查标题/简介是否含"职场""工作""上班""办公室""老板""同事"等词

**迁移状态**：feedback_no_zhichang_in_animation.md → 本节，feedback 可删
