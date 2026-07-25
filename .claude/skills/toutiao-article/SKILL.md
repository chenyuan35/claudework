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

所有操作通过 `run_pipeline.py` 编排，**禁止直接调用单个脚本文件**：

```bash
# 查看当前状态
python scripts/run_pipeline.py --status
# 检测恢复状态
python scripts/run_pipeline.py --recovery
# 执行编排（从当前Phase开始）
python scripts/run_pipeline.py
# Phase 0: 传入采集数据
python scripts/run_pipeline.py --phase 0 < scraped_data.json
# Phase 1: 传入候选选题
python scripts/run_pipeline.py --phase 1 < candidates.json
# Phase 2: 验证正文
python scripts/run_pipeline.py --phase 2 --input article.html
# Phase 7: 落盘清理
python scripts/run_pipeline.py --phase 7 < meta.json
```

`run_pipeline.py` 自动读取 `config/*.yaml`，写入 `runtime/_config.json`。
浏览器操作时 JS 从此文件读取选择器和阈值。操作指令写入 `runtime/_browser_task.json`。

## 账户画像（固定执行，不追轮换热点）

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
2. 低于70分的选题不写。
3. 生成5个标题候选，自动评分选最高分：正文一致(30) + 价值明确(20) + 具体清楚(15) + 受众匹配(15) + 好奇不夸张(10) + 与最近20篇差异(10)。
4. 标题硬闸：2-30字，不得标题党，不得虚假数字。保存未采用标题到当前状态文件。
5. 确定文章转粉字段：series_id、content_pillar、target_reader、core_problem、reader_gain、next_topic。
6. 写入选题结果到 runtime/state.json。

**Phase 1 自检**：候选选题≥70分 ✅ | 标题评分通过 ✅ | 转粉字段完整 ✅ | 与最近20篇无重复 ✅

### Phase 2：内容生成与本地硬闸

1. 根据选题生成正文 HTML。
2. **生成要求**：正文至少2000汉字，推荐2000-2400汉字。禁止先写短稿再补写。**生成提示词中不出现"最低1500"**。
3. **段落规则**：55-80个有效文字段（`<p>`），每段20-60汉字。按 。！？ 换段。至少80%的普通段只有1句。任一段不得超过2句。空段=0，纯标点段=0。连续纯正文段不超过10段。
4. 正文包含5-8个语义区块，用小标题/图片/总结承接。
5. **本地硬闸**：`python scripts/validate_article.py` 验证HTML。通过标准：
   - chinese_count ≥ 1500 | paragraph_count 55-80 | empty_paras=0 | punct_only=0
   - markdown_leaks=0 | over_60_paras=0 | max_sentences≤2 | single_sentence_ratio≥0.80
   - forbidden_cta=0 | heading_count 4-8 | max_consecutive_text_paras≤10
6. 若 `passed=false` → 修正后重新验证。
7. 若 chinese_count < 1500 → 不允许补结尾，使用原选题和原大纲完整重生成一次（生成要求提高到2200汉字）。第二次仍<1500 → 标记 content_failed，不写入编辑器，进入失败处理。
8. 写入 runtime/state.json（phase=2, title, article_hash）。

**验证硬闸**：只有 `passed=true` 才能进入 Phase 3。

### Phase 3：写入编辑器

1. 确保发布页已打开且页面签名通过（`selectors.yaml` 的 page_texts_check 全部匹配，按钮顺序正确）。
2. `page.evaluate` 一次性写入 `.ProseMirror.innerHTML = html`，dispatch input 事件。
3. **二次核验**：从编辑器读取 innerText，用 `validate_article.py` 的规则核验汉字数。
4. 若编辑器汉字数与本地结果差异超过5% → 只允许重新写入同一份HTML一次，不重新生成正文。
5. 写入标题：`page.locator('textarea[placeholder*="请输入文章标题"]').fill(title)`。核验写入值与目标标题完全一致，长度2-30字。
6. 更新 state.json（phase=3）。

### Phase 4：配图生成、上传、relocate

1. 从正文中提取3段场景描写作为英文prompt。
2. 调用 `python scripts/generate_images.py` 生成3张图片（Agens主→sese-ai回退）。
3. 若任意图片生成失败（Agens和sese-ai都失败）→ 不发布当前文章，清空标题/正文/图片，保存失败状态，不降级。
4. 下载图片后，依次 `browser_drop` 到 `.ProseMirror`。
5. 执行 `validate_images.js` 的 `relocateImages(page)` 自动分布到25%/50%/75%位置。
6. 核验图片：`validateImages(page)`：
   - imageDivCount === 3 | blobCount === 0 | cdnImageDivCount === 3
   - 分布通过：三档区间 [8%,30%] / [30%,55%] / [55%,85%]，每档≥1，间距≥15%
   - 最后3个文字段无图 | 图前一段以 。！？ 结束
7. 任一项不通过 → 清空图片DIV后重新 browser_drop → relocate。不超过2次重试。

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

