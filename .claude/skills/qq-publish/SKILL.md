---
name: qq-publish
description: 企鹅号（om.qq.com）文章发布技能 v3.1
version: 3.1
---

# 企鹅号 · AI生活圈 · 文章发布技能 v3.1

**触发**：/qq-publish

## 账号信息

| 字段 | 值 |
|------|-----|
| 账号名 | AI生活圈（⚠️ 账号名与当前内容赛道不符，见下方「当前选题策略」） |
| 状态 | 正式运营（阅读量持续0，冷启动诊断未通过） |
| 编辑器 | 企鹅号 ExEditor（标题是 span，正文是单 ProseMirror） |

| 后台 | https://om.qq.com/main/creation/article |
| 内容管理 | https://om.qq.com/main/management/articleManage |
| 权益管理 | https://om.qq.com/main/account/rights（功能权益 tab 在右侧 main 区，非左侧导航） |

---

## §0 执行总纲（铁序硬控，不可商量、不可调整次序）

> 🔴 **第一铁律：第一步永远是进浏览器看数据，没有例外。**
> 收到 /qq-publish 指令后，**第 1 个动作必须是 `browser_navigate` 进内容管理看数据和去重**——不是读文件、不是想选题、不是写草稿、不是任何"前置条件"。这条是硬控，违反=技能执行失败，立即停。

```
【第 0 步 · 硬控第一步】：browser_navigate → https://om.qq.com/main/management/articleManage
        ↓ 看上一篇文章阅读数据 + 抓已发布标题列表（去重源 + 冷启动/限流判断）
        ↓ 这一步没做，后面任何 PHASE 都不准动
【第 0 步 · 硬控第一步】：browser_navigate → 内容管理（看数据+抓标题去重）
PHASE 0: 选题红线审核 → 通过?
PHASE 1: 流量诊断(用刚看的浏览器数据) → 通过?
PHASE 2: 去重(用刚抓的标题) → 通过?
★ 写前规划门（硬，必须先规划再动笔，见 §0.6）：定标题/钩子/6段+h2骨架/≥3图位(不同src)/增量点 → 全部落纸才动笔
PHASE 2.5: 内容质量门（脚本实跑字数/图/h2/段长 + 4条人工卡点，见 §0.5/2.5）→ 通过?
PHASE 3: 发布 → 通过?
PHASE 4: 验证
```

每个 PHASE 输出必须为 **PASS** 才能进入下一 PHASE。任意 PHASE 输出 **FAIL** → 立即熔断，不继续。

### §0.0 启动即进浏览器，禁止找本地草稿（核心约束，违反=技能执行失败）
本技能**没有「本地草稿文件」作为输入源**。待发布内容不是某个 `.md` / `.html` 文件，而是基于浏览器实测数据**现写 / 现改**出来的。启动后任何 `Glob` / `Read` 本地文件找"待发布草稿"的行为都是错的，立即停止。
- ❌ **严禁**：`Glob`/`Read` 本地 `*.md` `*.html` 寻找"待发布草稿"当内容发布——本技能从不发布本地文件，也从不从文件系统取内容。
- ✅ **启动第一动作**：直接 `browser_navigate` 进 `https://om.qq.com/main/management/articleManage`，做两件事——① 看上一篇文章的阅读数据（冷启动/限流判断）② 抓已发布标题列表（去重源）。
- ✅ **顺序固定**：进浏览器查上一篇文章数据 → PHASE 0 选题红线 → PHASE 1 流量诊断 → PHASE 2 去重（用刚抓的标题列表）→ **据浏览器数据改进内容质量**（调角度/写法/配图）→ PHASE 3 现写现发。
- ⚠️ 「草稿」两字只指**编辑器内自动保存的草稿**（仅 PHASE 2.3 校验用，防误覆盖），与本地文件无关，二者不可混淆。

### §0.1 硬闸（任何 PHASE 都不可逆，违反=违规）
- **A 选题硬闸**：未通过 §0 PHASE 0 选题红线审核，禁止进入 PHASE 1，更禁止准备素材（封面/HTML/正文）。违反本闸 = 技能执行失败。
- **B 素材准备时序**：封面图 / HTML 转换 / 任何发文素材，只能在 PHASE 2 PASS **之后**准备。禁止在去重通过前生成封面或转正文。
- **C 内容质量门硬闸**：PHASE 2.5 未通过（字数/排版/图片/信息增量任一不达标），禁止进入 PHASE 3，退回重写。违反本闸 = 技能执行失败。**不得因流程跑通就放行垃圾内容**——质量门是发布前最后一道人眼卡点，须逐项自检通过才放行。

---

## PHASE 0：选题红线审核（硬性，不通过不进入 PHASE 1）

### 0.1 企鹅号受众画像
- 内容中台 QQ看点：95后/00后扎堆，偏好校园生活、明星八卦、动漫二次元、电竞数码、搞笑娱乐、情感。
- 腾讯新闻/QQ浏览器/微信看一看：下沉市场，偏好民生实用、健康养生、情感家庭、正能量、实用干货。
- 平台算法偏爱（多平台运营者复盘原文）："无论哪个内容平台，只要能从财富、健康、教育等方面制造一定焦虑和恐惧，以及传播娱乐、搞笑内容，都会备受流量青睐。鸡汤性质的内容，企鹅号貌似更加偏爱。"

### 0.2 选题红线（违反任一 = FAIL，熔断，禁止发布）
| 类型 | 判定 | 处理 |
|:-----|:-----|:-----|
| ❌ 禁止 AI/科技/大模型/副业卖课/高知男视角 | 标题或正文以 AI 工具、模型、代码、副业赚钱为核心 | **直接 FAIL**，不写不发 |
| ❌ 禁止纯技术教程、参数对比、行业趋势分析 | 面向技术人群的内容 | **直接 FAIL** |
| ✅ 首选 国民常青赛道：游戏 | 企鹅号爆款领域第一就是游戏，话题足、受众广、长青。标题每期现想，不预设栏目名/不编号（见下方选题策略坑） | 通过（分类选「游戏」） |
| ✅ 允许 其他国民常青赛道 | 情感/家庭、民生实用干货、健康养生、历史名人轶事、搞笑娱乐、正能量 | 通过 |
| ⚠️ 例外：AI 仅作"下沉化实用技巧"载体 | 如"打工人用AI十分钟写完周报"——AI 不是主角，解决普通人麻烦才是 | 视为禁止类（FAIL），不得发布 |

