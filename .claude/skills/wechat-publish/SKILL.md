---
name: wechat-publish
description: 公众号谋生与人性全自动生产管线 v9.0 — 品牌增长策略 + 状态机驱动 + 无人值守
vars:
  siliconflow_api_key: sk-fhyebysadetapteypeklskautvwwpcizruxnqhbwmrqbacfy
---

# 公众号「谋生与人性」v9.0 — 品牌增长与状态机发布引擎

**唯一入口**：`run_wechat_publish.py`（禁止绕过脚本手工操作）
**架构**：状态机引擎驱动 22 个状态。AUTO 步骤脚本自动执行，BROWSER 步骤由 Codex 调用 Playwright 操作后标记完成。
**排版核心**：`bake_wechat_html.py` — `split_blocks()` 句子级拆分 + `--auto-position` 自动算图 + `<p id="pN">` 防 ProseMirror 合并

---

## 执行流程

### 第 0 步：启动会话

```bash
cd C:/Users/59314/claudework
python run_wechat_publish.py --init "选题关键词"
# 重置状态机，开始新会话
```

### 第 1 步：状态机循环

```bash
while true; do
  python run_wechat_publish.py --status   # 读取 current_state
  # AUTO  → python run_wechat_publish.py --step
  # BROWSER → 执行下方对应 Playwright 代码 → python run_wechat_publish.py --complete
  # terminal(done) → 退出循环
  # terminal(error) → 判断错误类型：终局错误则通知用户，其余自动重试或回滚
done
```

---

## 完整状态定义（22 个状态）

| 序号 | 状态名 | 类型 | 描述 | 最大重试 | 恢复点 |
|---|---|---|---|---|---|
| 0 | init | auto | 检查目录/依赖 | 1 | ✅ |
| 1 | topic | browser | 选题: 按SOP选定文章主题和标题 | 2 | ✅ |
| 2 | write | auto | 写作: 生成文章并保存 .txt（2400—2800 汉字，策略字段自动验证）| 2 | ✅ |
| 3 | qa_para | auto | 段长闸: check_wechat_para.py | 2 | |
| 4 | qa_ai | auto | AI味闸: ai_score.py ≤45 | 2 | |
| 5 | image_gen | auto | 生图: cover.jpg + inline1-3 | 2 | ✅ |
| 6 | dedup | browser | 去重: Playwright提取已发表标题 | 2 | ✅ |
| 7 | cors | auto | CORS服务: 启动HTTP服务器 :8768 | 2 | ✅ |
| 8 | editor_open | browser | 编辑器: 打开新文章编辑页 | 2 | ✅ |
| 9 | title_author | browser | 标题作者: 填入编辑器 | 2 | |
| 10 | image_upload | browser | 插图上传: 3张一次传完获取CDN | 2 | ✅ |
| 11 | bake | auto | 烘焙: bake_wechat_html.py | 2 | |
| 12 | validate | auto | 门禁: validate_wechat_html.py | 2 | ✅ |
| 13 | insert | browser | 插入正文: fetch→清空→insertHTML | 2 | ✅ |
| 14 | visual_check | browser | 视觉检查: 截图验证排版 | 2 | ✅ |
| 15 | cover | browser | 封面: 上传并设置封面图 | 2 | ✅ |
| 16 | final_verify | browser | 终极验证: DOM+CDN+表情+封面 | 2 | ✅ |
| 17 | save | browser | 保存草稿 | 2 | ✅ |
| 18 | review | auto | 记录本轮内容支柱、营销任务和选题分 | 1 | |
| 19 | skill_fix | auto | 技能修复: 固化本次经验 | 1 | |
| 20 | cleanup | auto | 清理: 临时文件+备份轮换 | 1 | |
| 21 | done | terminal | 完成 | 0 | ✅ |

---

## §0 账号定位与营销运营策略

### §0.1 一句话定位

**「谋生与人性」帮助普通人解决现实问题：一半讲怎样获得收入、保护现金流和提升工作能力；一半讲怎样看懂利益、关系与选择。**