1. 写入 history.json（title, topic, direction, series_id, framework, scheduled_time, publish_status, article_hash）。
2. 写入 metrics.json（滚动30天数据）。
3. 删除 runtime/images/ 下临时图片。
4. 每日2篇成功后，state.json 重置为 idle。
5. history.json 和 metrics.json 保留。

### 下一篇

重复 Phase 0-7 执行当日第二篇。任一篇未完成 → 停止当天流程，修复后重试。

## 启动恢复

## 启动恢复

每次启动执行 `python scripts/run_pipeline.py --recovery`：
- `publish_verified=true` → 直接继续下一篇。
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

## Phase 0→7 详细流程

### Phase 0：数据采集

```bash
# 从页面获取最近20篇 + 昨日数据 + 粉丝画像
browser_navigate('https://mp.toutiao.com/profile_v4/manage/content/all')
→ browser_snapshot 提取标题/数据
→ python scripts/collect_metrics.py 计算指标 → 写入 runtime/metrics.json
```
失败 → 采集字段为 null 继续，不编造。页面全空 → 自动重试1次后跳过。

### Phase 1：选题评分

```bash
# 生成候选选题，读取 metrics.json 获取高表现方向
python scripts/score_topics.py < runtime/_candidates.json
→ 输出评分排序列表，取最高分
```
失败 → 退回到用户确认选题方向，重试1次。

### Phase 2：内容生成与本地硬闸

```bash
# 生成正文HTML → 写入临时文件 → 验证
python scripts/validate_article.py article.html
→ 输出 {passed: bool, failures: [...]}
```
**重试标准**：
- chinese_count < 1500 → 整篇重生成（2200汉字目标），第二次失败标记 content_failed。
- 其他验证失败 → 修正后重新验证，不重生成。
- content_failed → 不进入Phase 3，当前文章跳过。

### Phase 3：写入编辑器

1. 打开发布页，执行页面签名检查（9项全部通过）。
2. `scripts/editor.js` 的 `writeBody(page, html)`。
3. `verifyBody(page)` 核验汉字数。编辑器与本地差异>5% → 重新写入一次。
4. `page.locator()` 写标题，核验长度2-30字且与目标完全一致。
5. 更新 state.json（phase=3, article_hash）。

失败 → 清空编辑器后重试。2次失败 → 停止当天流程。

### Phase 4：配图生成/上传/relocate

1. 提取3段英文prompt → `python scripts/generate_images.py`。
2. 3张全部生成成功 → `browser_drop` 依次拖入 `.ProseMirror`。
3. `scripts/validate_images.js` 的 `relocateImages(page)` 分布图片。
4. `validateImages(page)` 全项核验。

任意图片生成失败（Agens+sese都失败）→ 不发布，清空后标记失败。
图片核验不通过 → 清空图片DIV后重拖（最多2次），仍不过→不发布。

### Phase 5：开关/位置/封面/定时

1. 执行 `scripts/publish.js` 的 `setSwitches(page)` → 所有开关确认。
2. 取消引用AI，核验为false。
3. `setPosition(page, '上海')` → 验证包含"上海"。
4. `setCover(page)` → 选中单图，预览非空。
5. 执行前核验清单9项全部通过。
6. `schedulePublish(page, dayStr, hourStr)` → 日期验证+时间核验+两步确认。

**ensureSwitchWithVerify 铁律**：找不到throw → click后checked仍false throw。
**时间核验**：同时验证日期、小时、分钟。漏任一→throw。

### Phase 6：发布后列表验证

1. `scripts/verify_publish.js` 的 `verifyPublished(page, title, time)`。
2. URL在作品管理页 + 标题精确匹配 + 状态为定时发布 + 时间一致。
3. 无法确认→最多3次核验（含1次刷新）。仍无法确认→publish_uncertain停止。

### Phase 7：状态落盘和临时文件清理

```bash
# 写入历史 → 清理临时文件 → 重置状态
python -c "
from scripts.state import append_history, cleanup_temp, reset_to_idle
append_history({...})
cleanup_temp()
reset_to_idle()
"
```

## 选择器速查

所有选择器唯一来源：`config/selectors.yaml`。

| 用途 | URL / 选择器 |
|------|-------------|
| 发布页 | `https://mp.toutiao.com/profile_v4/graphic/publish` |
| 作品管理列表 | `https://mp.toutiao.com/profile_v4/manage/content/all` |
| 标题输入框 | `textarea[placeholder*="请输入文章标题"]` |
| 正文编辑器 | `.ProseMirror` |
| 位置 | `.position-cell .edit-label` → `.position-select` → `.byte-select-option` |
| 封面单图 | `.byte-radio-wrapper` 含文本"单图" |
| 日期选择 | `.day-select` / `.hour-select` / `.minute-select` |
| 定时按钮 | `button:has-text("定时发布")` |
| 最终确认 | `button.publish-btn:has-text("定时发布")` |

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
