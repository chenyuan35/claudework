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

管道自动完成 14 个阶段：check_dashboard → find_trending → select_topic → write_article → validate_article → generate_inject → prepare_home → open_editor → inject_content → insert_images → set_cover → publish_gate → schedule_publish → verify_submission

### reasoning 阶段处理

当管道输出 `{"type": "reasoning", "stage": "xxx"}` 时：

1. 读取 `runtime/_task.json` 获取 prompt 与 context（含 `articleHistory`）
2. 按 prompt 使用工具执行（搜索/浏览器/推理）
3. 将结构化结果写入 JSON 文件（**必须含 `status` 与 `taskToken`**）
4. 调用 `--complete` 推进：
   ```bash
   python scripts/run_baijiahao_publish.py --complete --stage <stage> --result <result_file>
   ```

### browser 阶段处理

当管道输出 `{"type": "browser", "stage": "xxx"}` 时：

1. 读取 `runtime/_task.json`，按 `operations` 数组顺序执行每个操作
2. 所有操作使用 `mcp__playwright__browser_*` 工具
3. **最后一个操作**已合并 `status/pass + taskToken`，将其完整写入 JSON 文件
4. 调用 `--complete` 推进

> 脚本侧约定：每个 `sourceFile` 脚本在 return 前把结果写入 `sessionStorage.bjh_stage_result`；管道末尾 verify 合并 token。执行者不要删改 operations 顺序。

### 错误处理

```bash
python scripts/run_baijiahao_publish.py --fail --stage <失败阶段> --error "<错误描述>"
```

连续 2 次同阶段失败 → 硬熔断，报告用户。

---

## 选题策略（CTR 优先）

账号弱点击率（约 0.05%），选题必须以点击为第一优先级。

| 规则 | 内容 |
|------|------|
| 历史轮换 | 读 `runtime/article_history.json` 最近 5 篇；排除最近 2 篇已用结构 |
| 结构池 | 清单体 > 踩坑叙事 > 实验报告 |
| 领域切换 | 连续 3 篇同 domain 必须切换；池=健康养生/居家省钱/消费决策/家庭生活 |
| 标题公式 | 20-26 汉字；含数字 **或** 对立选择 **或** 反常识结论；禁空泛词 |
| 热搜 | 优先 heat 高且能落到「我/我家」第一人称故事的话题 |
| 发布后 | `verify_submission` 成功自动 append 历史（最多 20 条） |

---

## 排版规范（手机端阅读设计）

- **一个句号一个段落**：每段只写一句话，方便碎片化扫读
- **小节标题加粗**：每个小节以一个 `p[data-bjh-role="section-title"]` 开头，用 `<strong>` 加粗
- **🔴 正文段落内禁止加粗**：只有节标题能用 `<strong>`
- **恰好 6 个小节**：与 `insert_ai_images.js` 固定 6 节配图对齐
- **开头两段抓人**：前 2 段 intro 出现具体场景/数字/反常识结论中至少 1 项（目标 2 项）
- **段长上限 80 字符**（含标点；编辑器 `getContent()` 为准）

## 质量门（熔断级——不过不发布）

注入前 Python 预检拦截：

- 汉字总数 ≥2000（CJK 统一表意字符；**写作目标 2500+**）
- 恰好 6 个小节，标题已加粗
- 正文段无 `<strong>`；注入前无图
- 无权威口吻（你应该/你必须/你一定/建议你）
- 无评论区/留言引导
- 多句段落 ≥8 段 → 熔断；≥3 段 → 警告
- **严重 AI 味熔断**：过渡词≥3 或 情绪标签≥2 或 排比≥5

## AI 味检测（警告级；过重升级熔断）

| AI 味类型 | 检测方式 | 与真人写作的区别 |
|-----------|----------|------------------|
| 段落长度过于均匀 | 标准差检测 | 真人写作有长有短 |
| 各小节段落数完全一致 | 模板痕迹检测 | 真人每节内容量不同 |
| AI 过渡词 | 值得注意的是/不可否认/众所周知/综上所述/不可忽视的是/换句话说/毋庸置疑/值得一提的是 | 真人用"不过话说回来""讲真" |
| 情绪标签 | 令人XX的是/让人XX的是/使人XX的是 | 真人靠细节表达情绪 |
| 排比句式密集 | 不仅…更…/既…又…/无论…都…/不但…而且… 每文≥3处 | 机器最爱排比对仗 |