账号按“问题”服务读者，不按年龄圈人。核心读者是正在处理工作、收入、合作、家庭责任和现实选择的成年人。中年只是可用的人生阶段标签，不是内容主线，也不是标题默认前缀。

### §0.2 三条内容支柱

每篇文章只归入一个支柱。滚动最近 10 篇保持 `4:3:3`，下一篇优先补足缺口最大的支柱。

| 内容支柱 | 10 篇配额 | 解决的问题 | 固定栏目 |
|---|---:|---|---|
| 谋生工具箱 | 4 | 职业、副业、报价、技能、AI 工具、社保、合同、现金流、小生意 | 给出可执行步骤、工具或模板 |
| 人性账本 | 3 | 合作、利益、边界、信任、人情、职场关系、亲密关系 | 讲清行为动机、代价和判断标准 |
| 现实选择题 | 3 | 钱与关系、工作与家庭、技术与普通人、养老与责任、消费与欲望 | 用真实情境拆解决策 |

**年龄标签门**：滚动最近 10 篇标题中，含“中年/人到中年/中年人/四十岁/五十岁”的文章最多 2 篇。年龄只在社保、养老、父母照护、职业转折等确实具有阶段差异时使用。

### §0.3 三种营销任务

每篇文章同时承担一个营销任务。滚动最近 10 篇保持 `5:3:2`。

| 营销任务 | 10 篇配额 | 文章必须交付的东西 | 目标 |
|---|---:|---|---|
| 搜索拉新 | 5 | 明确问题、具体答案、可搜索关键词 | 获得搜索和推荐入口 |
| 信任建立 | 3 | 真实案例、判断过程、可验证细节 | 让读者认可账号判断力 |
| 收藏沉淀 | 2 | 清单、表格、模板、步骤或决策树 | 提高收藏、分享和回访 |

不使用奖励、胁迫或夸张措辞诱导关注、点赞、分享。结尾只提出一个与正文直接相关的具体问题，邀请自然留言。

### §0.4 数据反馈闭环

每次选题先从公众号已发表列表读取最近 20 篇的阅读、点赞、分享、推荐、留言和划线数据。单篇传播分按下式计算：

`传播分 = 阅读人数 + 2×点赞人数 + 5×分享人数 + 3×推荐人数 + 3×留言条数 + 2×划线人数`

同一内容支柱累计至少 3 篇后才参与配额调整。每完成 10 篇，只允许把下一轮 1 个名额从最低传播分支柱移给最高传播分支柱；每个支柱最低 2 篇、最高 5 篇，禁止因单篇爆文把账号重新锁死在单一题材。

### §0.5 运营节奏与账号资产

- 以 10 篇为一个运营周期，周期内保持既有发布频次和时段，不同时改频率、时段和题材。
- 三个固定栏目名称就是“谋生工具箱、人性账本、现实选择题”，账号菜单、合集和文末相关阅读统一使用这三个名称。
- 每个栏目保留一篇入口文章，说明该栏目能解决什么问题，并链接 3 篇最具代表性的内容。
- 每篇只测试一个主要变量：选题、标题结构或交付物。下一轮依据 24 小时和 72 小时数据调整，不凭当天感觉改方向。
- 阅读决定入口价值，分享和收藏决定实用价值，留言和推荐决定信任价值；不以单一阅读数判定整条内容支柱。

### §0.6 增长与商业化路径

增长只走一条漏斗，不额外制造第四套内容分类：

1. **入口**：用“搜索拉新”文章回答具体问题，让新读者通过搜索、推荐和转发第一次进入账号。
2. **留存**：把文章归入三个固定栏目，文末只推荐同栏目最相关的一篇旧文，账号菜单提供栏目入口。
3. **沉淀**：把高分享、高划线的步骤、清单和判断标准整理成可反复使用的内容资产。
4. **转化**：连续两个运营周期出现同一类高需求后，先做免费清单验证领取和使用，再把被反复使用的资产组合成模板包、工具包或案例服务。

三个栏目对应的商业化方向固定如下：

