---
name: baijiahao-publish
description: 百家号图文发布。质量门：2000+汉字 / 6张图 / 封面 / AI声明 / 定时发布
---

# 百家号发布

## 质量门（不过不发布，注入前 Python 预检拦截）

1. 纯文本 ≥2000 汉字（仅 CJK，标点/英文/数字不计）
2. 6 个小节（━━━ 标题），每节 ≥7 段，总非标题段 ≥49
3. 每段总字符 ≤80，汉字 ≥40
4. 6 张不同配图（每节 1 张）
5. 封面已设、AI 声明已勾选
6. 无「你应该/你必须/你一定/建议你」等权威口吻
7. 无「评论区聊聊」类引导话术

---

## 主管道（5 阶段顺序固定，无分支，无临场判断）

> 每步完成后立即执行下一步，不穿插 SOP 未规定的 browser_click/evaluate。

### 阶段 1：打开编辑器

1. `browser_navigate` 至 `https://baijiahao.baidu.com`
2. 等待页面加载完成（readyState=complete）
3. 清除覆盖层：evaluate `clearOverlays()`（设 foldContent 的 pointerEvents=none）
4. `browser_click('text=发布作品')`
5. 执行 `scripts/open_editor_ready.js` — 等待标题栏 `div[contenteditable="true"]:visible`（最长 180s）。脚本自检测当前是否已在编辑器页，自动走合适路径
6. 验证：evaluate 确认有可见的 contenteditable div（`getClientRects().length > 0`）

**熔断：** 180s 内标题栏未出现 → 关旧 tab 重新从步骤 1 开始。2 次失败后报告用户。

> **铁律1：** 不等渲染完就操作是所有卡点的根因。open_editor_ready.js 自带 waitForPublishBtn + 180s 超时 + clearOverlays，不要手写替代路径。
> **铁律2：** 不能 browser_navigate 直达 `/builder/rc/edit` → 内容丢失。必须通过点击"发布作品"触发 SPA 跳转。

### 阶段 2：写标题 + 注入正文

**写标题：** `browser_click` 聚焦 `div[contenteditable="true"]` → `browser_type` 写入

**注入前预检（硬性，无例外）：**
写好的 HTML 注入编辑器**之前**，先做两件事：

**① Python 验证**——汉字≥2000、段数≥49、单段≤80、每段汉字≥40：
```python
import re
with open('article.html') as f: html = f.read()
paras = re.findall(r'<p[^>]*>(.*?)</p>', html, re.DOTALL)
text = ''.join(paras).replace('<strong>','').replace('</strong>','')
text = re.sub(r'\s+', '', text)
han = len(re.findall(r'[一-鿿豈-﫿]', text))
assert han >= 2000, f'汉字{han}<2000'
assert len(paras) >= 49, f'段落{len(paras)}<49'
for p in paras:
    p_clean = re.sub(r'<[^>]+>', '', p).strip()
    p_clean = re.sub(r'\s+', '', p_clean)
    assert len(p_clean) <= 80, f'超80字'
    cjk = len(re.findall(r'[一-鿿豈-﫿]', p_clean))
    assert cjk >= 40, f'汉字{cjk}<40'
```
不通过 → 回写作修正全文，**不允许注入后修补**。

**清空编辑器（防累积）：** evaluate `() => { UE_V2.instants["ueditorInstant0"].setContent(''); }`

**注入：** JS 模板字符串（backtick）包裹 HTML → `UE_V2.instants['ueditorInstant0'].setContent()`
```python
with open('article.html') as f: html = f.read()
escaped = html.replace('\\', '\\\\').replace('`', '\\`').replace('${', '\\${')
js = f'() => {{ UE_V2.instants["ueditorInstant0"].setContent(`{escaped}`); }}'
with open('inject.js', 'w') as f: f.write(js)
```
然后 `browser_evaluate` 执行 inject.js。

> **铁律：全文只注入一次。** 闸门不过就重写全文重新注入，不允许在页面上拼接修补。

**注入后验证：** evaluate 设 `sessionStorage.setItem('bjh_gate_stage', 'content')`，然后执行 `scripts/check_article_gate.js`。必须 hardFailures.length===0。

失败处理：清空编辑器（setContent('')）→ 修正全文 → 重新注入 → 重新验证。

### 阶段 3：插 6 张配图

执行 `scripts/insert_ai_images.js` — 逐节用段落原文+写实风格生成并插入 AI 配图，自动清理占位段。脚本内置验证（非1x1像素）。

成功标准：返回 6 个 section，每节 imgs ≥1。

失败处理：清空编辑器 → 修正全文 → 从阶段 2 重新注入 → 重新插图。

### 阶段 4：封面 AI封图

顺序三步，不可合并：

1. `browser_click('text=选择封面')` — **必须 Playwright 原生点击**
2. `browser_click('text=AI封图')` — **必须 Playwright 原生点击**
3. 执行 `scripts/set_cover.js` — 取标题做 prompt → 生成 → 轮询等图片（最长 40s）→ 当前 tabpane 内点"确定" → 验证封面 src 长度 ≥20

**铁律：** 步骤 1、2 禁止改用 evaluate/reactClick/el.click()。

失败处理：开新 tab 从阶段 1 重做。2 次失败后报告用户。

### 阶段 5：AI 声明 + 发布