## 封面验证 SOP（必做 — set_cover 阶段必须执行）

封面阶段不可跳过以下三条验证，任一项不通过则 `cover_complete` 禁止回传，必须重新生成封面。

### SOP-1：验证正文是正确文章
向编辑器发 `UE_V2.instants['ueditorInstant0'].getContent()`，检查：
- 内容非空
- 首段包含所选标题中的关键词（≥2 个连续关键词匹配）
- 无「请点击输入图片描述」占位残留

如果为空白或标题关键词不匹配 → **说明页面状态异常（可能跳转到了空白草稿）** → 熔断，回到 `open_editor` 阶段重新打开编辑器，不走 set_cover，不重试封面。

### SOP-2：验证所有正文图片互不相同（跨节去重）
在配图阶段（`insert_ai_images.js`）每条图片插入后和 check_article_gate 正文门中执行：
1. 提取编辑器内所有 `<img>` 的 `src` 列表
2. 对每对 src 做 **全等匹配** + **末尾 60 字符模糊匹配**（同一 CDN 图不同参数前缀）
3. 若有任意一对匹配 → **正文图重复** → 当前 section 的插入必须 throw 重试（insert_ai_images 层），或熔断重跑配图（gate 层）

### SOP-3：验证封面 src 与所有正文图片 src 不同
在 `set_cover.js` 点确定后，封面验证前执行：
1. 从封面元素提取当前封面 `src`
2. 从正文编辑器提取所有 `<img>` 的 `src` 列表
3. 封面 `src` 与每个正文 `src` 比较——若封面 src 模糊匹配任意正文 src（末尾 60 字符相同），或封面 src 为空 → **封面与正文图重复** → 禁止确认，必须重新生成封面

### 失败处理
- SOP-1 不通过 → 熔断回 `open_editor`
- SOP-2 不通过 → 清除全文图片重新跑 insert_images
- SOP-3 不通过 → 清除当前封面重新生成
- 连续 2 次同 SOP 失败 → 硬熔断，报告用户

---

## 发布门（验证门，全部通过才发布）

全部勾选通过才允许点定时发布；任一项失败禁止点击发布。

- [ ] 注入前 Python 预检通过（汉字≥2000/6 节/无权威口吻/无引导话术/AI 味）
- [ ] 注入后 content 门通过，`bjh_content_gate_signature` 已写，status=`content_gate_passed`
- [ ] 插图后：6图互不相同（SOP-2），`bjh_ai_images_complete=1`，status=`images_complete`
- [ ] 封面后：SOP-1（文章正确） + SOP-3（封面≠正文图） + src≥20，`bjh_cover_complete=1`，status=`cover_complete`
- [ ] publish 门通过（AI 声明已勾 + 凭据齐全），status=`publish_gate_passed`
- [ ] 定时跳转 URL 含 clue，`bjh_publish_gate_receipt` 已写，status=`scheduled`
- [ ] 投稿列表见标题+状态，status=`submission_verified`，历史已 append

| 阶段 | 验证方式 | 失败处理 |
|------|----------|----------|
| 注入前 | Python 预检（汉字≥2000/6 节/无权威口吻/无引导话术/AI 味） | 回写作修正全文 |
| 注入后 | check_article_gate.js（content），写入 `bjh_content_gate_signature`，返回 `content_gate_passed` | 清空→修正→重新注入 |
| 插图后 | insert_ai_images.js：每节≥1 图 + **SOP-2（正文图互不重复）**，写 `bjh_ai_images_complete`，返回 `images_complete` | 清空→从插图重来 |
| 封面后 | set_cover.js：src≥20 + **按封面验证 SOP 逐条通过（SOP-1+SOP-2+SOP-3）**，写 `bjh_cover_complete`，返回 `cover_complete` | 按 SOP 失败处理：SOP-1→回 open_editor；SOP-2→清图重跑；SOP-3→重新生成封面 |
| 发布门 | check_article_gate.js（publish）+ 凭据检查，返回 `publish_gate_passed` | 补齐缺步后重跑 |
| 定时后 | publish_timing.js：URL 含 clue + 写 `bjh_publish_gate_receipt`，返回 `scheduled` | 检查弹窗 loading 后重试 |
| 验收 | verify_submission.js：投稿列表见标题+状态，返回 `submission_verified`；写入历史 | 手动检查投稿列表 |