| 栏目 | 免费资产 | 后续可验证产品 |
|---|---|---|
| 谋生工具箱 | 报价表、客户沟通清单、工具流程、现金流表 | 模板包、实操工具包、案例拆解 |
| 人性账本 | 合作检查表、边界话术、关系成本清单 | 判断卡片包、场景案例库 |
| 现实选择题 | 决策表、风险清单、家庭分工表 | 决策工具包、专题案例服务 |

公众号长文是内容母版。同一篇只派生三种外部分发素材：一个核心判断、一张步骤清单、一个真实案例片段；外部分发不另起新主题，确保所有渠道共同强化“谋生与人性”。

### §0.7 账号承诺与风险边界

- 工具教程必须真实操作过，收益数字必须有可验证来源；禁止编造“赚了多少”“问了多少人”。
- 关系文章必须给出判断标准或行动方案，禁止只制造焦虑和情绪共鸣。
- 社会热点只作为现实问题入口，不做无资质的时政采编，不靠冲突对立蹭流量。
- 标题必须清晰、完整、准确体现正文主旨；禁止恐吓、绝对化、隐藏关键信息和模板化夸张。
- AI 可以辅助生产，正文必须包含真实体验、具体工具、数据来源或可复核案例。
- 配图人物的年龄、职业和关系必须从正文场景提取，禁止默认生成中年人物。

---

## §1 选题流程（状态 1: topic，BROWSER 步骤）

**执行时机**：状态机达到 `topic`。严格按“数据盘点 → 配额缺口 → 候选搜集 → 百分制评分 → 唯一胜出题”执行，并把策略字段写入 `session_state.json` 后才允许进入 `write`。

### §1.1 数据盘点与候选来源

1. 从已发表列表提取最近 20 篇标题和六项互动数据，计算三支柱最近 10 篇数量、营销任务数量及年龄标签数量。
2. 先确定缺口最大的内容支柱和营销任务，再围绕该组合搜集 3 个候选题。
3. 搜索词从内容支柱产生：
   - 谋生工具箱：职业选择、副业、报价、合同、社保、现金流、AI 工具、效率、小生意。
   - 人性账本：合作、利益、边界、信任、人情、借钱、拒绝、职场关系、亲密关系。
   - 现实选择题：家庭责任、养老、婚姻财务、教育成本、技术影响、消费决策、风险选择。
4. 用微信搜一搜读取候选关键词前 10 条标题，确认存在真实搜索意图；再补充亲身实践、后台数据、公开资料或可复核案例。

### §1.2 百分制选题门

三个候选逐项评分，只选择总分最高且不低于 75 分的一题。

| 评分项 | 分值 | 得分标准 |
|---|---:|---|
| 品牌匹配 | 25 | 明确落在“谋生、人性或两者交叉”，账号名称能自然解释 |
| 实用价值 | 25 | 读完能采取行动，得到步骤、工具、清单、模板或判断标准 |
| 搜索意图 | 20 | 标题对应用户会主动搜索的具体问题 |
| 真实证据 | 15 | 有亲测过程、真实场景、后台数据或可靠公开来源 |
| 差异化 | 10 | 与最近 20 篇不重复，不套用连续出现的框架 |
| 栏目连续性 | 5 | 能强化“谋生工具箱、人性账本、现实选择题”之一 |

以下任一命中即淘汰：与最近 20 篇主题高度重叠；纯情绪无行动答案；收益或人数无法验证；标题默认套“人到中年”；连续使用“先看这四个/几个信号/几笔账”等同构模板。

### §1.3 标题与开头

标题只使用一种结构，并明确交付内容：

- 工具型：`具体工具/问题 + 可完成的结果 + 交付物`，例如“批量整理客户资料：这套表格能省掉每天一小时”。
- 决策型：`具体处境 + 怎样选择 + 核心权衡`，例如“工作不稳定时要不要买房：先算现金流，不先猜房价”。
- 案例型：`真实对象/行动 + 具体结果 + 可复用经验`，例如“一个小店怎样把退货率降下来：店主改了三处流程”。

正文前 150 汉字必须交代具体场景、读者损失和本文交付物。搜索关键词自然出现一次，不堆砌。禁止把“痛点+数字框架”作为所有文章的统一标题模版。

### §1.4 写入状态

选题完成后写入以下字段：