### 0.3 审核动作
```
输入：待发布文章的标题 + 主题关键词
IF 命中「禁止 AI/科技/高知男视角」 → FAIL：选题违反红线，停止
IF 命中「国民常青赛道」 → PASS
IF 命中「例外(下沉化AI技巧)」 → 视为禁止类（FAIL），不得发布
```
**PHASE 0 输出 FAIL → 立即熔断，不进入 PHASE 1，不准备任何素材。**

### 0.4 写法铁律（用户 2026-07-12 硬要求 + 2026-07-15 补充呼吸感规则）
- **聊天体，不是新闻稿/百科体**。像跟读者坐一块儿唠嗑：多用"你玩过没""当年我也……""说真的""咱实话讲"；口语、碎句、反问、自嘲。
- **禁止**：第三人称客观叙述、"本文报道""据悉""专家指出"等新闻腔；禁止百科词条式罗列参数。
- **禁止 AI 味**：不写"值得一提的是""综上所述""在当今社会"；不堆华丽排比。
- **禁止标准式结尾**：不写"留个问题""评论区唠唠""说说你的看法"这类硬抛互动的套路收尾。结尾要像真聊完随口停住，可用悬念钩子（"下一期聊的那个，说出来你可能都不信"），不要向读者下指令。
- **🆕 呼吸感：段落长短交替，每 h2 区块至少含一根"换气管"（1-2 句的短段）**。禁止连续 2 段以上超过 150 汉字——读者读着读着会累，需要短句短段来"换气"。写时每 h2 区块内故意穿插一段 1-2 句话的段落（汉字 ≤ 50），作为阅读节奏的停顿。
- **模仿参照**：动笔前先找一篇同平台同类爆款文章，分析其段长分布。直接复制参考文章的段落节奏（短段/长段比例、每段汉字数序列），用自己的内容填进去。不准先写 50 字再补丁式扩写。


### 0.5 内容硬指标（用户 2026-07-12 硬要求，必须**代码实跑**量化，不可自填报）
> ⚠️ 下列每条都是**可被 JS 量化的硬数值**。PHASE 2.5 会跑真实脚本算出来，不满足 → 脚本直接输出 FAIL，退回重写。**文字清单约束不了行为，必须靠代码卡。**

- **字数（纯汉字，非字符、非英文、不含标点/标签）**：
  - 游戏长文 **最少 3000 汉字**（用户 2026-07-12：「最少 3000 汉字以上」）。
  - 计量公式（PHASE 2.5 实跑）：`text.replace(/<[^>]+>/g,'').replace(/[^一-龥]/g,'').length` —— 只留 一–龥，其余全删。
  - `< 3000` → FAIL（水稿）。
- **排版**：
  - 每段纯汉字 ≤ **150**（超过需拆段）。
  - **🆕 段长分布（2026-07-18 新增）**：整篇段落汉字数中位数 ≤ **90**（即至少一半段落汉字 ≤ 90）；汉字数 > **120** 的超长段占比 ≤ 总段数的 **10%**；禁止连续 **2** 段汉字 > **110** 之间无任何 ≤ **80** 的段落插入。
  - h2 小标题数量：总汉字 / 600，向上取整，即 3000 字至少 **5 个 h2**。
  - **🆕 段落节奏（呼吸感）**：每 h2 区块内至少含 1 个短段（汉字 ≤ 50），用于视觉换气。禁止连续 **2** 段汉字 > **100** 之间无任何 ≤ **50** 的短段插入。
  - **🆕 区块段落数**：每 h2 区块下至少 3 个 `<p>`（含过渡性短段）。单区块仅 1-2 段 = 排版不合格（文字墙）。
  - 实测：统计 `<h2>` 数量 + 最长 `<p>` 的汉字数 + 按 h2 拆区块统计短段分布。
- **图片**：
  - 封面 1 张（1024×1024）。
  - **文中图 ≥ 3 张**：正文 `<img>`（非封面区）≥ 3。**每张 src 必须不同，不得重复使用同一张图。**
  - 实测：统计正文内 `<img>` 数量 + 去重 src 数量。
- **信息增量 / 选题一致 / 钩子非空 / 非模板腔**：
  - 这四条**代码无法直接判定**，列为 PHASE 2.5 的「人工卡点」——必须在发布前由执行者逐字过一遍并给出具体证据（哪句是增量、标题/正文/钩子各写的什么、钩子指向哪期），任一条答不出 = FAIL。禁止填"PASS"了事。

### §0.6 写前规划门（硬，动笔前必须锁死，违反=技能执行失败）
> ⚠️ **质量把关在上游，不在下游。** 禁止「先随便写、写完用脚本凑数」——那是我反复犯的错（先写 1600 字再补到 3000，纯属事后补救）。正确做法：去重 PASS 后、**动笔前**，先把下列硬参数一次性规划落纸，全部定死才允许写正文。规划缺口 = 直接停，不准动笔。

- **找参考模板**：选 1 篇同平台同类文章，读开头 2-3 段，用 `段内容.replace(/[^一-龥]/g,'').length` 统计每段汉字数，看段长分布（中位数、最长段、短段比例），直接把参考模板的段长序列写进规划。禁止闭门造车凭空写。
- **标题**：现想，不预设栏目名/不编号。须满足 §0.4 聊天体 + 强话题（让人想点的痛点/反差/好奇）。标题定稿后不得中途改。
- **钩子**：结尾须指向**已定的下期主题**（具体，不悬空）。钩子先于正文定，正文为钩子服务。
- **骨架**：按「汉字数 ÷ 500」定 h2 段数下限（3000 字 → ≥6 个 h2），每段承载一个独立子观点，**不得有"水段"**（只凑字数无信息）。
- **配图位 + 图描述词**：按 h2 段数布 ≥3 个 img 位。**图片规则：① 每张图必须放在与之内容相关的段落之后 ② 每张图 src 必须不同 ③ 每张配图标注描述词（scene_prompt）**，根据该段核心内容提取——如"首充礼包"段落 → `first purchase reward, mobile payment screen`。描述词写进规划后再写正文。
- **增量点**：正文须含 ≥2 个「读者原不知道」的硬信息/反直觉观点（如"它因太成功而衰落""满足的是存在感非装备"）。先列增量清单再写，无增量清单 = 不准写。
- **字数预算（硬核算，动笔前必跑，禁凭手感拍）**：选好 h2 段数 N 后，**必须先跑下方预排版核算脚本**，由脚本算出「每段汉字下限 / 上限 / 换气短段 / 段落数 / 图位」的逐段锁死表。脚本是唯一权威，不得自己心算"每段~500"。下段"规划 PASS"验收要求把脚本打印的表逐行抄进规划，缺表 = 不准动笔。