---

## 选择器 / 坐标表

| 步骤 | 工具 | 命令 |
|------|------|------|
| 打开首页 | browser_navigate | `https://baijiahao.baidu.com` |
| 点发布作品 | browser_click | `text=发布作品` |
| 填标题 | browser_type | `[data-bjh-title="true"]` |
| 清编辑器/注入 | browser_evaluate | `UE_V2.instants['ueditorInstant0'].setContent(...)` |
| 正文门/发布门 | browser_evaluate | `scripts/check_article_gate.js` |
| 配图 | browser_evaluate | `scripts/insert_ai_images.js`（图按钮 `#edui28_body` / AI tab `ai-illustration`） |
| 开封面 | browser_click | `text=选择封面` → `text=AI封图` |
| 设封面 | browser_evaluate | `scripts/set_cover.js` |
| 勾 AI 声明 | browser_click | `label:has(.aigc_bjh_status) .cheetah-checkbox` |
| 定时发布 | browser_evaluate | `scripts/publish_timing.js` |
| 投稿验收 | browser_evaluate | `scripts/verify_submission.js` |

| 用途 | 选择器 |
|------|--------|
| 发布作品按钮 | `text=发布作品` |
| 标题栏 | `div[contenteditable="true"]`（`open_editor_ready.js` 会标 `data-bjh-title="true"`） |
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
| 定时发布确认 | `.cheetah-modal button` 文本「定时发布」且无 `img` loading 子元素 |

---

## 约束条件

- **不能** `browser_navigate` 直达 `/builder/rc/edit` → 内容丢失。必须走"发布作品"按钮 SPA 跳转。
- **封面确定按钮只点当前 tabpane 内**：set_cover.js 用 `.cheetah-tabs-tabpane-active` 限定。
- **prompt textarea 是 React 受控组件** → 脚本用 `nativeSetter` 赋值。
- **封面/配图 AI 生成用轮询**：最长 40s，条件满足立即返回，禁止固定长 sleep。
- **配图脚本每一步有固定 sleep 延迟**：点生成按钮后最少等 15s 才检查结果；选图后等 4s 才点确认；确认后等 8s 才验证。固定 sleep 防止点击过快。
- **UEditor 剥离 data-\***：注入后 `<p>` 内唯一 `<strong>` 即节标题。
- **定时发布弹窗确认按钮有 loading**：须等 textContent 为「定时发布」且无 `img` 子元素再点。
- **段落长度质量门（≥81 字拦截）以 editor.getContent() 输出为准**。
- **阶段 status 字符串必须与 pipeline expected_status 完全一致**（如 `cover_complete`/`scheduled`/`images_complete`），否则 `--complete` 熔断。
- **浏览器脚本 return 前必须 `sessionStorage.setItem('bjh_stage_result', JSON.stringify(result))`**，否则 verify 合并丢 status。
- **🔴 封面验证 SOP 硬性执行（2026-07-27 新增）**：set_cover.js 自身必须同时完成 SOP-1（编辑器正文非空验证）、SOP-2（正文图互不重复）和 SOP-3（封面 src 不与正文图重复）。任一项不通过 → throw 错误，`cover_complete` 禁止被写入。SOP-1 失败熔断回 `open_editor`；SOP-2 失败清图重跑 insert_images；SOP-3 失败从封面重新生成重试。
- **🔴 图片去重铁律（2026-07-27 新增）**：insert_ai_images.js 每条插入后必须全编辑器 src 去重（末尾 60 字符模糊匹配），重复立即 throw → 外层 retry 重跑。check_article_gate.js 正文门和发布门均设图片去重闸，任何重复图直接熔断。

## 效率约定

- 配图/封面生成等待：条件轮询为主（最长 40s），辅以固定 sleep 防点击过快（生成15s/选图4s/确认8s）
- 编辑器复用：已在 `/builder/rc/edit` 则跳过首页跳转
- 已有节图：`sectionImgCount>=1` 直接 skip
- 封面 prompt：标题 +「高对比封面，生活场景情绪瞬间，竖版构图，无文字无水印」
- 配图 prompt：节标题 + 节末 80 字 +「手机端横图，写实生活场景，自然光，无文字水印」

## 复盘

按 CLAUDE.md 技能修复标准流程执行。