```json
{
  "topic": "具体主题",
  "title": "最终标题",
  "article_file": "绝对路径",
  "content_pillar": "谋生工具箱|人性账本|现实选择题",
  "marketing_job": "搜索拉新|信任建立|收藏沉淀",
  "topic_score": 75,
  "topic_evidence": "搜索意图和真实证据摘要",
  "actionable_asset": "本文交付的步骤、工具、清单、模板或判断标准",
  "pillar_counts_last10": {"谋生工具箱": 4, "人性账本": 3, "现实选择题": 3},
  "age_title_count_last10": 0,
  "dedup_result": "实时去重结果"
}
```

`write` 状态会硬检查支柱、营销任务、选题分、证据、交付物、年龄标签上限、标题一致性和 2400—2800 汉字。任何字段缺失都不得继续。

---

## §2 正文绑定配图（状态 5: image_gen，AUTO 步骤）

唯一入口仍是 `python run_wechat_publish.py --step`，禁止手工复用工作区现成图片。状态机对文章正文计算 SHA-256 指纹；只有 `image_manifest.json` 的文章指纹、四张图片哈希和当前正文完全一致时，才允许断点续跑复用。正文变化或清单缺失时，必须在 `_wechat_image_stage` 中重新生成 `cover.jpg` 与 `inline1.jpg`—`inline3.jpg`，四张全部通过后再一次替换工作区图片。

`auto_gen_images.py` 对每个插图标记执行同一条规则：锁定标记前最近的小节，从该小节选择人物、地点、动作和物件最明确的段落；提示词必须包含小节标题和完整具体场景，不得只截最后一段，不得统一截成 120 字，不得默认中年人物。三张正文图使用不同镜头距离，但人物年龄、职业、关系与情境只能来自本篇正文。

生图完成必须同时满足：

1. `image_manifest.json.article_sha256` 等于当前文章指纹；
2. 四张图片均存在、单张不少于 10KB，文件哈希与清单一致；
3. 三张正文图分别记录 `section_title`、`scene` 和完整 `prompt`，三个场景互不相同；
4. `logs/wechat_img_gen.log` 写入本轮文章路径、指纹、每张图对应章节和场景；旧日志不得作为本轮成功证据。

任一项失败，`image_gen` 保持当前状态并按状态机上限重试；旧图不得进入上传步骤。

---

## BROWSER 步骤实现

### 选择器表

| 用途 | 唯一选择器 |
|---|---|
| 标题编辑器 | `document.querySelectorAll('.ProseMirror')[0]` |
| 正文编辑器 | `document.querySelectorAll('.ProseMirror')[1]` |
| 作者输入框 | `input[placeholder="请输入作者"]` |
| 正文图片入口 | `li#js_editor_insertimage` |
| 封面入口 | `.select-cover__btn.js_cover_btn_area` 的第一个元素 |
| 图片库菜单 | 可见的 `a.pop-opr__button.js_imagedialog` |
| 图片库弹窗 | 标题含“选择图片”的 `.weui-desktop-dialog` |
| 封面缩略图 | `cover.jpg` 图片项内的 `.weui-desktop-img-picker__img-thumb` |
| 封面预览 | `.js_cover_preview_new` |
| 保存草稿 | 角色为按钮、名称为“保存为草稿” |

### topic — 选题

参照 **§1 选题流程** 执行：

1. **实时盘点**：按下方 `dedup` 路径提取最近 20 篇标题及六项互动数据
2. **分类计数**：计算最近 10 篇三支柱、三营销任务和年龄标签数量
3. **确定缺口**：选择配额缺口最大的“内容支柱 × 营销任务”组合
4. **搜集候选**：按 §1.1 为该组合搜集 3 个候选题
5. **唯一胜出**：按 §1.2 评分，选择最高且不低于 75 分的一题
6. **一次写足**：写入精确 `article_file`，目标 2600 汉字并通过 2400—2800 汉字硬门
7. **写入状态**：按 §1.4 写全策略字段和实时去重结果
8. **标记完成**：`python run_wechat_publish.py --complete`

### dedup — 去重（熔断级，不可跳过）