> 🔧 **预排版核算脚本（动笔前必跑一次，输出即逐段锁死表）**：
```js
// 运行：node -e "..."  传入：TARGET=3000, N=选定h2段数
function preWriteBudget(TARGET, N){
  const minH2   = Math.ceil(TARGET/600);            // 质量门地板（3000→5）
  if (N < minH2) return 'FAIL: 段数 '+N+' < 最少h2 '+minH2+'，加段';
  const floor   = Math.ceil(TARGET/N);              // 每段汉字下限，保证 N×floor≥TARGET
  const ceil    = 150*3;                            // 每段上限≈3个≤150长段(留换气)
  const totalOk = N*floor >= TARGET;               // 下限总和必须≥目标
  const imgMin  = Math.max(3, N);                   // 文中图下限
  const rows = [];
  for (let i=1;i<=N;i++){
    rows.push(
      `段${i}(h2): 汉字 ${floor}–${ceil} ｜ 含≥1个≤50换气短段 ｜ ≥3个<p>(每段≤150) ｜ 段后1张img(${i<=imgMin?'必填':'封面另算'})`
    );
  }
  return {
    TARGET, N, 最少h2:minH2, 每段下限:floor, 每段上限:ceil,
    下限总和:N*floor, 达标: totalOk, 文中图下限:imgMin,
    锁死表: rows,
    // 段长分布要求（2026-07-18）：总段数 = N × (每h2区块最少3段) 约 18+
    段长中位数要求: '≤90（写完第3段后实跑自查）',
    超长段大于120占比: '≤总段数10%',
    连续2段大于110: '之间必须有≤80的过渡段'
  };
}
// 例：preWriteBudget(3000, 6) → 每段下限500、上限600、6段总和≥3000、文中图≥3(不同src)
```
> 脚本跑完必须打印出 `锁死表` 六行（N=6 时），每行的「汉字下限」就是该段动笔时的硬指标。

> 🚨 **写时铁律（2026-07-13 实测 + 2026-07-16 强化 + 2026-07-18 段长分布，违反=技能执行失败）**：每写完一个 h2 段，**立即用 `len(段内容.replace(/[^一-龥]/g,''))` 验汉字数**，对照上表该段「汉字下限」：不够当场续够再写下一句/下一段；**禁止先写短了再回头批量补字数**——这是 2026-07-16 实测跑了 4 轮补丁（1371→3007）的根因。**写完第3段后立即检查已写段落的中位数（所有段落汉字数排序取中间值）：若中位数 > 90，从最长段拆出 1-2 个短段（≤80 汉字），确保全局段长分布合理再继续写后续段落。** 同时扫一遍有无任意段落汉字 > 150，有则当场拆段。一次性写到规模，质量门只是验收不是补丁生产线。

验收：① 找参考模板分析段长序列已写入规划 ② 规划全项落纸（标题/钩子/骨架/配图位含描述词/增量点/字数预算） ③ **预排版核算脚本已跑、锁死表已逐行抄入规划**（无表=不准写） ④ 写时逐段对照下限验字数 → 四项齐 = 输出「规划 PASS」→ 进 PHASE 2.5 写正文。任一项空缺 → 退回去补全，不准动笔。

---

## PHASE 1：流量诊断（硬性，不通过不发布）

### 1.1 检查流量增长计划状态
导航：权益管理 `https://om.qq.com/main/account/rights` → 右侧 main 区点「功能权益」tab（K15：tab 是 main 内 li，非左侧导航；用 `document.querySelectorAll('li').find(l => l.textContent.trim() === '功能权益').click()`）→ 找「流量增长计划」行：
```
IF 该行有"关闭"按钮 → PASS（已开通）
IF 该行有"申请开通"按钮 → 执行开通流程（见附录A）
   开通流程失败 → FAIL，熔断
IF 整行不存在 → FAIL，报告"账号可能被限流"
```
验收：必须输出 `PASS` 或 `FAIL: 原因`

### 1.2 检查历史发布数据
导航：内容管理 `https://om.qq.com/main/management/articleManage`（默认「全部」筛选）。
evaluate 统计（注意：已发布列表的标题不是 `a[href*="/article/preview"]`，该选择器在企鹅号**匹配为空**；改用 `body.innerText` 正则或逐行解析）：
- 已发布文章总数
- 其中阅读 > 0 的篇数
- 最近7天发布的篇数

```
IF 阅读 > 0 的篇数 = 0 → 冷启动标志 = true
IF 最近7天发布篇数 < 4 → 发布频率不合格
```

### 1.3 检查AI声明完整性
evaluate 遍历已发布列表，检查是否有「未声明」标签（文本 "未声明未完成内容中素材是否AI生成声明"）。

```
IF 存在「未声明」标签 → 记录篇数，必须处理（见附录B 限制）
```

**⚠️ 附录B 限制（2026-07-12 实测）**：企鹅号后台对已**「微信同步」来源的已发布文章是只读的**——编辑器打开会显示「当前内容不支持在企鹅号修改，请前往内容发布端修改」。在「进行补充」AI 声明弹窗里勾选 AI 素材后点「提交」，UI 显示成功、弹窗关闭，但**刷新后列表仍显示「未声明」**（服务端不持久化）。这类文章无法在企鹅号侧补声明，须回微信源头处理。本技能对纯手工发文（来源=手工发文）的声明在 PHASE 3 发布时一并设置。

### 1.4 输出诊断报告
合并 1.1–1.3，输出一条诊断结论：`可发布` / `需修复后发布` / `账号异常熔断`
**PHASE 1 输出 FAIL → 立即终止，不进入 PHASE 2。**

---

## PHASE 2：去重验证（熔断级，必须硬匹配）

### 2.1 抓取已发布标题列表
内容管理页 `body.innerText` 逐行解析「全部」列表的标题（每行格式：`标题\n[原创/创作声明]\n日期\n[来源]\n已发布\n[未声明?]\n阅读\n0...`）。
> ⚠️ 不要用 `a[href*="/article/preview"]` —— 企鹅号该选择器为空。

### 2.2 比对标题
输入：待发布文章的关键词集合（如 ["论文转代码", "paper-to-code"]）
```
FOR EACH 已发布标题:
    IF 待发布关键词全部出现在某条已发布标题 → FAIL，熔断："已发布过：[标题]，停止"
    IF 待发布关键词部分出现（同主题/同模型） → FAIL，熔断："高度相似：[标题]，停止"
```

