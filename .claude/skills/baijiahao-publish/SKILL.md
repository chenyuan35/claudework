---
name: baijiahao-publish
description: 百家号图文发布。全管线：选题→写作→配图→封面→AI声明→定时发布
---

# 百家号发布

## 统一入口（唯一执行方式）

```bash
# 全新启动（删除旧状态，从 check_dashboard 开始）
python scripts/run_baijiahao_publish.py --start

# 恢复上次中断的管道（保留已有状态继续）
python scripts/run_baijiahao_publish.py --resume
```

> **⚠️ 新窗口、新会话必须用 `--start`**。`--resume` 仅用于同一会话中中断后继续。混用会导致浏览器状态不一致。

管道自动完成 15 个阶段：check_dashboard → find_trending → select_topic → write_article → validate_article → generate_inject → prepare_home → open_editor → inject_content → insert_images → set_cover → publish_gate → schedule_publish → verify_submission

### reasoning 阶段处理

当管道输出 `{"type": "reasoning", "stage": "xxx"}` 时：

1. 读取 `runtime/_task.json` 获取 prompt
2. 按 prompt 使用工具执行（搜索/浏览器/推理）
3. 将结构化结果写入 JSON 文件
4. 调用 `--complete` 推进：
   ```bash
   python scripts/run_baijiahao_publish.py --complete --stage <stage> --result <result_file>
   ```

### 快速模式（已有 HTML 文章）

跳过选题写作，从验证阶段开始：

```bash
python scripts/run_baijiahao_publish.py --start --article runtime/article.html --title "标题" --keyword 关键词
```

### browser 阶段处理

当管道输出 `{"type": "browser", "stage": "xxx"}` 时：

1. 读取 `runtime/_task.json`，按 `operations` 数组顺序执行每个操作
2. 所有操作使用 `mcp__playwright__browser_*` 工具
3. 最后一个操作的结构化返回值写入 JSON 文件
4. 调用 `--complete` 推进

### 错误处理

```bash
python scripts/run_baijiahao_publish.py --fail --stage <失败阶段> --error "<错误描述>"
```

连续 2 次同阶段失败 → 硬熔断，报告用户。

---

## 排版规范（手机端阅读设计）

百家号以手机端阅读为主，排版规则如下：

- **一个句号一个段落**：每段只写一句话，方便碎片化扫读
- **小节标题加粗**：每个小节以一个 `p[data-bjh-role="section-title"]` 开头，用 `<strong>` 加粗，便于读者定位和插入配图
- **🔴 正文段落内禁止加粗**：`check_article_gate.js` 通过 `<strong>` 数量判定小节数（要求恰好 = 节标题数）。`article_contract.py` 会在注入前拦截所有正文段内的加粗。只有节标题能使用 `<strong>`，正文段落内一律不得加粗。
- **3-10 个小节**：既保证深度又不拖沓
- **开头两段抓人**：前 100-200 字出现具体场景/数字/反常识结论中的至少 2 个

## 质量门（熔断级——不过不发布）

注入前 Python 预检拦截，以下是硬性门槛：

- 汉字总数 ≥2000（仅计 CJK 统一表意字符，标点/英文/数字不计）
- 3-10 个小节，标题已加粗
- 无「你应该/你必须/你一定/建议你」等权威口吻
- 无「评论区聊聊/欢迎留言/留言告诉」等引导话术
- 无注入前图片

## AI 味检测（警告级——不熔断，提醒修改）

`validate_article` 阶段检查以下 AI 味特征并发出警告，不阻断发布，但会写入报告供人工判断：

| AI 味类型 | 检测方式 | 与真人写作的区别 |
|-----------|----------|------------------|
| 段落长度过于均匀 | 标准差检测 | 真人写作有长有短，机器每段切得一样长 |
| 各小节段落数完全一致 | 模板痕迹检测 | 真人每节内容量不同，机器追求齐整 |
| AI 过渡词 | `{{c8::值得注意的是/不可否认/众所周知/综上所述/不可忽视的是/换句话说/毋庸置疑/值得一提的是}}` | 真人用"不过话说回来""讲真""有意思的是" |
| 情绪标签 | `{{c8::令人XX的是/让人XX的是/使人XX的是}}` | 真人靠细节表达情绪，不替读者贴标签 |
| 排比句式密集 | `{{c8::不仅…更…/既…又…/无论…都…/不但…而且…}}` 每文≥3处 | 机器最爱排比对仗，真人更随意 |

## 发布门（验证门，全部通过才发布）

| 阶段 | 验证方式 | 失败处理 |
|------|----------|----------|
| 注入前 | Python 预检（汉字≥2000/小节标题加粗/无权威口吻/无引导话术） | 回写作修正全文 |
| 注入后 | check_article_gate.js（编辑器实际渲染），写入 `bjh_content_gate_signature` | 清空→修正→重新注入 |
| 插图后 | insert_ai_images.js 内置（每节≥1图，非1x1像素），写入 `bjh_ai_images_complete` | 清空→从阶段2重来 |
| 封面后 | set_cover.js 验证（src长度≥20），写入 `bjh_cover_complete` | 开新tab从阶段4重试 |
| 发布后 | publish_timing.js 验证（URL含clue + `bjh_publish_gate_receipt`），verify_submission.js 确认 `submission_verified` | 手动检查投稿列表 |

---

## 选择器

| 用途 | 选择器 |
|------|--------|
| 发布作品按钮 | `text=发布作品` |
| 标题栏 | `div[contenteditable="true"]`（首个可见的） |
| 正文注入 | `UE_V2.instants['ueditorInstant0'].setContent()` |
| 图片插入按钮 | `#edui28_body`（不通过时换 `[title*="图片"]`） |
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

## 约束条件

- **不能** `browser_navigate` 直达 `/builder/rc/edit` → 内容丢失。必须走"发布作品"按钮 SPA 跳转。
- **封面确定按钮只点当前 tabpane 内**：set_cover.js 用 `.cheetah-tabs-tabpane-active` 限定。
- **prompt textarea 是 React 受控组件** → 脚本用 `nativeSetter` 赋值。
- **封面 AI 生成用轮询**：set_cover.js 内置 40s 轮询。
- **UEditor 剥离 data-* 自定义属性**（data-bjh-role / data-bjh-section）：注入后 editor.getContent() 不包含这些属性。正文已锁定无加粗，注入后 `<p>` 内唯一 `<strong>` 即节标题。
- **定时发布弹窗确认按钮有 loading 状态**：按钮含 `<img>` loading 动效时不可点击。脚本需等待 `.cheetah-modal button` 的 textContent 为"定时发布"且不含 `img` 子元素后再点击。
- **段落长度质量门（≥81字拦截）以 editor.getContent() 输出为准**，不依赖注入源 HTML。UEditor 可能合并/拆分段落或插入额外字符（span/strong 带 data-diagnose-id），导致实际段长与源 HTML 不同。