**执行时机**：每次启动本技能、写任何内容之前。必须先到公众号已发布列表页提取所有已发布标题。

**核心逻辑**：Playwright 从发表列表页提取所有已发标题 → 与当前文章标题比对 → 重复则熔断换题。

```javascript
// ========== Step 1: 从登录页 URL 提取 token ==========
// 先 browser_navigate → https://mp.weixin.qq.com/
// 落地 URL 形如 /cgi-bin/home?...&token=1742414256
// 提取 token 写入 state：
//   python -c "import json;s=json.load(open('session_state.json', encoding='utf-8'));s['token']='XXXXXX';json.dump(s,open('session_state.json','w', encoding='utf-8'))"

// ⚠️ 顶层 run_code 环境没有 URLSearchParams，禁止写 new URLSearchParams

// ========== Step 2: 导航到发表记录页（唯一去重入口）==========
browser_navigate → https://mp.weixin.qq.com/cgi-bin/appmsgpublish?sub=list&begin=0&count=20&token={token}&lang=zh_CN

// 禁止用下列页面当去重源：
// - /cgi-bin/appmsg?t=media/appmsg_list&action=list_card&type=9 → 素材库，常「暂无素材」
// - /cgi-bin/appmsg?type=77&action=list_card → 草稿箱
// - /cgi-bin/masssendpage?t=mass/list&action=history → 群发历史（标题带 [图文1] 前缀）

// ========== Step 3: evaluate 提取所有已发表标题 ==========
// 必须用 evaluate，snapshot 可能不完整
const titles = await page.evaluate(() => {
  const result = [];
  document.querySelectorAll('a, .title, h4, span, strong, [class*="title"]').forEach(el => {
    const t = (el.innerText || '').trim().replace(/\s+/g, ' ');
    if (t && t.length >= 8 && t.length <= 60 && !result.includes(t) &&
        !/^(首页|内容管理|互动|数据|收入|账号|广告|设置|素材|图片|音频|视频|新建|管理|关于|服务|规则|客服|侵权|反馈|问题|通知|谋生与人性|暂无|图文|商品|发表|全部|已通知|未通知|置顶)/.test(t) &&
        !/腾讯|Copyright|上传|日志|实时人数|第二日|风险|建议修改/.test(t)) {
      result.push(t.replace(/\s*原创\s*$/, ''));
    }
  });
  return result;
});

// ========== Step 4: 与当前标题比对 ==========
// - 待发布标题与 titles[] 完全匹配 → 熔断，报告「已发布过：<标题>」
// - 关键词高度重叠（同一主题/同一框架）→ 熔断，换选题
// 熔断后终止流程，不写任何新内容

// 通过后标记完成：
// → python run_wechat_publish.py --complete
```

**去重铁律**（2026-07-22 恢复）：
1. 每次启动技能必须先执行此事。不做就去写内容 = 流程违规。
2. 不依赖记忆或历史记录——必须实时从页面提取。
3. `appmsgpublish?sub=list` 是唯一稳定已发标题入口。
4. 比对结果分别打字写入 session_state.json 的 dedup_result 字段供下一步参考。

### editor_open — 打开编辑器

```javascript
browser_navigate → https://mp.weixin.qq.com/cgi-bin/appmsg?t=media/appmsg_edit_v2&action=edit&isNew=1&type=77&createType=0&token={token}&lang=zh_CN
// 等待 editor 加载（.ProseMirror 出现）
```

### title_author — 填标题和作者

```javascript
// 标题
const pm0 = document.querySelectorAll('.ProseMirror')[0];
pm0.focus();
document.execCommand('selectAll');
document.execCommand('insertText', false, '文章标题');

// 作者
await page.locator('input[placeholder="请输入作者"]').fill('谋生与人性');
```

### image_upload — 上传 3 张正文图片