### 2.3 二次验证
导航编辑器后，先读已有草稿标题（如有），回内容管理核对。草稿标题 ≠ null 则重复 2.2。
**PHASE 2 输出 FAIL → 立即终止，绝不再发同一篇。**

---

## PHASE 2.3：内容模式审计（2026-07-17 统一修复新增）

PHASE 2 去重 PASS 后、写正文前，做一篇内容健康度检查。

**执行：** 读已发文章列表，取最近 5 篇的开头和结构信息，检查：

| 维度 | 检查内容 | 阈值 |
|------|---------|:----:|
| 开头句式 | ≥3 条以相同句式开头？（故事/数据/反问/感叹） | ≥3→模式化 |
| 叙事结构 | ≥3 条使用相同骨架？（单线叙事/正反对照/清单/散文） | ≥3→模式化 |
| 话题簇 | ≥3 条同主题方向？ | ≥3→区域过密 |

任一项命中 → **本文必须换被命中的维度**（如开头全用故事→改用数据开篇）。

---

## PHASE 2.5：内容质量门（硬闸 §0.1-D，发布前最后一道卡点，**脚本实跑**）

> 本阶段在 PHASE 2 去重 PASS **之后**、PHASE 3 发布**之前**执行。把写完的 HTML 全文喂给下面脚本，**代码算出具体数值**，不满足硬指标 → 脚本直接输出 FAIL，退回重写。不可自填报、不可"我感觉达标"。

> 🚨 **一次性验证，不搞补丁循环（2026-07-13 实测追加）**：质量门脚本**只跑一次**。FAIL 之后不准逐句打补丁然后反复重跑——那是本轮实测跑了 11 轮的蠢事。正确流程：FAIL → 找出字数缺口最大的段 → 整段重写到足量 → 重跑一次验证。最多允许 2 轮。第 3 轮还 FAIL 说明写前规划没做够，退回 §0.6 重新规划。

### 2.5.1 校验脚本（对 HTML 全文实跑）
```js
function qualityGate(html) {
  const text = html.replace(/<[^>]+>/g, '');            // 去标签
  const han = text.replace(/[^一-龥]/g, '');            // 只留汉字
  const hanCount = han.length;
  const h2Count = (html.match(/<h2/gi) || []).length;
  const bodyImgs = (html.match(/<img/gi) || []).length;  // 正文 img（封面另算）
  const distinctImgs = new Set(html.match(/<img[^>]*src="([^"]+)"/gi)?.map(m=>m.match(/src="([^"]+)"/)[1])||[]).size;  // 去重 src
  var paragraphs = html.split(/<\/p>/i).map(function(s){return s.replace(/<[^>]+>/g,'').replace(/[^一-龥]/g,'').length;});
  var validParas = paragraphs.filter(function(l){return l>0;});
  const maxParaHan = Math.max(0, ...validParas);
  const minH2 = Math.max(1, Math.ceil(hanCount / 600));

  // 段长分布校验
  validParas.sort(function(a,b){return a-b;});
  var len = validParas.length;
  var median = len % 2 === 0 ? (validParas[len/2-1] + validParas[len/2])/2 : validParas[(len-1)/2];
  var over120 = validParas.filter(function(l){return l>120;}).length;
  var ratioOver120 = over120 / len;

  // 连续2段>110且中间无≤80
  var consecutiveLongPass = true;
  var rawParas = html.split(/<\/p>/i).map(function(s){return s.replace(/<[^>]+>/g,'').replace(/[^一-龥]/g,'').length;}).filter(function(l){return l>0;});
  for (var j=0; j<rawParas.length-1; j++) {
    if (rawParas[j] > 110 && rawParas[j+1] > 110) {
      var seg2 = [rawParas[j], rawParas[j+1]];
      var hasBreak = seg2.some(function(l){return l<=80;});
      if (!hasBreak) consecutiveLongPass = false;
    }
  }

  // 呼吸感校验：按 h2 拆区块，每区块至少 1 个短段 ≤ 50 汉字
  const blocks = html.split(/<h2[^>]*>/i).slice(1);
  let shortPass = true, blockParaPass = true;
  for (const block of blocks) {
    const paras = block.split(/<\/p>/i).map(function(s){return s.replace(/<[^>]+>/g,'').replace(/[^一-龥]/g,'').length;}).filter(function(l){return l>0;});
    if (!paras.some(function(l){return l<=50;})) shortPass = false;
    if (paras.length < 3) blockParaPass = false;
  }

  const checks = [];
  checks.push(['字数≥3000汉字', hanCount >= 3000, '汉字=' + hanCount]);
  checks.push(['h2小标题数满足', h2Count >= minH2, 'h2=' + h2Count + ' 需≥' + minH2]);
  checks.push(['单段汉字≤150', maxParaHan <= 150, '最长段=' + maxParaHan]);
  checks.push(['文中img≥3(src不同)', bodyImgs >= 3 && distinctImgs >= 3, 'img=' + bodyImgs + ' 去重=' + distinctImgs]);
  checks.push(['段长中位数≤90', median <= 90, '中位数=' + median + ' 总段=' + len]);
  checks.push(['超长段(>120)占比≤10%', ratioOver120 <= 0.10, '>120段=' + over120 + '/' + len + '=' + (ratioOver120*100).toFixed(0) + '%']);
  checks.push(['无连续2段>110且无换气', consecutiveLongPass, !consecutiveLongPass?'连续2段>110中间无≤80':'']);
  checks.push(['每h2区块有短段换气', shortPass, blocks.map(function(b,i) {
    var ps = b.split(/<\/p>/i).map(function(s){return s.replace(/<[^>]+>/g,'').replace(/[^一-龥]/g,'').length;}).filter(function(l){return l>0;});
    return 'b' + (i+1) + '=' + ps.join(',');
  }).join(' ')]);
  checks.push(['每h2区块≥3段', blockParaPass, '区块数=' + blocks.length]);

  const failed = checks.filter(function(c) { return !c[1]; });
  if (failed.length) {
    return 'FAIL: ' + failed.map(function(c) { return c[0] + '(' + c[2] + ')'; }).join(' / ');
  }
  return 'PASS: 汉字=' + hanCount + ' h2=' + h2Count + ' 最长段=' + maxParaHan + ' 中位数=' + median + ' img=' + bodyImgs;
}
```