1. `browser_click` 点 `label:has(.aigc_bjh_status) .cheetah-checkbox`
2. 执行 `scripts/publish_timing.js` — 点"定时发布" → 弹窗确认 → 验证 URL 含 `/builder/rc/clue`

失败处理：手动检查投稿列表。

---

## 发布门（验证门，全部通过才发布）

| 阶段 | 验证方式 | 失败处理 |
|------|----------|----------|
| 注入前 | Python 预检（汉字≥2000/段数≥49/单段≤80/汉字≥40） | 回写作修正全文 |
| 注入后 | check_article_gate.js（编辑器实际渲染） | 清空→修正→重新注入 |
| 插图后 | insert_ai_images.js 内置（每节≥1图，非1x1像素） | 清空→从阶段2重来 |
| 封面后 | set_cover.js 验证（src长度≥20） | 开新tab从阶段4重试 |
| 发布后 | publish_timing.js 验证（URL含clue） | 手动检查投稿列表 |

> 连续 2 次同一步骤失败 → 熔断停止，报告用户。

---

## 选择器

| 用途 | 选择器 |
|------|--------|
| 发布作品按钮 | `text=发布作品` |
| 标题栏 | `div[contenteditable="true"]`（首个可见的） |
| 正文注入 | `UE_V2.instants['ueditorInstant0'].setContent()` |
| 图片插入按钮 | `#edui28_body` → 备用 `[title*="图片"]` |
| AI配图tab | `[data-node-key="ai-illustration"]` |
| 正文生成按钮 | `.FeEditorApp-_65f7660e096d0b20-btn` |
| 正文选图 | 多选择器容错：clickArea → imageWrap → img-item → 1:1 img |
| 正文确认按钮 | `$$('button').find(b => b.textContent === '确认')` |
| 封面选择 | `text=选择封面` |
| AI封图tab | `text=AI封图` |
| 封面确认 | set_cover.js 内找 `.cheetah-tabs-tabpane-active button` 匹配"确定" |
| AI声明checkbox | `label:has(.aigc_bjh_status) .cheetah-checkbox` |
| 定时发布主按钮 | `text=定时发布` |
| 定时发布确认 | `$$('button').find(b => b.textContent === '定时发布')` |

---

## 约束条件（踩过的坑）

- **不能** `browser_navigate` 直达 `/builder/rc/edit` → 内容丢失。必须通过点击"发布作品"触发 SPA 跳转。
- **不能** `el.remove()` 或 `display:none` 操作 React DOM → SPA 崩。关闭弹窗只能用常规手段（取消/X）。
- **封面「确定」按钮只点当前 tabpane 内**：set_cover.js 通过 `.cheetah-tabs-tabpane-active` 限定作用域。
- **prompt textarea 是 React 受控组件** → 脚本用 `nativeSetter`，不直接用 `ta.value =`。
- **封面 AI 生成用轮询不等固定时间**：set_cover.js 内置 40s 轮询。
- **不等渲染完就操作是卡点根因。** 所有关键操作前都有等待 + 验证。

---

## 内容策略

### 标题公式

| 公式 | 参考阅读 |
|------|:--------:|
| 🏆 警告清单式 | 124 |
| ✅ 恐惧+指南 | 110 |
| ❌ 个人故事/平淡通告/冷门话题 | 0-30 |

20-26 字最佳，含 1-2 核心搜索关键词。个人故事/平淡通告/冷门话题一律不写。

### 结构轮换

**查最近记录 → 排除最近 2 篇已用结构 → 按优先级选第一个。**
优先级：清单体(1) → 实验报告(2) → 踩坑叙事(3)

连续 ≥3 篇同一领域（厨房/冰箱/夏季安全），强制切领域。

### 写作约束

- 无「你应该/你必须/你一定/建议你」— 改"我试了/我家是这样"
- 每段有"我/我家"视角，至少一处对话，至少一个具体数字
- 结尾是动作指令或开放提问，不是总结
- 每篇调整一次叙事口吻：清单体密集抛点，踩坑叙事渲染冲突和反转
- 每段 ≤80 总字符，汉字 ≥40
- 每 200-300 汉字一个 ━━━ 小标题
- 每段 2-3 个关键词加粗
- 并列信息强制数字列表
- 总段数公式：前言 4 + 6节×7 + 结尾 3 = 49
- 写完后 Python 预检，不回退不凑数

## 最新发布记录

| 时间 | 标题 | 结构 |
|------|------|:----:|
| 7/24 | 高温天喝水不当也会要命？5个致命误区很多人天天犯 | 清单体 |
| 7/24 | 千万别在车里开空调睡觉（已发） | 踩坑叙事 |
| 7/23 | 手机充电千万别干这5件事 | 清单体 |
| 7/23 | 冰箱剩菜放7天还能吃吗 | 实验报告 |
| 7/23 | 夏天点蚊香送急诊，5个致命驱蚊误区 | 清单体 |
| 7/22 | 三伏天空调开到28度进了医院 | 踩坑叙事 |
| 7/22 | 菜板用完不晾干测了多少菌 | 实验报告 |
| 7/21 | 夏天吃凉菜前不看6条挂了水 | 清单体 |
| 7/20 | 夏天外卖放桌上2小时挂了水 | 踩坑叙事 |
| 7/20 | 三伏天冰箱温度放9个温度计测一周 | 实验报告 |