```javascript
// Step 1: 点击工具栏插入图片按钮
document.querySelector('li#js_editor_insertimage')?.click();
await new Promise(r => setTimeout(r, 1000));

// Step 2: 找到文件 input，用 setInputFiles 一次上传 3 张（Playwright 原生方式）
// 注意：此处需要在 Playwright 的 browser_run_code_unsafe 中执行
const fileInput = page.locator('input[type="file"]');
await fileInput.setInputFiles([
  'C:\\Users\\59314\\claudework\\inline1.jpg',
  'C:\\Users\\59314\\claudework\\inline2.jpg', 
  'C:\\Users\\59314\\claudework\\inline3.jpg'
]);

// Step 3: 等待上传完成（8-10s，取决于文件大小和网速）
await page.waitForTimeout(10000);

// Step 4: 从 ProseMirror 正文中提取 CDN URL
const cdnUrls = await page.evaluate(() => {
  const bodyPM = document.querySelectorAll('.ProseMirror')[1];
  if (!bodyPM) return [];
  return Array.from(bodyPM.querySelectorAll('img'))
    .map(img => img.src)
    .filter(src => src && src.startsWith('http'));
});

// Step 5: 写入 state → Codex 执行
// 取 cdnUrls[0..2] 写入 session_state.json 的 cdn_urls 字段
// 然后 python run_wechat_publish.py --complete

### insert — 插入正文（v8.1 — 改用 innerHTML + input event）

```javascript
const resp = await fetch('http://127.0.0.1:8768/article_final.html');
const html = await resp.text();

const bodyPM = document.querySelectorAll('.ProseMirror')[1];
bodyPM.innerHTML = '';
await new Promise(r => setTimeout(r, 200));
bodyPM.innerHTML = html;
bodyPM.dispatchEvent(new Event('input', {bubbles: true}));
await new Promise(r => setTimeout(r, 500));

// 验证
const withSrc = Array.from(bodyPM.querySelectorAll('img')).filter(i => i.src).length;
// withSrc !== 3 → 重试
```

### visual_check — 视觉检查

截图检查：开头段落正常、中间图片位置正确、结尾完整。用 `browser_take_screenshot` 截取 viewport。
检查项：
1. Markdown 残留（无 `#`、`*`、`---` 等原始符号）
2. 段落堆积（连续空段 ≤2）
3. 图片已渲染（img 元素存在）

### cover — 封面上传（**加固版 2026-07-29**）

**核心原则**：封面按钮、图片缩略图、下一步和确认均用 Playwright 原生定位点击；只有“从图片库选择”菜单按可见性筛选后触发。每步均验证，任何一步失败→刷新页面从头重试。

**黄金路径：点封面+ → 从图片库选择 → 上传本轮 cover.jpg → 点缩略图选中 → 下一步 → 确认 → 验证预览**