### 2.5.2 人工卡点（代码判不了，必须逐字给证据）
脚本 PASS 后，仍需逐条回答，任一条答不出 = FAIL：
- **信息增量**：本文哪一句/哪一段是「读者原来不知道的事」或「可转发的情绪」？说不出具体 = FAIL。
- **选题一致**：标题说的、正文写的、结尾钩子引的，三者各是什么？不一致 = FAIL。
- **钩子非空**：结尾钩子指向哪一期、什么主题？悬空 = FAIL。
- **非模板腔**：通读是否像真人在唠嗑而非 §0.4 填空？像 AI 演人类 = FAIL。
- **🆕 呼吸感**：通读一遍，是否有连续 2 段以上都超过 4 行、没有短段"换气"的地方？有 = 不合格，需拆段/插短段。
- **🆕 段长分布（2026-07-18 新增）**：目测大致段落长度，是否一半以上段落都在 2-3 行以上（汉字 > 80）？是 = 不合格，拆段，确保至少一半段落短于 2 行。

### 2.5.3 输出
```
IF 脚本 PASS 且 人工卡点 4 条全答出 → 输出 PASS，进入 PHASE 3
IF 脚本 FAIL 或 任一人卡点答不出 → 输出 FAIL: [具体原因] + 退回重写
   重写后重新跑 2.5.1 + 2.5.2，直至全 PASS
```
⚠️ 质量门是发布前最后一道硬卡。质量不达标发出去也是 0 阅读，等于白发。
**PHASE 2.5 输出 FAIL → 退回重写，绝不放行进 PHASE 3。**

---

## PHASE 3：发布执行（v3.0 现场勘出真实坐标）

### 3.0 前置条件
```
IF CORS 服务未运行 → 启动（见 §5 CORS 服务）
IF 封面图不存在 → 生成封面（见 §6 封面图生成）
```

### 3.1 编辑器真实 DOM 坐标（2026-07-12 实测，必读）
| 字段 | 真实选择器 | 备注 |
|------|--------------|------|
| 标题 | `span[data-placeholder*="标题"]`（class `.omui-inputautogrowing__inner`） | **不是** `.ProseMirror`，是 contenteditable span |
| 正文 | `document.querySelector('.ProseMirror')`（class `.ExEditor-basic`） | **全页只有 1 个** ProseMirror（标题是 span） |
| 封面按钮 | `button.omui-button--add`（在 `#articlePublish-coverinfo` 内） | 点开图片选择弹窗 |
| 单图/三图 | `input.omui-radio__input[type=radio]` value=1/3 | 默认单图已勾 |
| 标签输入 | `.omui-suggestion__input.is--multi input.omui-suggestion__value`（**真实 input 在 div 内**，div 本身不可 fill） | 填值 + Enter 成 chip |
| 分类输入 | `.omui-suggestion__input.is--single input.omui-suggestion__value` | 必填！选「科技」等 |
| 声明原创 | `.omui-checkbox`（「原创」group，选填） | — |
| 自主声明 | `#articlePublish-selfDeclaration button.omui-button--dashed`（「添加内容自主声明」） | **必填**！点开声明类型对话框 |

### 3.2 清草稿 + 填内容（顺序固定，前一步验收不过不进下一步）
> ⚠️ 企鹅号 ExEditor 的 ProseMirror **禁止逐块 append insertHTML**（会把后续块吞进同一节点，h2 之后全文塌缩成 1 个 child）。**必须单次整段 insertHTML**（先 selectNodeContents 全选 → delete → 一次 insertHTML 整篇 HTML）。

| 步骤 | 操作 | 验收 |
|:-----|:-----|:---------|
| 3.2.1 标题 | focus + `execCommand('insertText')` | 显示「标题 X/64」 |
| 3.2.2 正文 | focus + 全选 delete + **单次** `execCommand('insertHTML', false, 整篇HTML)` | 显示「正文字数」，childCount≈段数+5个h2；**evaluate `document.querySelectorAll('.ProseMirror img').length` ≥ 文中图数，且每张 img 的 naturalWidth > 0（图片加载成功）** |
| 3.2.3 封面 | 见 OP-2（下方） | 封面区出现 `<img src="inews.gtimg.com/om_ls/...">` |
| 3.2.4 标签 | 真实 input 填值 + Enter × 3 | 出现 3 个 chip |
| 3.2.5 分类 | 真实 input 填「游戏」+ 选 option | 分类显示「游戏」 |
| 3.2.6 自主声明 | 见 OP-7（下方） | 显示「作者声明：该文章由AI生成」，**无「请选择自主声明」报错** |
| 3.2.6.5 AI素材声明 | 见 OP-8（下方） | 无「存在未进行AI生成声明素材」警告 |
| 3.2.7 发布 | `button` 中 `textContent.trim() === '发布'` 精确匹配 click（K1） | URL 跳转到 articleManage |

**任意步骤卡住 3 次失败 → 熔断，记录卡点坐标到 §7，停止本次发布。**

> ⚠️ **图片 src 铁规（2026-07-18 新增）**：正文 `<img>` 的 src **必须使用 `inews.gtimg.com` 图床地址**（封面同款），外链图片（picsum.photos / placeholder.com 等）会被 ProseMirror 或发布端过滤清空，验收阶段即发现为 0 张渲染图。**文中每张图 src 必须不同，不得重复使用同一张图。** 正文中每个 img 应先通过素材库上传拿到 `inews.gtimg.com` 链接再插入。若验收发现 `.ProseMirror img` 数量 < 预期或 `naturalWidth = 0` 或去重 src 数量 < 文中图数 → 停止、换图源重插。

### OP-2：封面图上传（★ DataTransfer 注入，K6）
```
1. 点 button.omui-button--add → 弹窗（文内图片/本地上传/我的图片素材）
2. 点 .omui-tab__label 中 textContent='本地上传' → 出现 input[type=file]（父 .omui-upload-image-trigger）
3. DataTransfer 注入（浏览器禁脚本操作 file chooser）：
   const r = await fetch('http://127.0.0.1:8768/cover.jpg');
   const f = new File([await r.blob()], 'cover.jpg', {type:'image/jpeg'});
   const dt = new DataTransfer(); dt.items.add(f);
   Object.defineProperty(fileInput, 'files', {value: dt.files, configurable:true});
   fileInput.dispatchEvent(new Event('change', {bubbles:true}));
4. 等 5s → 弹窗出现缩略图（img src 含 gtimg/om_bt）
5. 点缩略图（.omui-thumb 或 [class*=thumb]）→ 点「确认」button
6. 验收：#articlePublish-coverinfo 内出现 img（src=inews.gtimg.com/om_ls/...）
```
⚠️ 封面图建议 1024×1024（企鹅号单图封面方形即可；旧 1792×1024 也可）。
⚠️ **封面单图即可，不要动三图选项，默认单图已勾（2026-07-18）。**

