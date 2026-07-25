---
name: toutiao-article
description: 今日头条(头条号)全品类生活攻略文章自动定时发布。每日2篇，Agens配图，排版硬闸。v8.0
exec_mode: strict_linear
---

# 今日头条 · 生活攻略类文章定时发布（v8.0 — 模块化无人值守版）

## 全局原则

- **读者视角第一**：读者刷头条是来找答案的，不是被教育的。标题承诺什么，正文必须兑现。
- **线性执行，不可跳跃**：每 Phase 完成后方可进入下一 Phase。不通过→退回修正。
- **无人值守**：终局错误（登录失效/验证码/封禁/DOM签名变化/双图服务不可用/发布无法确认）才打断用户。其他错误自动重试最多2次。
- **禁止API发布**：全部走 UI 操作（browser_drop、定时弹窗、UI开关）。
- **禁止创建草稿**：正文写入后必须走完定时流。中断时先清空标题、正文、图片再离开。
- **禁止刷新发布页**：正文写入后不得刷新。定时弹窗问题→关闭后原地重试。
- **所有阈值/选择器/配置在 config/*.yaml 中，SKILL.md 只编排不存数字。**
- **技能修复按 CLAUDE.md 技能修复标准流程执行。**

## Pipeline 概述

```
Phase 0 数据采集        → collect_metrics.py
Phase 1 选题评分        → score_topics.py
Phase 2 内容生成与本地硬闸 → validate_article.py
Phase 3 写入编辑器       → editor.js + 二次核验
Phase 4 配图生成/上传    → generate_images.py → validate_images.js
Phase 5 开关/位置/封面/定时 → publish.js
Phase 6 发布后列表验证   → verify_publish.js
Phase 7 状态落盘/清理    → state.py
```

## 统一入口（唯一执行方式）

先在技能目录执行守卫，然后只调用 `scripts/run_pipeline.py`。禁止直接调用单个模块：

```bash
python ../tools/run_skill.py --check toutiao-article
```

```bash
python scripts/run_pipeline.py --recovery
```

```bash
python scripts/run_pipeline.py
```

每个 Phase 的 JSON 输入统一通过 `--input` 或 stdin 传入。Phase 2/3 的输入对象必须包含 `title` 和 `html`。浏览器 Phase 0/3/4/5/6 生成 `runtime/_browser_task.json`；严格按其中的 `code_file`、`image_paths`、`drop_target` 执行，然后把浏览器结果保存为 JSON 并用 `--complete N --input result.json` 回传。服务端 Phase 1/2/7 直接执行，禁止调用 `--complete`。Phase 5 只有返回 `publishClicked=true` 才可 complete；Phase 6 只有返回 `verified=true` 才可 complete。

任务完成后执行：

```bash
python ../tools/run_skill.py --post-check toutiao-article --task-id <id>
```

`run_pipeline.py` 自动读取 `config/*.yaml`，写入 `runtime/_config.json`。当前文章的正文与元数据写入 `runtime/_article_context.json`，`state.json` 只保存轻量状态。

## 账户画像（账号方向固定，热点仅匹配加分）

| 属性 | 值 |
|------|-----|
| 账号名称 | 实用生活攻略馆 |
| 受众 | 男性和女性都覆盖，41岁以上为核心 |
| 语言 | 直白、短句、少行话 |
| 配比 | 10篇核心+3篇相邻+1篇实验/热点（滚动7天14篇） |

## 每日执行流程

### Phase 0：数据采集

1. 导航到作品管理列表，采集最近20篇标题（去重用）。
2. 采集昨日发布文章数据：展现量/阅读量/点击率/阅读完成率/平均阅读时长/点赞/评论/收藏/分享/新增粉丝/粉丝净增/流量来源。没有对应字段写 `null`，不编造。
3. 计算：ctr、interaction_rate、follow_conversion、completion_score、retention_score。
4. 方向排名按 follow_conversion → completion_score → ctr → interaction_rate → 阅读量。
5. 写入 runtime/metrics.json。

### Phase 1：选题评分

1. 生成候选选题，按以下维度100分评分：受众匹配(25) + 历史数据(25) + 实用价值(20) + 系列连续性(15) + 时效/搜索(10) + 来源可靠(5)。
2. 热点综合分达到配置阈值、提供 `hot_age_days` 或可解析的 `hot_published_at`、发布时间未过期、且 `content_pillar` / `direction` / `subdirection` 精确属于账号方向时，附加最多5分；缺少时效证据或不符合账号方向均不加分，热点不能覆盖主评分。
3. 读取 history.json 最后一篇的 `hook_id`，候选中相同钩子全部排除；连续两篇不得使用同一钩子。
4. 低于配置 `score_min` 的选题不写。
5. 生成5个标题候选，自动评分选最高分：正文一致(30) + 价值明确(20) + 具体清楚(15) + 受众匹配(15) + 好奇不夸张(10) + 与最近20篇差异(10)。
6. 标题硬闸：2-30字，不得标题党，不得虚假数字。保存采用标题及选题元数据到 `runtime/_article_context.json`。
7. 确定文章转粉字段：series_id、content_pillar、target_reader、core_problem、reader_gain、next_topic。

**Phase 1 自检**：候选选题≥70分 ✅ | 标题评分通过 ✅ | 转粉字段完整 ✅ | 与最近20篇无重复 ✅

### Phase 2：内容生成与本地硬闸

1. 根据选题生成正文 HTML。
2. **生成要求**：正文至少2000汉字，推荐2000-2400汉字。禁止先写短稿再补写。**生成提示词中不出现"最低1500"**。
3. **段落规则**：55-80个有效文字段（`<p>`），每段20-60汉字。按 。！？ 换段。至少80%的普通段只有1句。任一段不得超过2句。空段=0，纯标点段=0。连续纯正文段不超过10段。
4. 正文包含5-8个语义区块，用小标题/图片/总结承接。**每个小标题必须用 `<strong>` 包裹**（如 `<p><strong>第一步做什么</strong></p>`），禁止使用纯文字段落当标题。小标题字符数2-30字，不加句尾标点。
5. **本地硬闸**：`run_pipeline.py` 的 `phase2_generate()` 内部调用 ArticleValidator；禁止绕过统一入口。通过标准：
   - chinese_count ≥ 1500 | paragraph_count 55-80 | empty_paras=0 | punct_only=0
   - markdown_leaks=0 | over_60_paras=0 | max_sentences≤2 | single_sentence_ratio≥0.80
   - forbidden_cta=0 | forbidden_writing=0 | heading_count 4-8 | max_consecutive_text_paras≤10
6. 若 `passed=false` → 修正后重新验证。
7. 若 chinese_count < 1500 → 不允许补结尾，使用原选题和原大纲完整重生成一次（生成要求提高到2200汉字）。第二次仍<1500 → 标记 content_failed，不写入编辑器，进入失败处理。
8. 写入 `runtime/_article_context.json`（title, html, article_hash 与选题元数据），state.json 推进到 phase=3。

**验证硬闸**：只有 `passed=true` 才能进入 Phase 3。

### Phase 3：写入编辑器

1. 确保发布页已打开且页面签名通过（`selectors.yaml` 的 page_texts_check 全部匹配，按钮顺序正确）。
2. `page.evaluate` 一次性写入 `.ProseMirror.innerHTML = html`，dispatch input 事件。
3. **二次核验**：从编辑器读取 innerText，按CJK正则计汉字；同时与 Phase 2 本地汉字数比较。
4. 编辑器汉字数低于硬闸或与本地结果差异超过配置 `chinese_editor_diff_pct` → 当前浏览器任务失败；只允许重新写入同一份HTML一次，不重新生成正文。
5. 写入标题：`page.locator('textarea[placeholder*="请输入文章标题"]').fill(title)`。核验写入值与目标标题完全一致，长度2-30字。
6. 更新 state.json（phase=3）。

### Phase 4：配图生成、上传、relocate

1. `phase4_images()` 从 `runtime/_article_context.json` 读取真实标题和HTML，提取3段英文prompt并直接调用配图模块；禁止手工再次调用单脚本。
2. 配图模块生成3张图片（Agens主→sese-ai回退），提示词采用写实摄影风（realistic/photorealistic documentary style）。每张必须通过 HTTP 状态、图片 Content-Type、Pillow 解码和最小尺寸核验后才原子写入标题hash目录。恢复时复用已通过核验的图片。
3. 任意图片生成失败（两个服务都失败）→ 标记 image_failed，不生成浏览器任务、不发布当前文章。
4. `phase4_images()` 把三张图复制进 Playwright 允许目录并生成一个自包含 `code_file`；执行者只运行该文件，不单独调用 `browser_drop`，不选择光标，不手调图片位置。
5. `code_file` 先把编辑器恢复为 Phase 2 已验证的原始HTML，再在专用空锚点上传三张图；然后只选择以句尾标点结束的完整段落，自动寻找最接近25%/50%/75%的安全位置。位置允许在配置三档内偏移，禁止拆开任何原段落。
6. 同一代码核验：
   - imageBlockCount === 3 | blobCount === 0 | uniqueCdnCount === 3
   - `paragraphIntegrityOk === true`：上传前后的非空文字段落数组逐项完全一致，任何断句、合并、丢字都失败
   - 三档区间 [8%,30%] / [30%,55%] / [55%,85%] 每档≥1，间距≥15%，90%之后无图
   - 最后3个节点无图 | 图前一段以 。！？ 结束
7. 任一项失败 → 同一个 `code_file` 自动恢复原始HTML并重试上传一次；仍失败则停止发布。

### Phase 5：开关、位置、封面、定时

1. **底部开关**：ensureSwitchWithVerify('投放广告赚收益') → ensureSwitchWithVerify('头条首发') → ensureSwitchWithVerify('发布得更多收益') → ensureSwitchWithVerify('个人观点，仅供参考')。**每个开关必须：找到→读取checked→click→读取checked确认。找不到或仍false→throw。**
2. **引用AI**：检测checked，若true则click取消，再次核验为false。
3. **位置**：setPosition(page, '上海')。验证位置显示包含"上海"。
4. **封面**：找到"单图"选项，选中后确认预览非空。
5. **执行前核验清单**：
   - [ ] 标题不为空且与目标一致
   - [ ] 编辑器汉字数≥1500
   - [ ] 图片核验全通过
   - [ ] 底部开关已勾选
   - [ ] 引用AI已取消
   - [ ] 位置已设置（上海）
   - [ ] 封面已设置
6. **定时发布**：点击"定时发布"按钮→弹窗→选日期→选小时→选分钟(0)→核验时间一致→"预览并定时发布"→最终确认。**日期/小时/分钟每个选择必须返回selected=true。最终同时验证日期、小时、分钟。**
7. 页面跳转到 `/graphic/articles`。

### Phase 6：发布后列表验证

1. 确认URL进入作品管理页。
2. 列表中存在精确标题，状态显示定时发布。
3. 定时时间与目标一致。
4. 无法确认时标记 `publish_uncertain` 并停止，禁止继续下一篇。最多核验3次。

### Phase 7：状态落盘和临时文件清理

1. 只有 Phase 6 返回 `verified=true` 并通过 `--complete 6` 写入 `publish_verified=true` 后，Phase 7 才可执行。
2. 以 `operation_key` 检查 history.json；已落盘则从历史记录对账 article_index 和 metrics，禁止重复计数。
3. 新文章先写入带 `operation_key`、`article_index_after` 的 history 提交记录，再幂等更新 state 与 metrics；三个 JSON 均使用临时文件 + `os.replace` 原子替换。
4. metrics.json 的 articles_total 只对新落盘文章递增一次。
5. 删除当前文章上下文和 runtime/images/ 临时图片。
6. 第一篇成功后保留 `article_index=1`，状态转为 idle 并从 Phase 0 开始第二篇；第二篇成功后 state.json 完全重置为 idle。
7. history.json 和 metrics.json 保留。

### 下一篇

重复 Phase 0-7 执行当日第二篇。任一篇未完成 → 停止当天流程，修复后重试。

## 启动恢复

每次启动执行 `python scripts/run_pipeline.py --recovery`：
- `publish_verified=true` → 先执行 Phase 7 幂等落盘；确认 history 已记录且状态清理后，再从 Phase 0 继续下一篇。
- `publish_clicked=true` 但 `publish_verified=false` → 进入作品管理列表核验。3次找不到→标记 publish_uncertain，禁止再点击发布。
- 编辑器有脏内容 → 清除标题/正文/图片，从 Phase 2 重新执行。
- 无脏编辑器 → 从 state.json 最后成功 Phase 继续。

## 终局错误（打断用户）

| 条件 | 处理 |
|------|------|
| 登录失效 / 验证码 / 封禁 | 停止，通知用户 |
| 页面DOM签名变化 | 停止，通知用户 |
| 两个图片服务均不可用 | 停止，通知用户 |
| 发布结果无法确认（3次后） | 标记 publish_uncertain，停止 |
| 其他错误 | 自动重试最多2次，成功继续，失败熔断 |

## 标题评分维度

| 维度 | 分值 | 说明 |
|------|------|------|
| 与正文一致 | 30 | 标题承诺在正文中完整兑现 |
| 价值明确 | 20 | 读者知道读完能得到什么 |
| 具体清楚 | 15 | 不含模糊表达 |
| 受众匹配 | 15 | 目标人群看到会点 |
| 好奇但不夸张 | 10 | 有吸引力但不标题党 |
| 与最近20篇差异 | 10 | 区分度 |

## 选题评分维度

| 维度 | 分值 |
|------|------|
| 受众匹配 | 25 |
| 历史同方向数据 | 25 |
| 实用价值 | 20 |
| 系列连续性/转粉价值 | 15 |
| 时效或搜索需求 | 10 |
| 来源可靠性 | 5 |
| **合计** | **100** |

## 脚本调用与输出约定

所有脚本输入输出统一为JSON格式。失败返回固定 error_code 字段。

| 脚本 | 输入 | 输出 | error_code |
|------|------|------|-----------|
| `scripts/state.py` | -- | `{phase, status, ...}` | STATE_ERROR |
| `scripts/validate_article.py` | stdin/文件路径 | `{passed, failures: [...]}` | VALIDATION_FAILED |
| `scripts/collect_metrics.py` | `--fetch` 或 -- | `{message, ...}` | METRICS_ERROR |
| `scripts/score_topics.py` | stdin JSON | `[{title, score, breakdown}]` | SCORE_ERROR |
| `scripts/generate_images.py` | stdin/file prompts JSON | `{success, fail, results, all_ok}` | IMAGE_GEN_FAILED |
| `scripts/validate_images.js` | page context | `{passed, checks, failures}` | IMAGE_VALIDATION_FAILED |
| `scripts/editor.js` | page context | `{written/cleared/error}` | EDITOR_ERROR |
| `scripts/publish.js` | page context | `{passed, checks, failures}` | PUBLISH_SETUP_FAILED |
| `scripts/verify_publish.js` | page context | `{verified, reason}` | VERIFY_FAILED |

## 启动恢复流程

每一步后的成功/失败跳转：

```
→ state.detect_recovery()
   ├─ "continue_next" → 跳过已发布，直接进入下一篇文章 Phase 0
   ├─ "verify_publish" → 导航到作品管理列表，精确标题搜索
   │   ├─ 找到3次 → 标记publish_verified，继续下一篇
   │   └─ 3次找不到 → 标记publish_uncertain，停止（不重复发布）
   ├─ "clear_and_restart" → 清空编辑器（标题+正文+图片），从Phase 2重做
   └─ "new" → 正常执行 Phase 0
```

## 选择器/坐标表

所有选择器唯一来源：`config/selectors.yaml`。

| 用途 | 工具 | URL / 选择器 |
|------|------|-------------|
| 页面异常取证 | `browser_evaluate` | 当前URL、`.ProseMirror`、图片块与开关状态 |
| 发布页 | `browser_navigate` | `https://mp.toutiao.com/profile_v4/graphic/publish` |
| 作品管理列表 | `browser_navigate` | `https://mp.toutiao.com/profile_v4/manage/content/all` |
| 标题输入框 | `browser_run_code_unsafe` | `textarea[placeholder*="请输入文章标题"]` |
| 正文编辑器 | `browser_run_code_unsafe` | `.ProseMirror` |
| 图片上传定位 | `browser_run_code_unsafe` | `.ProseMirror > p:last-child`（Phase 4 模块每次先恢复为末尾空段） |
| 位置 | `browser_run_code_unsafe` | `.position-cell .edit-label` → `.position-select` → `.byte-select-option` |
| 封面单图 | `browser_run_code_unsafe` | `.byte-radio-wrapper` 含文本"单图" |
| 日期选择 | `browser_run_code_unsafe` | `.day-select` / `.hour-select` / `.minute-select` |
| 定时按钮 | `browser_run_code_unsafe` | `button:has-text("定时发布")` |
| 最终确认 | `browser_run_code_unsafe` | `button.publish-btn:has-text("定时发布")` |

## 真实性规则（强制）

- 不得虚构个人经历、人物、实验结果和金额。
- 数字必须来自可靠来源、页面数据或可复核计算。
- 没有真实案例时使用"常见场景"，不得伪装亲身经历。
- 政策、医疗、健康、金融、安全内容必须读取最新可靠来源。
- 政策内容必须注明适用地区和生效时间。
- 标题承诺必须在正文中完整兑现。
- 禁止洗稿、拼接常识和同义改写。

## 转粉结构（每篇必需）

每篇在选题时确定：
- `series_id`: 同一核心方向形成连续系列
- `content_pillar`: 内容支柱方向
- `target_reader`: 目标读者画像
- `core_problem`: 要解决的核心问题
- `reader_gain`: 读者读完的收获
- `next_topic`: 下一篇将解决的问题

结尾允许自然的开放问题或下一篇预告。**禁止**：求点赞/求关注/求转发/"评论区说说"/"关注我"/人工诱导互动。