```javascript
// ========== 封面上传 — 加固 6 步序列 ==========
// 要求：本轮 image_gen 已在工作区生成 cover.jpg

// Step 0: 检查当前封面状态，避免重复操作
const initCheck = await page.evaluate(() => {
  const preview = document.querySelector('.js_cover_preview_new');
  if (!preview) return 'no_element';
  return /mmbiz/.test(getComputedStyle(preview).backgroundImage) ? 'already_set' : 'empty';
});
if (initCheck === 'already_set') {
  // 封面已存在，跳过
} else {
  // ---------- Step 1: 点封面"+"按钮 ----------
  // 用精确选择器避免 ambiguity（.js_cover_btn_area 匹配 3 个元素）
  await page.locator('.select-cover__btn.js_cover_btn_area').first().click();
  await page.waitForTimeout(2000);

  // ---------- Step 2: 点"从图片库选择" ----------
  const libClicked = await page.evaluate(() => {
    // 选择可见的 a.pop-opr__button.js_imagedialog（3 个匹配中只有 1 个可见）
    const links = [...document.querySelectorAll('a.pop-opr__button.js_imagedialog')];
    for (const link of links) {
      if (link.offsetParent !== null) { link.click(); return true; }
    }
    return false;
  });
  if (!libClicked) throw new Error('封面步骤: 找不到可见的"从图片库选择"');
  await page.waitForTimeout(3000);

  // ---------- Step 3: 等待图片库弹窗 → 上传并选择本轮 cover.jpg ----------
  // 确认弹窗已渲染
  await page.locator('.weui-desktop-dialog__title').filter({ hasText: '选择图片' }).waitFor({
    state: 'visible', timeout: 5000
  });
  const imageDialog = page.locator('.weui-desktop-dialog').filter({
    has: page.locator('.weui-desktop-dialog__title').filter({ hasText: '选择图片' })
  });
  await imageDialog.locator('input[type="file"]').setInputFiles(
    'C:\\Users\\59314\\claudework\\cover.jpg'
  );
  await page.waitForTimeout(12000);
  const coverItem = imageDialog.locator('.weui-desktop-img-picker__item')
    .filter({ hasText: 'cover.jpg' }).first();
  await coverItem.locator('.weui-desktop-img-picker__img-thumb').click();
  if (!(await coverItem.getAttribute('class')).includes('selected')) {
    throw new Error('封面步骤: cover.jpg 未进入 selected 状态');
  }

  // ---------- Step 4: 点"下一步"进入裁剪 ----------
  await imageDialog.getByRole('button', { name: '下一步' }).click();
  await page.waitForTimeout(3000);

  // ---------- Step 5: 等待裁剪弹窗 → 点"确认" ----------
  await page.locator('.weui-desktop-dialog__title').filter({ hasText: '编辑封面' }).waitFor({
    state: 'visible', timeout: 5000
  });
  await page.getByRole('button', { name: '确认' }).click();
  await page.waitForTimeout(3000);

  // ---------- Step 6: 验证封面 ----------
  const coverResult = await page.evaluate(() => {
    const preview = document.querySelector('.js_cover_preview_new');
    if (!preview) return { pass: false, reason: 'preview元素不存在' };
    const bg = getComputedStyle(preview).backgroundImage;
    return { pass: /mmbiz/.test(bg), url: bg.slice(0, 100) };
  });
  if (!coverResult.pass) {
    throw new Error(`封面验证失败: ${coverResult.reason || '无mmbiz CDN'}`);
  }
}

// ========== 完成后标记状态 ==========
// → python run_wechat_publish.py --complete
```

### 失败恢复策略

| 故障点 | 表现 | 恢复动作 |
|--------|------|----------|
| Step 1: 找不到封面按钮 | 选择器无匹配 | 刷新页面回 draft（appmsgid 不变）→ 从头重试 |
| Step 2: 菜单不弹出 | 点击后 no visible link | 刷新页面 → 重试，增 wait 到 3s |
| Step 3: 图片库弹窗空白 | Vue 组件未渲染 | 刷新页面 → 重试，增 wait 到 5s |
| Step 4: cover.jpg 上传后未选中 | 图片项无 `selected` 类 | 刷新页面 → 重新上传本轮 cover.jpg → 点缩略图重试 |
| Step 5: 裁剪弹窗/确认按钮不可用 | waitFor 超时 | 刷新页面 → 重试 |
| Step 6: 验证失败 | 预览图无 mmbiz CDN | 刷新页面 → 重试整个序列 |

**连续 2 次失败**：回滚到 `editor_open` 恢复点，走 `image_upload → bake → validate → insert → visual_check → cover` 重新跑。

**禁止新增分支或跳过验证**。失败就重试全序列，不另辟蹊径。

### final_verify — 终极验证

**发布门**：下方终极验证返回 `pass=true` 后才进入 `save`；任何检查项失败都回滚到对应恢复点，禁止保存草稿。

```javascript
const bp = document.querySelectorAll('.ProseMirror')[1];
const text = bp.innerText;
const preview = document.querySelector('.js_cover_preview_new');
const hasCover = preview ? /mmbiz/.test(getComputedStyle(preview).backgroundImage) : false;
const imgsWithSrc = Array.from(bp.querySelectorAll('img')).filter(i => i.src).length;
const cnCount = (text.match(/[一-鿿]/g) || []).length;
const authorInput = document.querySelector('input[placeholder="请输入作者"]');
const hasAuthor = authorInput?.value === '谋生与人性';

return {
  pass: hasCover && imgsWithSrc === 3 && cnCount >= 2400 && hasAuthor,
  checks: { hasCover, imgsWithSrc, cnCount, hasAuthor }
};
```

### save — 保存草稿