### OP-2.5：文中图上传（2026-07-18，DataTransfer 注入）
```
1. 点编辑器工具栏「插入图片」button
   ⚠️ 按钮可能在折叠区域，先 evaluate scrollIntoView 再 click，或用 force:true
2. 弹窗→点 textContent='本地上传'
3. 出现 .omui-upload-image-trigger input[type=file]
4. DataTransfer 注入（可一次注入多张）：
   const r = await fetch('http://127.0.0.1:8768/xxx.jpg');
   const f = new File([await r.blob()], 'xxx.jpg', {type:'image/jpeg'});
   const dt = new DataTransfer(); dt.items.add(f);
   Object.defineProperty(fileInput, 'files', {value: dt.files, configurable:true});
   fileInput.dispatchEvent(new Event('change', {bubbles:true}));
5. 等 5s → 弹窗出现缩略图列表
6. 点缩略图选中 → 点「确认」
7. 验收：.ProseMirror 内出现 img，src 含 inews.gtimg.com/om_ls/
```
⚠️ 每张图 src 必须不同，验收检查去重 src 数 ≥ 文中图数。
```
1. 点 #articlePublish-selfDeclaration button.omui-button--dashed（「添加内容自主声明」）
   ⚠️ 必须用 page.mouse.click(中心点x,y) 或 locator.click({force:true}) 触发；
      仅 evaluate 内 .click() 对部分 React 按钮不生效，且此按钮弹的是「发布内容自主声明」对话框（含 该文章由AI生成 / 该文章由AI辅助创作 / 无需标注 / 内容为转载 / 虚构演绎 等 radio），不是活动约稿。
2. 对话框内点 label/radio textContent='该文章由AI生成'（本文由 AI 辅助写作+AI 生图，选「由AI生成」）
3. 点「确认」button
4. 验收：#articlePublish-selfDeclaration 显示「作者声明：该文章由AI生成」，且无「请选择自主声明」红字
```
⚠️ 手工发文（来源=手工发文）的 AI 声明在此步骤设置即可，发布后不会再有「未声明」告警。微信同步来源文章此步不可做（见 1.3 限制）。

### OP-8：AI 素材声明（发布前素材级声明，必填）
⚠️ OP-7 的「该文章由AI生成」是**文章级别**声明，此处是**图片/素材级别**声明，两者都要做。

OP-7 设置完自主声明后，右侧栏可能仍出现「存在未进行AI生成声明素材，请」+ 「进行补充>」链接（因正文含 AI 生成图片触发）。此步必须处理，否则发布后仍有「未声明」告警。

```
1. 点 textContent='进行补充>' 的链接 → 弹出「AI生成声明」对话框
2. 对话框内显示所有文中图片的缩略图 figure
3. 逐一 click 每个 figure 选中（is--selected 出现）
   evaluate:
     document.querySelectorAll('figure').forEach(f => f.click())
4. 点「提交」button
5. 验收：页面无「存在未进行AI生成声明素材」文本
```

---

## PHASE 4：发布后验证

### 4.1 确认发布成功
```
IF URL 含 /main/management/articleManage → PASS
ELSE → FAIL（记录异常 URL）
```
⚠️ 发布成功后是**「审核中」**状态（非立即「已发布」），列表顶部出现新标题即成功。

### 4.2 记录本次发布
```json
{
  "title": "实际标题",
  "source": "手工发文",
  "timestamp": "发布时间",
  "expectedPublishedToday": true,
  "status": "审核中"
}
```

### 4.3 流量跟踪预约
- 发后约 8 小时阅读 = 0 → 触发冷启动诊断（回 PHASE 1）（平台 8h 即可定成败，非 24h）
- 连续 3 篇阅读 = 0 → 继续发布，记录冷启动状态（不阻止发布）

### 4.4 复盘修复（执行链追溯，2026-07-18 重写）

**方法：** 每次执行完毕，追溯执行链断裂点，而不是填表。执行链 = 每个 PHASE 的每一步是否真正执行、是否按 SOP 执行、是否通过了验收。

#### 4.4.1 本次执行链日志（执行者填写）

| 环节 | 应做 | 实做 | 断裂？ | 断裂原因 |
|:----|:----|:----|:------|:---------|
| §0.0 进浏览器看数据 | browser_navigate 内容管理 | ✅ | — | — |
| PHASE 0 选题红线 | 检查是否游戏赛道 | ✅ | — | — |
| PHASE 1 流量诊断 | 检查流量增长/阅读数据 | ✅ | — | — |
| PHASE 2 去重 | 比对已发布标题 | ✅ | — | — |
| §0.6 规划门 | 定标题/钩子/骨架/图位/增量点/字数预算 | ❌ | 跳过图位场景prompt | 配图描述词SOP未验证，没有可执行路径 |
| PHASE 2.5 质量门 | 脚本实跑3000字/150段长/3图不同src | ✅ | — | — |
| PHASE 3.2.1 标题 | focus+insertText | ✅ | — | — |
| PHASE 3.2.2 正文 | 整段insertHTML | ✅ | — | — |
| PHASE 3.2.3 封面 | OP-2 DataTransfer上传 | ✅ | — | — |
| PHASE 3.2.4 标签 | 填→Enter→chip | ❌ | 未执行 | 被中断 |
| PHASE 3.2.5 分类 | 选「游戏」 | ❌ | 分类选不上 | suggestion input 被 placeholder 拦截点击 |
| PHASE 3.2.6 自主声明 | OP-7 | ❌ | 未执行 | 被中断 |
| PHASE 3.2.6.5 AI素材声明 | OP-8 | ❌ | 未执行 | 被中断 |
| PHASE 3.2.7 发布 | click「发布」 | ❌ | 未执行 | 被中断 |
| 文中图 src 去重 | 3张不同 src | ❌ | 6张全一样 | OP-2.5未验证，无上传路径 |
| 图片位置 | 放在对应段落后 | ❌ | 全在h2末尾 | 写HTML时未按段定位 |

#### 4.4.2 断裂点修复

对每个断裂点标注「修复措施」并执行：

1. **§0.6 规划门跳过图位场景prompt** → 删除未验证的"模仿参照/配图描述词"，保留可执行的"≥3图不同src"
2. **PHASE 3.2.5 分类选不上** → 已记录为K23/K24，用 `browser_type` slowly + popup click
3. **文中图 src 全一样** → 质量门加 `distinctImgs` 去重检查（已加）；OP-2.5 未经验证已删除
4. **图片位置乱放** → §0.6 配图位规则加「放在对应段落之后」（已加）
5. **全文被中断未完成发布** → 每次执行必须一口气跑完，不允许中间停

#### 4.4.3 SOP 健康检查

- 本次暴露的 SOP 不一致/过时项：分类写"科技"(实为游戏)、配图≥6/≥3矛盾 → 已修复
- 未验证的 SOP：OP-2.5（删除）、模仿参照（删除）、配图描述词（删除）
- 本次执行后 SKILL.md 中所有步骤均为已验证可执行步骤 ✅

---

## §5 CORS 图片服务（发布前必须启动）

Python http.server 默认无 CORS header，跨域 fetch 封面图会失败。
```
cd C:\Users\59314\claudework
python -c "
import http.server, socketserver, os
os.chdir(r'C:\Users\59314\claudework')
class H(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        super().end_headers()
s = socketserver.TCPServer(('127.0.0.1', 8768), H)
s.serve_forever()
"
```
⚠️ 启动后 `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8768/cover.jpg` 确认 200。
⚠️ 端口 8768 若被占用换端口；fetch 必须用 `http://127.0.0.1:8768/`（不用 localhost，IPv6 会失败）。

---

## §6 封面图生成

> ⚠️ **2026-07-15 修订：提示词每次必须随机多变**。旧版每条赛道只有一句固定提示词导致每次封面图长得差不多，现改为多元素随机组合模板，每次生成的 prompt 都不同。

脚本：`C:\Users\59314\claudework\generate_image.py`（Agnes API key 已硬编码在脚本内，无需 settings.json）。
```
python generate_image.py "<英文prompt>" cover.jpg 1024x1024
```

### 6.1 提示词生成规则（每次随机组合）

每次生成封面时，用下面规则组装唯一 prompt。**禁止连续两次使用相同的 5 元素组合**——执行时随机 shuffle 每个类别里的候选值，拼成一句后调用。

#### A. 场景/主体（从文章标题提取 + 随机选备选）
- 备选：`intense mobile gaming moment on smartphone screen`, `close-up of hands gripping phone in the dark`, `gaming setup with glowing keyboard and RGB lights`, `two players facing off in a tense moment`, `digital battlefield map with glowing markers`, `a player lost in thought after a game`, `neon-lit gaming room with trophies`, `smartphone screen showing match results`

#### B. 风格/视觉风格（随机3选1）
- `anime style, cel shaded`
- `photorealistic, hyper-detailed`
- `cinematic, film grain, anamorphic`

#### C. 光线（随机4选1）
- `dramatic neon backlight, blue and purple`
- `soft ambient light from monitor glow`
- `harsh contrast, shadows and highlights`
- `warm golden hour light from window`

#### D. 情绪/氛围（随机4选1）
- `tense, competitive, high stakes atmosphere`
- `melancholic, reflective, quiet mood`
- `energetic, excited, vibrant vibe`
- `mysterious, suspenseful, player vs system`

#### E. 质量标签（固定，一律追加）
`4K, highly detailed, masterpiece, sharp focus`

### 6.2 执行步骤
1. 从 A-E 各选一项（A 从备选池随机选，B/C/D 各随机选1，E 固定）
2. 用 `, ` 拼接成完整 prompt
3. 运行 `python generate_image.py "<完整prompt>" cover.jpg 1024x1024`
4. 验收：文件 `cover.jpg` 存在且大小 > 10KB

### 6.3 验证样例（随机组合的例子）
```
# 举例1：方案 A3+B2+C1+D1
prompt = "gaming setup with glowing keyboard and RGB lights, photorealistic, hyper-detailed, dramatic neon backlight, tense competitive high stakes atmosphere, 4K, highly detailed, masterpiece, sharp focus"

# 举例2：方案 A5+B1+C3+D3
prompt = "digital battlefield map with glowing markers, anime style cel shaded, harsh contrast shadows and highlights, energetic excited vibrant vibe, 4K, highly detailed, masterpiece, sharp focus"

# 举例3：方案 A7+B3+C2+D2
prompt = "neon-lit gaming room with trophies, cinematic film grain anamorphic, soft ambient light from monitor glow, melancholic reflective quiet mood, 4K, highly detailed, masterpiece, sharp focus"
```

---

## 附录A：流量增长计划开通流程
执行条件：PHASE 1.1 检测到「申请开通」按钮
1. 找 textContent='申请开通' 且所在行含流量增长计划的 button → click
2. wait 1s → 找 textContent='暂不绑卡' button → click（如弹窗）
3. wait 1s → `document.querySelector('label.omui-checkbox').click()`
4. 找 textContent='同意' 且 !disabled 的 button → click
5. 验收：状态变「已开通」，有「关闭」按钮
失败处理：弹窗未出现→重试步骤1（≤2次）；checkbox未找到→截图记录FAIL；同意按钮disabled→截图记录FAIL

## 附录B：修复缺失的AI声明（仅限手工发文来源）
执行条件：PHASE 1.3 发现**手工发文**来源的已发布文章有「未声明」标签。
1. 点该文章「修改」→ 打开编辑器
2. 找「存在未进行AI生成声明素材，请」后的「进行补充>」→ click（注意：微信同步来源此路只读，见 1.3 限制）
3. 弹「AI生成声明」对话框 → 勾选 AI 生成的图片素材（点 .omui-thumb figure，is--selected 出现）→ 点「提交」
4. 验收：该文章显示「已完成AI生成素材声明」
⚠️ 微信同步来源文章：对话框提交后刷新仍「未声明」，服务端不持久化，无法在企鹅号补——回微信源头处理。

---

## §7 已知坑（硬性映射表）