```javascript
// Escape × 3 回到顶层（如有弹窗遮挡）
await page.keyboard.press('Escape');
await new Promise(r => setTimeout(r, 500));
await page.keyboard.press('Escape');
await new Promise(r => setTimeout(r, 500));

// 点击"保存为草稿"按钮
await page.locator('button:has-text("保存为草稿")').click();
await new Promise(r => setTimeout(r, 2000));

// 验证：历史版本记录中出现"手动保存"
const historyCheck = await page.evaluate(() => {
  const cells = [...document.querySelectorAll('td')];
  const saveRow = cells.find(c => c.innerText.includes('手动保存'));
  return { saved: !!saveRow, detail: saveRow?.innerText || '' };
});
// saved === true 证明保存成功
// 保存 appmsgid（从 URL 中提取）到 session_state.json
```

---

## 排版管道（v8.0 — 极简固化）

排版由 `bake_wechat_html.py` 完成，三行 CSS 常量，三种块类型：

```
split_blocks() → auto_position → 渲染 → 全文 = 三种 <p>
  ↑按。！？拆句      ↑82%/55%/25%    ↑ body / sub / img
```
| 元素 | HTML | 关键 CSS |
|------|------|----------|
| 正文 | `<p id="p{N}">` | `font-size:18px;line-height:2;margin:0 0 24px;` |
| 子标题 | `<p id="h{N}">` | `font-size:22px;font-weight:700;color:#1677ff;text-align:center;margin:32px 0;` |
| 图片包裹 | `<p id="i{N}"><img>` | `margin:28px 0;text-align:center;` |

`<p id="p/h/i{N}">` 的 `id` 唯一（N 递增），ProseMirror 不合并不同 id 的 `<p>`，且 `<p>` 不被套多层 `<section>`。只输出 `<p>`+`<img>`，通过 8 项门禁。

---

## 回归测试

检查项：
| 检查 | 预期 |
|------|------|
| 封面存在 | 有 mmbiz 背景图 |
| 无点号段 | dotCount === 0 |
| 3 张有效图片（有 src） | imgsWithSrc === 3 |
| 图片位置误差 ≤5% | [25, 55, 82] 正负 5 |
| 小标题 4-7 个 | 一二三四... |

pass=false → 回滚到上一个恢复点重新执行黄金路径。

---

## 质量门

1. **段长闸**：`check_wechat_para.py` — 无段落超 150 汉字，无连续短段（<20 汉字）
2. **AI味闸**：`ai_score.py` ≤45 分
3. **字数闸**：**2400—2800 汉字，写作目标 2600 汉字**（`len(re.findall(r'[一-鿿豈-﫿]', text))`，只计 CJK 统一表意字符）。必须一次写足，不得先写短篇再在末尾追加；`step_auto_write()` 与段长闸双重验证。
4. **去重闸**：与已发表文章标题不重复
5. **封面闸**：封面上传后验证 mmbiz CDN 存在
6. **配图绑定闸**：图片清单文章指纹一致，四图哈希一致，三张正文图场景互异
7. **视觉闸**：截图检查无 Markdown 残留、图片可见
8. **回归闸**：5 项回归测试全部 pass

---

## 终局错误（需通知用户）

1. 登录失效 / 扫码页面 / 验证码
2. Playwright 连续两次真实调用失败
3. 平台接口连续两次 5xx
4. 文件读写异常
5. 质量门自动修复两次仍不通过

其他一切错误由状态机自动重试或回滚恢复点。

---

## 状态机自动化 CLI 命令

```bash
python run_wechat_publish.py --status          # 查看当前状态
python run_wechat_publish.py --step            # 执行当前 AUTO 步骤
python run_wechat_publish.py --complete        # 标记当前 BROWSER 步骤完成
python run_wechat_publish.py --dry-run         # 测试所有非浏览器步骤
python run_wechat_publish.py --init "主题"      # 初始化新会话
python run_wechat_publish.py --rollback        # 回退到上一个恢复点
python run_wechat_publish.py --reset           # 重置状态机
python run_wechat_publish.py --abort REASON    # 异常终止
python run_wechat_publish.py --regression-test # 打印回归测试 JSON
```