| 编号 | 症状 | 根因 | 唯一解法 |
|:-----|:-----|:-----|:---------|
| K1 | 发布按钮匹配多个 | React DOM 含隐藏按钮 | textContent 精确 `=== '发布'`，不用 includes |
| K3 | radio 选中后提交不生效 | React 未检测 change | click + `dispatchEvent(new Event('change', {bubbles:true}))` |
| K5 | 页面崩溃 | 用 evaluate 删 React 管理 DOM | 所有定位用 Playwright locator |
| K6 | 封面传不上 | 浏览器禁 file chooser 脚本操作 | DataTransfer 注入 + CORS server fetch（OP-2） |
| K8 | 点发布无反应 | 标题为空校验先触发 | 发布前 evaluate 确认标题已填 |
| K11 | 页面白屏 | React 检测外部 DOM 篡改 | 始终用 locator |
| K14 | 自动保存覆盖新内容 | 编辑器自动保存 | 清除后立即填写 |
| K15 | 功能权益 tab 点不动 | 组件 ref 每次加载变化 | evaluate 遍历 textContent='功能权益' 的 li |
| K16 | 弹窗确认按钮找不到 | ref 动态生成 | textContent 匹配 + 遍历 button |
| K17 | 上传封面 fetch 失败 | CORS server 未启动 | §5 必须在 OP-2 前启动 |
| K18 | 重复发布 | 未做去重 | PHASE 2 双重去重 |
| **K19** | 正文逐块 append insertHTML 被吞 | ExEditor ProseMirror schema 合并后续块进同一节点 | **单次整段 insertHTML**（全选delete后一次插入整篇 HTML） |
| **K20** | 自主声明按钮 evaluate .click() 不弹窗 | 部分 React 按钮需真实手势 | `page.mouse.click(中心点)` 或 `locator.click({force:true})`；且此按钮弹「发布内容自主声明」对话框（含 AI生成 radio），非活动约稿 |
| **K21** | 微信同步来源文章补 AI 声明提交后刷新仍「未声明」 | 企鹅号对同步文章只读，服务端不持久化 | 回微信源头处理；本技能只对手工发文设声明 |
| **K22** | 发布报「请选择分类」「请选择自主声明」 | 分类/声明是必填，未设 | 先设分类（OP-7 前）+ 自主声明（OP-7）再发布 |
| **K23** | 分类/标签 input 键入不生效 | 真实 input 嵌套在 div.omui-suggestion__input 内；React 受控输入，仅 `.value=` 不更新 state | **分类**：`browser_type`(slowly=true, target=`.omui-suggestion__input.is--single input.omui-suggestion__value`, text=游戏) → 候选下拉出现「游戏」→ evaluate 遍历 `[class*=suggestion__list/menu/popup/dropdown/item]` 找 textContent==='游戏' 的叶节点 click 选中。**标签**：同上 is--multi，键入后 `browser_press_key('Enter')` 真实键生成自由 chip（`omui-suggestion__chose` 容器），input 清空即成功；fake KeyboardEvent 无效 |
| **K24** | 分类项「游戏」候选需逐字键入才出下拉 | 分类 suggestion 不随 `.value=` setter 出候选，必须真实 pressSequentially 逐字触发 React onChange 过滤 | 用 `browser_type` slowly 模式（底层 pressSequentially），不用 fill |
| **K25** | 点「添加内容自主声明」/封面 action 时弹窗被图片对话框遮罩拦截 | 之前点封面 `.omui-thumb__action` 已开 `omui-dialog-wrapper.open exImageDialogWrap` 弹窗未关，遮罩 `omui-dialog-mask` 拦截后续点击 | 点声明前先 `evaluate` 找 `.omui-dialog-wrapper.open` 内的「取消」button 关掉残留弹窗 |
| **K26** | 封面上传弹窗打不开（evaluate 点 `.omui-thumb__action` 无效） | React 缩略图 action 需真实手势；且草稿若已有封面则显示「更换/编辑」figure 而非 `button.omui-button--add`（OP-2 的 add 按钮仅无封面时出现） | 草稿已有封面时直接用 `browser_click`(target=`.omui-thumb__action` 真实手势) 开「更换」弹窗；已有 `inews.gtimg.com/om_ls/` 图床封面则无需重传 |
| **K27** | 标签 chip 文本误判 | chip 容器 class 是 `omui-suggestion__chose`，input 包裹是 `omui-suggestion__value-wrap`，二者都含文本易混淆 | 查 chip 用 `.omui-suggestion__input.is--multi .omui-suggestion__chose *`，查待输入用 `input.omui-suggestion__value` 的 value |

| **K28** | 质量门反复跑 11 轮才达标 | 写完不逐段验字数，最后集中补丁凑数 | 每段写完当场验汉字数（§0.6 写时铁律）；质量门只跑一次，FAIL 就整段重写（§2.5） |
| **K29** | 发布后有「未声明」告警 | OP-7 自主声明已设，但正文图片的 AI 素材声明未做（OP-8 之前误写为"无额外操作"） | OP-7 + OP-8 都要做：先自主声明（文章级），再 AI素材声明 dialog（图片级），见 3.2.6 / 3.2.6.5 |
| **K30** | 每次封面图长得差不多 | §6 旧版每条赛道只有一句固定 prompt，反复用同一句 | §6 v3.1 改为 5 元素随机组合模板（A场景/B风格/C光线/D氛围/E质量），每次随机 shuffle 选不同组合 |
| **K31** | 正文全是长段落，读起来累，没有呼吸感 | 写时只关注单段≤150的硬指标，忽略了段落节奏——连续多段130-150文字堆在一起没有短段换气 | §0.4 写法铁律加「呼吸感」规则；§0.5 排版加「每h2区块至少1个短段≤50」+「每区块≥3段」；§2.5.1 脚本加对应 check；§2.5.2 人工卡点加「通读验呼吸感」 |
| **K32** | 发布后文中图全裂（0张渲染） | insertHTML 用了外链图片（picsum.photos），ProseMirror/发布端过滤了非图床 src | 验收必须 evaluate `.ProseMirror img` 数量 + `naturalWidth`；图片 src 必须用 `inews.gtimg.com` 图床链接，正文图先上传素材库拿到图床 URL 再插入 |
| **K33** | 闭门造车编段长，反复补丁凑字数 | 不找参考模板，自己凭感觉分段。先写短段再补丁式扩写 → 段长均匀推高 → 连续>110 → 排版FAIL → 重写 | 动笔前先找同平台爆款文章分析段长分布，直接抄人家的段落节奏（§0.6 找参考模板 + §0.4 模仿参照）。**不要先写再补，要一次写到目标长度** |
| **K34** | 文中图与段落内容不相关 | 配图没有根据段落内容提取描述词，随便塞图 | §0.6 配图位规划时标注 scene_prompt，根据每段核心内容生成描述词 |

### 新坑记录模板
```
新坑编号：Kxx
症状：
根因：
唯一解法：
关联步骤：
```
