---
name: toutiao-article
description: 今日头条(头条号)全品类生活攻略文章自动定时发布。每日2篇，Agens配图，排版硬闸。v7.14
exec_mode: strict_linear
---

# 今日头条 · 生活攻略类文章定时发布（v7.14 — 标记锚定 relocate 取代 DOM 结构猜测，杜绝图片割裂句子）

🚨 第一原则：读者视角 > 一切。 每一段话写完后问自己：读者看完这段得到什么？如果答案是"没有实际帮助"或"只是在凑字数"——删掉。不写"看起来有用但读完没收获"的废话。不写只有自己懂的行话。标题承诺了什么，正文必须兑现。读者刷头条是来找答案的，不是来被你教育的。

线性执行，不可跳跃。 Phase 0（去重+方向摸底）→ Phase 0.5（热点研究，核心）→ Phase 1（选题）→ Phase 2（发布）。每 Phase 做完检查清单全部打勾再进下一 Phase。

🚨 选题核心规则 — 热点优先：头条流量靠蹭热度。选题顺序：今天有热点→全押热点；没适合转生活攻略的热点→回方向数据选高表现方向。数据只是保底，热点才是主力。不依赖直觉、不参考不可靠的记忆。

Phase 自检不通过 → 退回上一步修正，不自欺跳过。不编造、不估算、不跳过。

禁止使用任何 API 操作（包括 save-xhr）。 save-xhr（/mp/agw/article/publish）调用后会在账号中创建一篇新草稿。所有操作必须通过 UI 完成。UI 定时成功标志是 URL 跳转到 /graphic/articles，不需要获取 pgc_id。

🚨 字数硬性规则（不可违反）：正文汉字≥1500，不设上限。每段汉字≤80（目标≤60）。底线是熔断判据不是写作目标。写前先做段落预算（55-75段×段均≈1500），算不够不落笔。核验必须用 `text.match(/[一-鿿㐀-䶿豈-﫿]/g)` 计汉字，禁止用 `len(str)` 或 `charCount` 代替。写完后汉字不足→整篇删掉重写，重新做段落预算后再落笔。

🚨 XHR 定时发布已废弃。 timer-publish.js / XHR timer-publish 不携带 UI 开关状态（广告/首发/收益/观点声明/配图）。所有设置必须在 UI 完成后，点击页面「定时发布」按钮走 UI 弹窗流程。

🚨 禁止制造草稿。 正文填入发布页后必须走完定时流发布，不得中途弃页。任何原因中断（报错/中断/重启）导致发布页有未发布内容时，必须清除正文/标题再离开页面，否则头条自动保存为草稿。

🚨 严禁刷新发布页。 正文和标题已写入编辑器后，不得使用 browser_navigate 或 page.reload 刷新发布页——刷新后ProseMirror编辑器内容丢失，且头条自动保存草稿。定时弹窗出问题时，关闭弹窗（点取消或×）后原地重试，不刷新、不导航离开。

🚨 正文通过 `browser_run_code_unsafe` 中 `page.evaluate` 一次性写入 `.ProseMirror`。写入后立即核验字数，字数不对不得继续。

## 🚨 账号定位与内容策略

账号名称：实用生活攻略馆 — 全品类生活攻略号，覆盖衣食住行+社会民生+生活观察。

### 内容覆盖范围

本账号不限单一方向，从生活攻略角度切入以下所有领域：

| 大类 | 具体方向 | 示例选题 |
|------|----------|----------|
| 🍚 食 | 厨房技巧、备餐、省钱买菜、食物保存、厨具测评 | 备餐技巧/冰箱收纳/剩菜处理 |
| 👔 衣 | 衣物护理、洗涤技巧、收纳整理、旧物改造、穿搭省钱 | 瓶罐改造/旧衣改制/洗涤避坑 |
| 🏠 住 | 居家收纳、清洁技巧、装修避坑、租房维权、家电使用 | 装修增项/租房押金/电器省电 |
| 🚗 行 | 出行省钱、机票攻略、通勤技巧、自驾准备 | 机票什么时候买/通勤省钱 |
| 📰 社会事件 | 民生政策解读、社保医保、消费维权、辟谣防骗 | 医保报销/消费退款/政策新规 |
| 👴 生活观察 | 老人行为观察、身边小事、普通人反差故事、人情世故 | 老人节俭/邻里小事/职场人际 |
| 💰 省钱理财 | 省钱技巧、理财入门、副业避坑、消费观念 | 工资分配/信用卡积分/副业避坑 |
| 🧠 职场成长 | 职场沟通、加薪谈判、人际边界、入职适应 | 拒绝甩锅/领导批评/新入职融入 |

### 🚨 选题三大来源（按优先级）

**🥇 来源1：社会热点 + 民生事件（首选，蹭热度才有流量）**
社会新闻从"普通人生活攻略"角度切入。政策变化第一时间解读（社保/医保/房产/教育）。热点是壳，生活攻略是核——把热点变成对读者有用的内容。

**🥈 来源2：自身经历 + 身边观察**
你今天遇到的事/看到的事/听到的事；你家、你朋友家、你同事家的生活场景。真实经历写出来最有共鸣。

**🥉 来源3：搜索结果 + 用户需求**
头条创作灵感/巨量算数搜趋势；评论区看读者在问什么、苦恼什么；搜索关键词看什么话题有持续需求。

### 尾流效应（热点内容）

头条对蹭热点的文章，首日爆发流量远大于常青内容。发布后 6-12 小时是推荐高峰，好的选题能在当天冲到几万阅读。热点内容不需要"慢慢养"——只要踩中平台当前推荐的热点词，首推就给你量。但热点退得也快，所以选题必须紧追最新趋势，不做"一个月前的热点"。

## PHASE 0：硬性去重 + 方向摸底（不可跳过，必须先执行）

执行时机：每次启动本技能、写任何内容之前。必须先到已发布列表页获取最近 6-8 篇文章的数据（去重用）。方向数据只作为 Phase 0.5 无热点时的保底参考，不主导选题——热点优先。

**步骤**

### 0.1 数据采集

1. 导航到作品管理/已发布内容页：`browser_navigate('https://mp.toutiao.com/profile_v4/manage/content/all')`
2. 翻页：先看第 1 页，再点第 2 页（.fake-pagination-list li 索引 2），共采集 6-8 篇。
3. 从 snapshot 提取每篇的：
   - 标题
   - 发布时间
   - 分类方向（对照 §内容覆盖范围 的 8 个大类）
   - 数据指标：**展现量 / 阅读量 / 点赞数 / 评论数**
   - 阅读率 = 阅读量 ÷ 展现量（有展现才有意义）

### 0.2 数据分析表

采集后，构建分析表（以下为示例格式，脑中完成）：

| 标题 | 方向 | 展现 | 阅读 | 阅读率 | 日期 |
|------|------|------|------|--------|------|
| ... | 🍚食 | 661 | 26 | 3.9% | 07-13 |
| ... | 🧠职场 | 1403 | 33 | 2.4% | 07-12 |
| ... | ... | ... | ... | ... | ... |

### 0.3 数据判断

基于分析表，判断以下结论，**全部记录，不可跳过**：

✅ **高表现方向判定标准（满足任一条）：**
- 展现量 ≥ 500 且阅读率 ≥ 2%
- 或展现量 ≥ 1000（标题吸引推荐）
- 或同方向有多篇展现均 ≥ 300（方向稳定）

❌ **低表现方向判定标准（满足任一条）：**
- 连续 2 篇展现 < 300
- 或阅读率 < 0.5%
- 或同方向 3 篇以上均 ≤ 200 展现

**结论输出（必须产出后才进入 Phase 0.5）：**
- 验证的高表现方向：_______
- 已证实的低表现方向：_______
- 待测试方向（近期未写过、也无数据支持的方向）：_______

### 0.4 去重比对

基于采集的标题，执行比对：
- 新标题不能和这 6 篇的标题完全相同
- 新标题不能和这 6 篇的选题角度高度重叠（同一件事/同一主题/同一模型名）
- 有重叠 → 换主题或改角度

**铁律**
- 每次启动必须先执行，不做就去写内容 = 流程违规。
- 不依赖记忆或历史记录——必须实时从页面看数据。
- 没有分析数据就选题 = 盲目生产，属于流程违规。

## PHASE 0.5 · 热点研究（不可跳过）

**前置条件：** 选方向前必须先看今天有什么热点。热点优先级始终高于方向数据——即使方向数据差，只要热点够热 + 能转生活攻略角度，就值得写。

**来源：** 头条热榜 + 微博/Reddit/百度热点 至少各 1 条。超过 3 天的不追。

## PHASE 1 · 选题策划

**核心原则：热点优先 > 方向数据。** 有热点蹭热点，没热点才回到方向数据选方向。

**选题优先级（严格按此顺序执行，不可跳过前一条就往下走）：**

1. 🥇 **有热点 → 全部押热点** — 今天 Phase 0.5 搜到热点了，2 篇都从热点走。能从热点里挖出 2 个不同生活攻略角度就是最佳方案（比如医保新规→①怎么报销 ②怎么省钱）。如果只挖出 1 个可用角度，第 2 篇再去方向数据里找。
2. 🥈 **无热点 → 回方向数据** — Phase 0.5 看完头条热榜/微博热搜/百度热点，前 10 条都不适合转生活攻略 → 回 Phase 0 的高表现方向，从中选 1-2 篇。
3. ❌ **不投** — 低表现方向不投，待测试方向只在确实没有热点、高表现方向也写完了才投 1 篇试水。

每篇确定：标题（用标题公式）、方向、定时时间（明天 06:00 或 18:00）。

### Phase 1 自检
- [ ] 热点已查（至少 2 个来源：头条热榜/微博/Reddit 等）
- [ ] 无热点→回了方向数据（高表现方向优先）
- [ ] 无 AI 相关标题/角度
- [ ] 与已发布的最近 6 篇无重复
- [ ] 标题用了数字 + 场景/人群词
- [ ] 热点选题：确认头条上这个话题还没铺天盖地（自查即可）

全部满足 → 进入 Phase 2。缺任一项 → 退回重选。

## PHASE 2 · 逐篇执行

**INPUT：** 已选定的 2 篇主题（标题 + 方向 + 定时时间）

⚠️ 入口检查
- [x] 已去重：与已发布最近 6 篇不冲突
- [x] 选题来源已确定：热点优先 / 方向数据保底
- [x] 已选题：2 篇可同方向（热点方向允许同向）或不同方向

### 执行前确认

- [ ] 浏览器上最近 6 篇标题已扫过
- [ ] 新标题不重复
- [ ] 位置是否已设为上海（Step 2 中已默认设置，若需其他城市改调用参数）

### Timeline 每日定时发布

执行时间：当天执行，定时到**明天**发布。scheduled_time = 明天日期 + 06:00 或 18:00。
如果今天 07-15，明天 07-16 → 两篇分别定时到 07-16 06:00 和 07-16 18:00。

操作流程全部自包含在 SKILL.md 中，不依赖外部脚本文件。直接使用下方「逐篇模板」的完整代码执行。

### 逐篇模板（精确可执行代码 + 日期预处理）

每篇执行前，根据当前日期计算明天日期，格式化为 MM月DD日，小时提取为纯数字。
示例：今天 2026-07-15 → 第一篇 date = "07月16日", hour = "6"（06:00 时段）；第二篇 date = "07月16日", hour = "18"（18:00 时段）。
替代下方代码中的 {date} 和 {hour}。

每篇执行时，将下方代码逐段复制到对应 MCP 工具中执行。所有选择器均为固定坐标，不可猜测替换。

### Step 1 — 打开发布页

```
MCP: browser_navigate('https://mp.toutiao.com/profile_v4/graphic/publish')
```

→ 页面签名检查（执行以下 evaluate 脚本，全部通过才继续）

```javascript
// 页面签名可执行检测
var sigCheck = await page.evaluate(function() {
  var r = { ok: true, fails: [] };
  // 1. URL
  if (!location.href.includes('/profile_v4/graphic/publish')) { r.ok=false; r.fails.push('URL不匹配'); }
  // 2. ProseMirror
  if (!document.querySelector('.ProseMirror')) { r.ok=false; r.fails.push('.ProseMirror不存在'); }
  // 3-8. DOM文本检查
  var texts = ['展示封面','投放广告','作品声明','预览','定时发布','预览并发布'];
  texts.forEach(function(t) {
    if (!document.body.innerText.includes(t)) { r.ok=false; r.fails.push('缺少文本:'+t); }
  });
  // 9. 按钮顺序
  var btns = document.querySelectorAll('button');
  var order = [];
  btns.forEach(function(b) { var t=b.textContent.trim(); if(t==='预览'||t==='定时发布'||t==='预览并发布') order.push(t); });
  var expected = ['预览','定时发布','预览并发布'];
  for (var i=0;i<expected.length;i++) { if (order[i] !== expected[i]) { r.ok=false; r.fails.push('按钮顺序错误'); break; } }
  return r;
});
if (!sigCheck.ok) { throw new Error('PAGE_SIG_FAILED: ' + sigCheck.fails.join(', ')); }
console.log('✅ 页面签名通过');
```

### Step 1.5 — 生成正文（直接在头条编辑器写，不是生HTML再贴）

🚨 **正文中禁止出现任何 `<img>` 标签。图片必须通过 Step 1.6 的 `browser_drop` 上传。** 直接在 innerHTML 中写 `<img src="CDN_URL">` 会导致图片加载失败（头条CDN需上传流程的认证）。正文只用纯文字段落 + 用 `<p><br></p>` 作为图片占位。图片上传和插入全部走 Step 1.6。

**第1步：查上一篇的钩子/框架/结尾类型**

回顾在浏览器里看到的最近1篇已发布文章的写法，判断它用的 hook_type / narrative_framework / ending_type。
本篇必须选不同的。同类型 → 重新选，不进入生成。

**第2步：写正文 + 代码预算硬闸（先算后写，预算不过不落笔）**

**2a. 写正文（在对话中输出 HTML）**
按下方强制模板撰写全文 HTML，段落预算参考下表：

| 段落区块 | 预算段数 | 段均汉字 | 小计汉字 |
|---|---|---|---|
| 开头钩子 | 2-4 | 35 | 70-140 |
| 方法1 主体 | 10-18 | 25 | 250-450 |
| 方法2 主体 | 10-18 | 25 | 250-450 |
| 方法3 主体 | 10-18 | 25 | 250-450 |
| 中段钩子 | 2 | 20 | 40 |
| 对比总结 | 5-8 | 30 | 150-240 |
| 结尾收束 | 2-4 | 25 | 50-100 |
| **合计** | **45-85** | — | **≥1500** |

**2b. 🚨 代码预算硬闸（不可跳过。预算不够→退回2a扩充，不进入2c）**

写完后，把正文 HTML 粘贴到以下 Python 命令中执行，计汉字数：

```bash
python -c "
import re, sys
html = '''此处替换为正文HTML'''
chinese = re.findall(r'[一-鿿㐀-䶿豈-﫿]', html)
count = len(chinese)
if count < 1500:
    print('BUDGET_FAIL: 预算' + str(count) + '汉字，不足1500，退回扩充')
    sys.exit(1)
else:
    print('BUDGET_PASS: 预算' + str(count) + '汉字 ≥1500')
"
```

预算不通过（BUDGET_FAIL）→ 退回 2a 扩充内容后重新预算，**不得直接写入编辑器**。
预算通过（BUDGET_PASS）→ 只允许进入 2c。

**2c. 写入编辑器**

直接写到页面上的 .ProseMirror 编辑器里，用 `pm.innerHTML = html` 一次性写入整篇。写入后 dispatch input 事件触发状态更新。

**🚨 正文写入后核验（兜底，与 2b 形成双保险）。** 用 `text.match(/[一-鿿㐀-䶿豈-﫿]/g)` 统计汉字数≥1500。不足时**不得在末尾追加段落、不得原地补内容**，必须删掉整篇，**回到 2a 重新做段落预算**，按预算扩充内容后重走 2b→2c。

⚠️ 写作时遵循下方强制模板——必须逐行遵循，不能当参考资料。

```
【强制段落结构模板 v2 — 2026完读率优化版】

全文字数硬性 ≥1500 汉字（最低1500，上不封顶）。
正文段落总数 45-85 段（仅计对开 `<p>`，不含图片 DIV）。
「段」指 `<p>...</p>`。每段目标 20-60 汉字，不超过 80 汉字（手机端超过 4 行=划走）。超过 60 汉字必须拆分。
「中段钩子」指：在文章约300字和600字处各埋一个互动钩子（反问/悬念/预告）。

===== 拆句规则 =====
- 普通正文默认「一个完整句号段一段」：每句以 。！？ 结束后换段，标点保留在段尾。
- 步骤/案例允许连续 2 句合为 1 段，但合计不得超过 60 汉字。
- 小标题、图片、引用块保持原结构，不参与拆句。
- 禁止空段、点号段、Markdown 标题泄漏、强行拆碎短语。

===== 呼吸点规则（2026一句段版） =====
每 6-8 个纯文字段后安排图片、短总结或自然转折，不再制造无意义短段作为"呼吸点"。——正文拆句后天然节奏密集，呼吸点由配图和标题段落承担。

===== 口语化铁律（2026头部账号核心差异） =====
🚨 写完每段后大声读出来——如果听着像"老师在讲课"，重写。
- 禁止书面修辞：然而、因此、综上、由此可见、值得注意的是、不难发现
- 强制口语连接词：说白了、其实、结果、后来、说实话、你猜怎么着
- 短句为主：一句话不超过2个逗号，超过就拆成两句
- 数据要具体："省了187块" 比 "省了不少" 有效10倍
- 案例要有人物："我一个做装修的朋友老王" 比 "有研究表明" 有效10倍

===== 加粗策略（全篇仅3处） =====
🚨 2026头部账号加粗策略：全篇只加粗3处，放在最炸裂的金句/结论上。
- ❌ 错误：每个小标题都加粗（5-7处 = 没有重点）
- ✅ 正确：只加粗3处——最反常识的结论 / 最有用的操作步骤 / 最扎心的金句
- 小标题不用<strong>，用自然段落即可（读者扫读时小标题本身已醒目）

===== 中段钩子（2026新增，完读率提升40%） =====
在文章约300字处和600字处各插入1个"中段钩子"：
- 类型1（悬念预告）："但真正让我惊讶的，是第三个方法……"
- 类型2（反问互动）："看到这里你可能会问：这真的有用吗？往下看。"
- 类型3（数据预告）："有个数据你可能想不到——后面会说到。"
中段钩子 = 独立短段（≤25字），前后各空1段。

===== 对比表格（攻略类文章必备） =====
生活攻略类文章必须包含至少1个对比表格，用 <table> 或结构化文字呈现。
示例：
"旧抹布 vs 旧T恤：吸水性差3倍，还掉毛。"
表格让读者一眼抓到重点，完读率比纯文字高35%。

===== 全文结构（精简4段式，适配硬性≥1500汉字） =====

【段1-2】开头钩子（前200字铁律：必须含"具体场景+具体数字+反常识结论"中至少2个）
- 开头前30字必须有钩子（7种之一）。不能铺垫、不能渲染气氛。
- 直接抛出场景/数据/颠覆认知/自嘲/故事/痛点/反常识。
- 第1段≤60字。第2段过渡，≤80字。
- 前200字内必须出现至少1个具体数字（"187块""3倍""4分钟"）。

【段3起】方法主体（3个方法，每个方法 10-18 段，一句一段为主）
- 步骤/案例允许连续 2 句合为一段（≤60 汉字），其余按句号换段。
- 每个方法必须：
  - 至少有1个具体案例（"我一个朋友""我一个同事"）+ 具体数字
  - 方法末尾用口语化短句过渡到下一个（"但下面这个更省事"）
- 第1个方法结束后插入【中段钩子1】。
- 第2个方法结束后插入【中段钩子2】。

【对比总结】对比总结（5-8 段，用表格或对比句呈现）
- 方法优劣对比 / 使用前后对比 / 花费对比
- 让读者一眼看到"用这个方法值不值"

【结尾】（2-4 段，4种之一，连续两篇不同类型）
- ❌ 绝对禁止：'评论区说说''来评论区说说''你学会了吗''你觉得呢''评论区见''转发给需要的人' 以及 '不妨试试''要不你也试试''下次试试看''你也行动起来吧'
- ✅ 允许的4种：
  1. 闭环感悟型 — 回到开头故事/场景，轻收
  2. 数据验证型 — 用自家效果收尾（"去年X，今年Y"）
  3. 延伸思考型 — 留一个值得想的角度
  4. 自嘲总结型 — 用自己收尾
- 结尾1-2段自然收束，不超过100字。
- 结尾前一段可加一个微互动："你家有没有这种'留着没用扔了可惜'的东西？"（开放性问题，不强制）

===== 配图位自动插入（2026-07-24 自动 relocate 替代手工标记） =====
不再需要在正文中写 `【图1】` 标记。relocate 脚本自动统计全文纯文字段落数 N，按 25%/50%/75% 三档计算段落索引，把 3 张图分别插到对应的段落后。写出干净的 HTML 即可，不嵌任何标记文字。
- 第1张图在全文 25% 段落处（第2-4段后），但**不得在第1段之后立即插入**（开头至少要有2段连续纯文字建立阅读节奏后，才用图片打断）
- 第2张图在 50% 段落处
- 第3张图在 75% 段落处
- 最后3段不能有图（结尾清洁）
- **全文配图固定 3 张**（1500字文章标准）。3张图分别落在全文段数的 25%、50%、75% 位置，形成均匀呼吸节奏。
```

**第4步：产出后核验（硬核，不过不进入下一步）**

1. 编辑器内汉字数必须 ≥1500。核验用 `text.match(/[一-鿿㐀-䶿豈-﫿]/g)`，禁止用总字符数代替。不足→整篇删掉重写，重新做段落预算后再落笔。
2. 正文中无 '评论区说说' & '来评论区说说' & '你学会了吗' & '你觉得呢' & '评论区见' & '转发给需要的人'
   **以及** 无 '不妨试试' & '下次试试看' & '要不你也试试' & '你也行动起来吧' 类祈使句结尾
3. 每个 <p> 内容的汉字数 ≤80（目标≤60，核验工具逐段检查；超过60必须拆分）
4. 总段数 45-85 个正文段（一句段模式）
5. 无段超过2个逗号（核查每句逗号数，枚举用顿号）
6. 前50字有钩子（自嘲/场景/数据/痛点 之一）
7. 结尾无禁止句式
8. 最后3段无图片（插入Agens图后核验）

任一项不通过 → 不继续，在编辑器中修改后重新核验。

### Step 1.6 — Agens 配图生成（只负责生成，不直接插入编辑器）

【执行流程】

Agens API：POST https://apihub.agnes-ai.com/v1/images/generations
模型：agnes-image-2.1-flash
Key（硬编码）：sk-37fc8R90O1p5YQy7py4vQpmbWywfsnqg3qLJxxJg2cO8y3Ui

1. 从正文中提取 3 段场景描写作为配图 prompt（分别对应 25% / 50% / 75% 位置附近的画面）。规则：把正文中最具画面感的 3 句话分别提炼成英文 prompt（保留写实摄影风格+中国场景+自然光暖色调）。不是自己编场景，是从正文里找。**必须用英文 prompt（避免 Windows shell 编码问题）**。

2. 🚨 用 Python requests 调 Agens API（禁止用 curl —— Windows 下 curl 传中文 prompt 会因 UTF-8 编码问题报 surrogates not allowed）。每张设置 timeout=120s：

```bash
python -c "
import requests, json
r = requests.post('https://apihub.agnes-ai.com/v1/images/generations',
    headers={'Authorization': 'Bearer sk-37fc8R90O1p5YQy7py4vQpmbWywfsnqg3qLJxxJg2cO8y3Ui', 'Content-Type': 'application/json'},
    json={'model':'agnes-image-2.1-flash', 'prompt':'...ENGLISH PROMPT HERE...', 'n':1}, timeout=120)
data = r.json()
if 'data' in data:
    print('URL:' + data['data'][0]['url'])
else:
    print('ERR:' + json.dumps(data))
"
```

3. 下载每张图片到本地临时目录：
```bash
python -c "import requests; r=requests.get('AGENS_URL', timeout=60); open(r'C:\Users\59314\claudework\.playwright-mcp\agens_img1.png','wb').write(r.content); print('downloaded')"
```
全部3张图片用 img1/img2/img3 命名，重复此步骤。

4. 🚨 **配图生成容错链（Agens 主 → sese-ai 回退）：**

   **Agens API（首选）：**
   - `POST https://apihub.agnes-ai.com/v1/images/generations`
   - 模型：`agnes-image-2.1-flash`
   - Key：`sk-37fc8R90O1p5YQy7py4vQpmbWywfsnqg3qLJxxJg2cO8y3Ui`
   - 用 Python requests 调用（禁止 curl，Windows下curl传中文报编码错误），timeout=120s

   **sese-ai 回退（Agens 3次服务端失败后自动启用）：**
   - `POST https://api.sese-ai.com/api/generate`
   - 认证：`Authorization: Bearer AADDCC001122`
   - 模型：`z-image`，`aspect_ratio: "1:1"`，`quality: "1k"`
   - 返回格式：`{images: [{ok: true, b64: "base64_data"}]}`
   - Python 调用：
     ```bash
     python -c "
     import requests, json, base64
     r = requests.post('https://api.sese-ai.com/api/generate',
         headers={'Authorization': 'Bearer AADDCC001122', 'Content-Type': 'application/json'},
         json={'model':'z-image', 'prompt':'ENGLISH_PROMPT', 'aspect_ratio':'1:1', 'quality':'1k'}, timeout=120)
     data = r.json()
     decoded = base64.b64decode(data['images'][0]['b64'])
     open(r'C:\Users\59314\claudework\.playwright-mcp\agens_img1.png','wb').write(decoded)
     print('downloaded')
     "
     ```

   **容错链（线性执行，无选择）：**
   1. 调 Agens API，等待 ≥40s（实际生成最低耗时）
   2. Agens 返回 503/timeout → 等 40s 重试，最多 2 次
   3. Agens 连续 3 次失败 → 自动走 sese-ai（URL/Python代码替换为sese-ai格式）
   4. sese-ai 也失败 → 跳过该张，继续下一张
   5. Agens 客户端错误（400/rejected）→ 简化prompt重试一次，仍失败→sese-ai
   6. 3 张全部失败 → 熔断，停止本篇发布（不发布无图文章）；至少保留 1 张以上则继续

5. 🚨 图片上传到头条的方式：

   **已验证方案：用 `browser_drop` 拖放上传（2026-07-15 实测通过）**
   
   头条编辑器支持将图片直接拖入正文区域，ProseMirror 自动上传到头条CDN并插入正文。不需要点任何按钮。

   **操作步骤：**
   
   a. 下载图片到本地并复制到 Playwright 允许的目录（见第 3 步的 python requests 下载命令）。
   
   b. 依次调用 `browser_drop` 将3张图片拖入编辑器：
      ```
      mcp__playwright__browser_drop(target: ".ProseMirror", paths: ["C:\\Users\\59314\\claudework\\.playwright-mcp\\agens_img1.png"])
      ```
      每张拖入后编辑器将图片上传到头条CDN并自动插入到 **光标位置**。
      ⚡ 全部3张拖完后，图片全集中在编辑器开头，需要执行下一步 relocate。
   
   c. ⚠️ **关键：图片 relocate（一次性自动分布 25%/50%/75%）**
      
      `browser_drop` 插入的 3 张图片都在编辑器顶部，需运行下方自动 relocate 脚本。该脚本统计全文纯文字段落数，按 25%/50%/75% 三档计算位置，一次性振序并核验。不再使用 `【图N】` 标记。
      
      **DOM 结构须知：** ProseMirror 将每张图片包装在 `<div>` 容器中（不是 `<p>`），且每个 div 内含 2 个 `<img>` 标签（一个 1024px 展示用，一个 440px 预览用）。这是 ProseMirror 内部机制，不影响显示。查图片容器时查 `<div>` + `querySelector('img')`。
      
      在 `browser_run_code_unsafe` 中执行自动 relocate 脚本（一次性完成找图+算位置+插图+核验）：
      
      ```javascript
      // 🚨 自动 relocate：按段落数计算 25%/50%/75% 位置，不用标记
      async (page) => {
        var relocateResult = await page.evaluate(function() {
        var pm = document.querySelector('.ProseMirror');
        if (!pm) return { error: 'no pm' };
        
        // 1. 找到所有图片 DIV
        var imgDivs = [];
        for (var i = 0; i < pm.children.length; i++) {
          if (pm.children[i].tagName === 'DIV' && pm.children[i].querySelector('img')) {
            imgDivs.push(pm.children[i]);
          }
        }
        if (imgDivs.length !== 3) return { error: 'imgDivs=' + imgDivs.length };
        
        // 2. 找到所有纯文字 P 段落
        var textParas = [];
        for (var i = 0; i < pm.children.length; i++) {
          if (pm.children[i].tagName === 'P' && !pm.children[i].querySelector('img')) {
            textParas.push(pm.children[i]);
          }
        }
        if (textParas.length < 10) return { error: 'paras=' + textParas.length };
        
        var textParaCount = textParas.length;
        
        // 3. 计算目标段落索引（25%/50%/75%）
        var targets = [
          Math.floor(textParaCount * 0.25) - 1,
          Math.floor(textParaCount * 0.50) - 1,
          Math.floor(textParaCount * 0.75) - 1
        ];
        for (var t = 1; t < targets.length; t++) {
          if (targets[t] <= targets[t-1]) targets[t] = targets[t-1] + 2;
        }
        if (targets[2] >= textParaCount) targets[2] = textParaCount - 1;
        
        // 4. 从后往前插图
        for (var k = imgDivs.length - 1; k >= 0; k--) {
          var targetPara = textParas[targets[k]];
          if (targetPara) {
            targetPara.insertAdjacentElement('afterend', imgDivs[k]);
          }
        }
        
        pm.dispatchEvent(new Event('input', {bubbles: true}));
        
        // 5. 核验分布
        var newImgNodes = [];
        var totalAllNodes = pm.children.length;
        for (var i = 0; i < totalAllNodes; i++) {
          if (pm.children[i].querySelector && pm.children[i].querySelector('img')) {
            newImgNodes.push(i);
          }
        }
        var distribution = newImgNodes.map(function(idx) {
          return { index: idx, percent: Math.round(idx / totalAllNodes * 100) };
        });
        
        var band1 = distribution.filter(function(d){ return d.percent >= 8 && d.percent < 30; }).length;
        var band2 = distribution.filter(function(d){ return d.percent >= 30 && d.percent < 55; }).length;
        var band3 = distribution.filter(function(d){ return d.percent >= 55 && d.percent <= 85; }).length;
        var inLast10 = distribution.filter(function(d){ return d.percent > 90; }).length;
        var gapsOk = true;
        for (var g = 1; g < distribution.length; g++) {
          if (distribution[g].percent - distribution[g-1].percent < 15) gapsOk = false;
        }
        
        return {
          totalNodes: totalAllNodes,
          imgCount: newImgNodes.length,
          targets: targets,
          distribution: distribution,
          band1: band1, band2: band2, band3: band3,
          inLast10: inLast10,
          gapsOk: gapsOk,
          passed: (newImgNodes.length === 3 && band1 >= 1 && band2 >= 1 && band3 >= 1 && gapsOk && inLast10 === 0)
        };
      });
      
      console.log('Relocate:', JSON.stringify(relocateResult));
      if (!relocateResult.passed) throw new Error('RELOCATE_FAILED: ' + JSON.stringify(relocateResult));
    }

      ⚠️ **图片上传失败 / blob 残留 标准处置 SOP（不可临时发挥，必须走这套）**
      - 拖完 3 张后，先核验 `uniqueImg === 3 && blobCount === 0`：
        - 若 `blobCount > 0`（某张只生成本地预览、未传头条CDN）：**先清空编辑器内全部图片 DIV**（DOM 遍历删 `tagName==='DIV' && querySelector('img')` 的节点，正文文字不动），然后**重新 browser_drop 3 张**，再执行一次上面的 relocate 脚本。**绝不在有 blob/重复节点时叠加 relocate。**
        - 若 `uniqueImg > 3`（出现重复图，如重拖导致）：同样先清空全部图片 DIV，重新拖 3 张再 relocate 一次。
        - 若 `uniqueImg < 3`：说明有图根本没传上，检查 Agens 下载/拖放是否成功，补拖缺失的那张，再 relocate。
      - **铁律：任何一次 relocate 之前，编辑器里必须恰好是 3 个干净的图片 DIV（无 blob、无重复）。relocate 只做一次，做完即核验分布，绝不二次叠加。**
      - 禁止在 relocate 后手动 insertAdjacentElement 微调位置——百分比脚本已固定 25/50/75%，手动改只会引入不一致。

	   d. 🚨 **图片核验清单（不可跳过，逐条检查）：**
	      - [ ] **编辑器内 img 标签唯一数 ≥ 3（去重后，每张图 ProseMirror 自动生成 2 个 img）。** 
        ⚡ 注意：实际可能有 8 个因为 ProseMirror 每张图插 2 个 img。此时应检查去重后的唯一图片数：
        `var seen = {}; imgs.forEach(function(i){var m=i.src.match(/tos-cn-i-[^/]+\/([^~?]+)/);if(m)seen[m[1]]=true;}); uniqueCount=Object.keys(seen).length`
        核验标准：uniqueCount ≥ 4。
      - [ ] **图片 URL 以 `https://image-tt-private.toutiao.com/` 开头**（确认已上传到头条CDN）
      - [ ] **最后3段内无 img 标签**（检查 pm 最后3个子元素内无 querySelector('img')）
      - [ ] **无相邻两张图片**（遍历 pm.children，相邻两个元素都有 querySelector('img') → 违反）
      - [ ] **所有图片都在纯文字段落之间**（图前至少1段纯文字，图后至少1段纯文字）
      - [ ] **图片分散性检查（2026-07-24 修正区间）**：3 张图按 25%/50%/75% 三档均匀分布。三档区间 [8%,30%] / [30%,55%] / [55%,85%]，每档至少1张。相邻两张图百分比差≥15%。最后10%不得有图。若缺档/间距不足/堆在文末 → 退回修正。
      - [ ] **标题不为空**（检查 textarea[placeholder*="请输入文章标题"] 的 value，空则先用 locator.fill() 写入标题）
      
      任一项不通过 → 退回修正，不自欺跳过。

### Step 2 — 全自动设置（在 browser_run_code_unsafe 中执行）

```javascript
// ★ 固定坐标：[标题输入框]
await page.locator('textarea[placeholder*="请输入文章标题"]').fill('{title}');

// ★ 标题核验（头条限制2-30字）
var titleLen = await page.evaluate(function() {
  var tb = document.querySelector('textarea[placeholder*="请输入文章标题"]');
  return tb ? tb.value.length : 0;
});
if (titleLen > 30) {
  throw new Error('TITLE_TOO_LONG: 标题' + titleLen + '字，超过30字限制，需缩短后重试');
}

// ★ 固定坐标：[正文编辑器] — 写入整篇正文（已在Step 1.5写入, 这里只核验不覆写）
// ⚡ 汉字核验：必须用 match(/[一-鿿㐀-䶿豈-﫿]/g) 计汉字数，不用总字符数
await page.evaluate(function() {
  var pm = document.querySelector('.ProseMirror');
  if(!pm) throw new Error('ProseMirror not found');
  var text = pm.innerText || '';
  var chineseCount = (text.match(/[一-鿿㐀-䶿豈-﫿]/g) || []).length;
  if(chineseCount < 1500) throw new Error('汉字不足1500（当前'+chineseCount+'汉字），退回Step 1.5 重新做段落预算后重写');
});

// ★ 跳过平台AI配图：正文已有 Agens 嵌入的 3 张图（Step 1.6 已生成），不需要平台内置配图
// 核验 Agens 图片唯一数量（ProseMirror 每张图生成 2 个 img，用 uniqueCount）
var agensImgCheck = await page.evaluate(function() {
  var pm = document.querySelector('.ProseMirror');
  if (!pm) return { count: 0, uniqueCount: 0 };
  var imgs = pm.querySelectorAll('img');
  var seen = {};
  imgs.forEach(function(img) {
    var m = img.src.match(/tos-cn-i-[^/]+\/([^~?]+)/);
    if (m) seen[m[1]] = true;
  });
  return { total: imgs.length, uniqueCount: Object.keys(seen).length };
});
console.log('📸 Agens 配图: total=' + agensImgCheck.total + ' unique=' + agensImgCheck.uniqueCount);
if (agensImgCheck.uniqueCount < 3) {
  throw new Error('❌ Agens 配图不足3张（unique=' + agensImgCheck.uniqueCount + '），退回 Step 1.6');
}

// ★ 图片分布检查（3张图必须按 25% / 50% / 75% 三档分布，各占一档，不得堆积）
var imgDistributionCheck = await page.evaluate(function() {
  var pm = document.querySelector('.ProseMirror');
  if (!pm) return { error: 'no pm' };
  var children = pm.children;
  var totalNodes = children.length;
  var imgIndices = [];
  for (var i = 0; i < totalNodes; i++) {
    if (children[i].querySelector && children[i].querySelector('img')) {
      imgIndices.push(i);
    }
  }
  var distribution = imgIndices.map(function(idx) {
    return { index: idx, percent: Math.round(idx / totalNodes * 100) };
  });
  // 三档区间：band1=[8%,30%]（25%档中心）, band2=[30%,55%]（50%档中心）, band3=[55%,85%]（75%档中心）, 最后10%不得有图
  var band1 = distribution.filter(function(d){ return d.percent >= 8 && d.percent < 30; }).length;   // 25%档
  var band2 = distribution.filter(function(d){ return d.percent >= 30 && d.percent < 55; }).length;  // 50%档
  var band3 = distribution.filter(function(d){ return d.percent >= 55 && d.percent <= 85; }).length; // 75%档
  var inLast10 = distribution.filter(function(d){ return d.percent > 90; }).length;
  // 间距检查：相邻两张图的百分比差≥15%（防止挤在一起）
  var gapsOk = true;
  var gapInfo = [];
  for (var g = 1; g < distribution.length; g++) {
    var gap = distribution[g].percent - distribution[g-1].percent;
    gapInfo.push({ from: distribution[g-1].percent, to: distribution[g].percent, gap: gap });
    if (gap < 15) gapsOk = false;
  }
  return { totalNodes: totalNodes, imgCount: imgIndices.length, distribution: distribution, band1: band1, band2: band2, band3: band3, inLast10: inLast10, gapsOk: gapsOk, gapInfo: gapInfo };
});
console.log('📊 图片分布:', JSON.stringify(imgDistributionCheck.distribution), '档位 25%/50%/75%=', imgDistributionCheck.band1, imgDistributionCheck.band2, imgDistributionCheck.band3, '间距OK=', imgDistributionCheck.gapsOk);
if (imgDistributionCheck.imgCount !== 3) {
  throw new Error('❌ 图片数不等于3（当前' + imgDistributionCheck.imgCount + '），退回 Step 1.6');
}
if (imgDistributionCheck.band1 < 1 || imgDistributionCheck.band2 < 1 || imgDistributionCheck.band3 < 1) {
  throw new Error('❌ 图片未按25%/50%/75%三档均匀分布（各档=' + imgDistributionCheck.band1 + '/' + imgDistributionCheck.band2 + '/' + imgDistributionCheck.band3 + '），退回 Step 1.6 重新 relocate');
}
if (imgDistributionCheck.inLast10 >= 1) {
  throw new Error('❌ 有图落在最后10%（结尾应无图），退回 Step 1.6 重新 relocate');
}
if (!imgDistributionCheck.gapsOk) {
  throw new Error('❌ 相邻图片间距不足15%（' + JSON.stringify(imgDistributionCheck.gapInfo) + '），退回 Step 1.6 重新 relocate');
}

// ★ 底部遮罩（.garr-footer-publish-content 含三个按钮，不可移除）

// ★ 底部开关 — 只用 evaluate + DOM click
async function ensureSwitch(page, label) {
  var isChecked = await page.evaluate(function(targetLabel) {
    var checks = document.querySelectorAll('input[type="checkbox"], input[type="radio"]');
    for (var i = 0; i < checks.length; i++) {
      var p = checks[i].parentElement;
      for (var j = 0; j < 5; j++) {
        if (!p) break;
        if (p.textContent && p.textContent.includes(targetLabel)) {
          return checks[i].checked;
        }
        p = p.parentElement;
      }
    }
    return false;
  }, label);
  if (isChecked) { console.log(label + ': 已勾'); return; }
  await page.evaluate(function(targetLabel) {
    var checks = document.querySelectorAll('input[type="checkbox"], input[type="radio"]');
    for (var i = 0; i < checks.length; i++) {
      var p = checks[i].parentElement;
      for (var j = 0; j < 5; j++) {
        if (!p) break;
        if (p.textContent && p.textContent.includes(targetLabel)) {
          if (!checks[i].checked) checks[i].click();
          return;
        }
        p = p.parentElement;
      }
    }
  }, label);
  console.log(label + ': ✅');
}

await ensureSwitch(page, '投放广告赚收益');
await page.waitForTimeout(300);
await ensureSwitch(page, '头条首发');
await page.waitForTimeout(300);
await ensureSwitch(page, '发布得更多收益');
await page.waitForTimeout(300);
await ensureSwitch(page, '个人观点，仅供参考');
await page.waitForTimeout(300);

// ★ 引用AI反勾选（同样用 input.checked 检测）
var aiChecked = await page.evaluate(function() {
  var checks = document.querySelectorAll('input[type="checkbox"]');
  for (var i = 0; i < checks.length; i++) {
    var p = checks[i].parentElement;
    for (var j = 0; j < 5; j++) {
      if (!p) break;
      if (p.textContent && p.textContent.includes('引用AI')) { return checks[i].checked; }
      p = p.parentElement;
    }
  }
  return false;
});
if (aiChecked) {
  await page.evaluate(function() {
    var checks = document.querySelectorAll('input[type="checkbox"]');
    for (var i = 0; i < checks.length; i++) {
      var p = checks[i].parentElement;
      for (var j = 0; j < 5; j++) {
        if (!p) break;
        if (p.textContent && p.textContent.includes('引用AI')) {
          checks[i].click();
          return;
        }
        p = p.parentElement;
      }
    }
  });
}

// ★ 固定坐标：[添加位置] — 上海
async function setPosition(page, city) {
  // Step 1: 点击 edit-label 激活位置区域
  await page.evaluate(function() {
    var cell = document.querySelector('.position-cell .edit-label');
    if (cell) cell.click();
  });
  await page.waitForTimeout(1000);
  // Step 2: 直接 click .position-select div 打开下拉（input 此时不可见）
  await page.evaluate(function() {
    var posSelect = document.querySelector('.position-select');
    if (posSelect) posSelect.click();
  });
  await page.waitForTimeout(1500);
  // Step 3: 选择城市选项
  var selected = await page.evaluate(function(cityName) {
    var opts = document.querySelectorAll('.byte-select-option');
    for (var i = 0; i < opts.length; i++) {
      if (opts[i].textContent.trim() === cityName) { opts[i].click(); return true; }
    }
    return false;
  }, city);
  await page.waitForTimeout(500);
  if (!selected) throw new Error('POSITION_CITY_NOT_FOUND: ' + city);
  var posDisplay = await page.evaluate(function() {
    var pos = document.querySelector('.position-select');
    return pos ? pos.textContent.trim() : '';
  });
  console.log('📍 位置已设置: ' + posDisplay);
  if (!posDisplay.includes(city)) throw new Error('POSITION_SET_FAILED: 位置未设置为' + city);
}
await setPosition(page, '上海');
await page.waitForTimeout(300);

// ★ 封面设置 — 确认"单图"模式已选中（正文第一张图自动成为封面）
// ⚡ 不依赖头条默认行为，主动检查+设
var coverSet = await page.evaluate(function() {
  // 找所有 radio/label 文本含"单图"的元素
  var all = document.querySelectorAll('label, span, div, .byte-radio-wrapper');
  for (var i = 0; i < all.length; i++) {
    if (all[i].textContent.trim() === '单图') {
      var wrapper = all[i].closest('.byte-radio-wrapper') || all[i];
      if (wrapper.classList.contains('byte-radio-wrapper-checked')) {
        return '已选中';
      }
      // 未选中 → 点击
      wrapper.querySelector('input')?.click();
      if (!wrapper.querySelector('input')) wrapper.click();
      return '已点击设';
    }
  }
  return '未找到单图选项';
});
console.log('🖼️ 封面设置:', coverSet);
await page.waitForTimeout(500);

// ★ 内容核验：汉字≥1500 + 禁止句式检测 + 段落长度检测
// ⚡ 必须用 match(/[一-鿿㐀-䶿豈-﫿]/g) 计汉字，不收非汉字字符
var contentCheck = await page.evaluate(function() {
  var pm = document.querySelector('.ProseMirror');
  if (!pm) return { error: 'ProseMirror not found' };
  var text = pm.innerText || '';
  // 汉字计数：仅统计CJK统一表意字符
  var chineseCount = (text.match(/[一-鿿㐀-䶿豈-﫿]/g) || []).length;

  // ★ v7.6：禁止句式检测（硬闸）
  var forbiddenPatterns = ['评论区说说', '来评论区说说', '你学会了吗', '你觉得呢', '评论区见', '转发给需要的人', '不妨试试', '要不你也试试', '下次试试看', '你也行动起来吧'];
  var foundForbidden = [];
  forbiddenPatterns.forEach(function(p) {
    if (text.includes(p)) foundForbidden.push(p);
  });

  // ★ 逐段汉字长度检测（目标≤60；硬闸≤80）
  var paras = pm.querySelectorAll('p');
  var longParas = [];
  var over60Paras = [];
  var paraLengths = [];
  for (var i = 0; i < paras.length; i++) {
    var pt = (paras[i].textContent || '');
    var chineseInPara = (pt.match(/[一-鿿㐀-䶿豈-﫿]/g) || []).length;
    paraLengths.push(chineseInPara);
    if (chineseInPara > 60) over60Paras.push('#'+(i+1)+':'+chineseInPara+'汉字');
    if (chineseInPara > 80) longParas.push('#'+(i+1)+':'+chineseInPara+'汉字');
  }

  return {
    chineseCount: chineseCount,
    forbiddenFound: foundForbidden,
    longParas: longParas,
    over60Paras: over60Paras,
    paraCount: paras.length
  };
});
console.log('📊 内容核验:', JSON.stringify(contentCheck));

if (contentCheck.error) { throw new Error('内容核验失败: ' + contentCheck.error); }
if (contentCheck.chineseCount < 1500) {
  throw new Error('❌ 汉字不足1500(当前' + contentCheck.chineseCount + '汉字)，退回Step 1.5 重新做段落预算后重写');
}
// 汉字超过1500视为合格（内容越丰富越好），不设上限
if (contentCheck.forbiddenFound && contentCheck.forbiddenFound.length > 0) {
  throw new Error('❌ 包含禁止句式: ' + contentCheck.forbiddenFound.join(', ') + '，退回 Step 1.5 重写结尾');
}
if (contentCheck.over60Paras && contentCheck.over60Paras.length > 0) {
  throw new Error('❌ 超过60汉字段(' + contentCheck.over60Paras.length + '段): ' + contentCheck.over60Paras.join('; ') + '，退回拆分');
}
if (contentCheck.longParas && contentCheck.longParas.length > 0) {
  throw new Error('❌ 超长段(' + contentCheck.longParas.length + '段): ' + contentCheck.longParas.join('; ') + '，退回 Step 1.5 拆分段落');
}
```

### Step 3 — 🚨 禁止调用任何 API（save-xhr 会创建重复草稿）

直接进入 UI 定时流程。

### Step 4 — 🚨 UI 定时发布（精确代码，不可修改）

🚨 **🚨 **执行前硬性核验（不可跳过）：**
1. **标题不为空** — 检查 `textarea[placeholder*="请输入文章标题"]` 的 value。若为空，必须用 `locator.fill('{title}')` 重写（不能用 `el.value + dispatchEvent`——byte-component 不接受），写完后再次核验。
2. **字数 ≥1500 汉字** — 编辑器底部"共 X 字"或 innerText 计算。低于1500则续写末段到足量，上不封顶。严禁反复删改凑恰好1500。
   🚫 禁止复盘时改为精确等于1500。1500是最低线，不是目标值。2026-07-21 硬性锁死。
3. **图片核验清单全部通过**（§ Step 1.6.d 7项全 ✅）。
4. **图片位置分散性检查（2026-07-24 修正区间+间距）** — 3 张图按 25%/50%/75% 三档均匀分布。三档区间 [8%,30%] / [30%,55%] / [55%,85%]，每档至少1张，相邻两张百分比差≥15%。用 `pm.children` 遍历每张图片的索引计算百分比位置。如有任一张落在最后 10%、三档缺档或相邻间距不足 → 退回修正。
5. **图片不割裂句子（2026-07-24 新增）** — 每张 DIV(img) 的 `previousElementSibling` 必须是以句尾标点（。？！.!?）结尾的 P 段落。用 `page.evaluate` 遍历核验，任一张图的前一段不以句标结尾 → 退回 Step 1.6 重新 relocate。分散性和割裂是两道独立的闸，必须全部通过才能进 Step 4。
6. **底部开关已勾选**（投放广告/头条首发/发布得更多收益/个人观点）。
7. **引用AI已取消勾选**。
8. **位置已设置**（上海）。
9. **封面已设置** — Step 2 的封面代码会主动检查并设好"单图"模式。确认输出有 `🖼️ 封面设置:` 即可。
10. **定时时间核验（2026-07-17 新增）** — 打开定时弹窗并设好日期/小时/分钟后，必须用代码读取弹窗显示的时间，确认与目标时间一致，**再**点"预览并定时发布"。不一致则退回修正。

// ★ 固定坐标：[定时发布]
await page.locator('button:has-text("定时发布")').click();
await page.waitForTimeout(2000);

// ★ 固定坐标：[定时发布弹窗] — 弹窗检测
var hasDialog = await page.evaluate(function() {
  var btns = document.querySelectorAll('button');
  var c=false, p=false;
  for(var i=0;i<btns.length;i++){var t=btns[i].textContent;if(t.includes('取消'))c=true;if(t.includes('预览并定时发布'))p=true;}
  return c&&p;
});
if (!hasDialog) {
  await page.waitForTimeout(3000);
  await page.evaluate(function() {
    var btns = document.querySelectorAll('button');
    for(var i=0;i<btns.length;i++){if(btns[i].textContent.trim()==='定时发布'){btns[i].click();break;}}
  });
  await page.waitForTimeout(2000);
  var hasDialog2 = await page.evaluate(function() {
    var btns = document.querySelectorAll('button');
    var c=false, p=false;
    for(var i=0;i<btns.length;i++){var t=btns[i].textContent;if(t.includes('取消'))c=true;if(t.includes('预览并定时发布'))p=true;}
    return c&&p;
  });
  if (!hasDialog2) { throw new Error('TIMER_DIALOG_FAILED: 定时弹窗未弹出'); }
}

// ★ 固定坐标：[日期选择器] — ⚡ .day-select 不可见（offsetParent=null），Playwright locator.click() 报 timeout
// 统一用 evaluate DOM click + 异步延时后遍历选项
await page.evaluate(function() {
  var ds = document.querySelector('.day-select');
  if (ds) ds.click();
});
await page.waitForTimeout(1000);
// ⚡ hasText 用正则精确匹配日期，避免匹配到其他包含相同文字的选项
await page.evaluate(function(dateStr) {
  var opts = document.querySelectorAll('.byte-select-option');
  for(var i=0;i<opts.length;i++) {
    if(opts[i].textContent.trim() === dateStr) { opts[i].click(); return; }
  }
}, '{date}');
await page.waitForTimeout(800);

// ★ 固定坐标：[小时选择器] — 同上，统一用 evaluate DOM click
// ⚡ {hour} 纯数字（6 或 18），必须精确匹配
await page.evaluate(function() {
  var hs = document.querySelector('.hour-select');
  if (hs) hs.click();
});
await page.waitForTimeout(1000);
await page.evaluate(function(hourStr) {
  var opts = document.querySelectorAll('.byte-select-option');
  for(var i=0;i<opts.length;i++) {
    if(opts[i].textContent.trim() === hourStr) { opts[i].click(); return; }
  }
}, '{hour}');
await page.waitForTimeout(800);

// ★ 固定坐标：[分钟选择器]（必设 0）— 同上
await page.evaluate(function() {
  var ms = document.querySelector('.minute-select');
  if (ms) ms.click();
});
await page.waitForTimeout(1000);
await page.evaluate(function() {
  var opts = document.querySelectorAll('.byte-select-option');
  for(var i=0;i<opts.length;i++) {
    if(opts[i].textContent.trim() === '0') { opts[i].click(); return; }
  }
});
await page.waitForTimeout(800);

// ★ 定时时间核验：读取弹窗显示的时间，确认后再点发布
var timerVerify = await page.evaluate(function() {
  var daySelect = document.querySelector('.day-select');
  var hourSelect = document.querySelector('.hour-select');
  var minSelect = document.querySelector('.minute-select');
  return {
    day: daySelect ? daySelect.textContent.trim() : 'not found',
    hour: hourSelect ? hourSelect.textContent.trim() : 'not found',
    min: minSelect ? minSelect.textContent.trim() : 'not found'
  };
});
console.log('⏰ 定时时间核验:', JSON.stringify(timerVerify));
if (!timerVerify.day.includes('{date}') || !timerVerify.hour.includes('{hour}')) {
  throw new Error('❌ 定时时间设置失败：期望 {date} {hour}:00，实际=' + timerVerify.day + ' ' + timerVerify.hour + ':' + timerVerify.min);
}

// ★ 固定坐标：[预览并定时发布（弹窗内）]
await page.evaluate(function() {
  var buttons = document.querySelectorAll('[role="dialog"] button');
  for(var i=0;i<buttons.length;i++){
    if(buttons[i].textContent.includes('预览并定时发布')){
      ['mousedown','mouseup','click'].forEach(function(type){
        buttons[i].dispatchEvent(new MouseEvent(type,{bubbles:true,cancelable:true,view:window}));
      });
      break;
    }
  }
});
await page.waitForTimeout(2000);

// ★ 固定坐标：[定时发布（最终确认）] — 2026-07-18复盘修正：最终确认按钮是 byte-btn-primary publish-btn
// 预览浮层中的"定时发布"按钮 class="byte-btn byte-btn-primary byte-btn-size-large byte-btn-shape-square publish-btn"
// "返回编辑"按钮才是 byte-btn-default publish-btn
// 选择器用 button.publish-btn:has-text("定时发布") 即可区分
await page.locator('button.publish-btn:has-text("定时发布")').waitFor({timeout: 10000});
await page.waitForTimeout(1000);
await page.locator('button.publish-btn:has-text("定时发布")').click();
await page.waitForTimeout(3000);
// → URL 跳转到 /graphic/articles ✅ 成功
```

### Step 5 — 记录本次发布

记录到记忆：本篇的 hook_type / narrative_framework / ending_type，用于下一篇轮换判断。

记录信息：
- title: "..."
- direction: "..."
- scheduled_time: "..."
- hook_type: "..."
- narrative_framework: "..."
- ending_type: "..."
```

### Step 6 — 下一篇（重复 Step 1-5）

当日 2 篇全部 ui_scheduled → 进入 §32 每日加固。任一篇未完成 → 停止当天流程，修复后重新执行。

## 🎯 选择器坐标速查表

所有表格统一为 4 列：元素 → CSS 定位 → Playwright 操作 → ⚠️ 注意。代码块不再内嵌选择器。

### 页面入口

| 用途 | URL |
|---|---|
| 统计页 | https://mp.toutiao.com/statistics/data |
| 作品管理列表 | https://mp.toutiao.com/profile_v4/manage/graphic |
| 创作-已发布 | https://mp.toutiao.com/profile_v4/manage/content/all |
| 作品数据-单篇 | https://mp.toutiao.com/profile_v4/analysis/works-single/article |
| 发布页 | https://mp.toutiao.com/profile_v4/graphic/publish |
| 草稿箱（仅查看） | https://mp.toutiao.com/profile_v4/manage/draft |

### 发布页·编辑器区

| 元素 | CSS 定位 | Playwright 操作 | ⚠️ 注意 |
|---|---|---|---|
| 标题输入框 | textarea[placeholder*="请输入文章标题"] | locator.fill('{title}') | ⚡ 不能用 JS el.value + dispatchEvent，byte-component 不响应 |
| 正文编辑器 | .ProseMirror | el.innerHTML = html + dispatchEvent(new Event('input')) | 赋值后必须 dispatch input 事件触发状态更新 |
| 页面签名验证 | .ProseMirror + button 文本 | browser_evaluate 检测 9 项签名（URL+DOM+按钮顺序） | 全部通过才继续，缺任一项停止 |

### 发布页·右侧面板

| 元素 | CSS 定位 | Playwright 操作 | ⚠️ 注意 |
|---|---|---|---|
| AI配图缩略图 | .advise-item-recommend ul li | 🚫 跳过！用 Agens 管线时走 Step 1.6，不点头条内置配图 | - |
| AI 创作标签 | text=AI 创作 | 不点击（走 Agens 配图管线） | - |
| 添加位置（上海） | .position-cell .edit-label → 点击 → .position-select div.click() → .byte-select-option 选"上海" | setPosition(page, '上海') | ⚡ 硬性步骤，不跳过。默认上海。2026-07-18实测：edit-label点击后input不可见，需直接click .position-select div触发下拉 |

### 发布页·封面设置

| 元素 | CSS 定位 | Playwright 操作 | ⚠️ 注意 |
|---|---|---|---|
| 单图 | text=单图 | 默认已选中，确认即可 | 正文第一张图自动成为封面 |
| 三图 | text=三图 | 不选 | - |
| 无封面 | text=无封面 | 不选 | - |
| 封面预览图 | 封面预览区域 | 检查非空白即可 | 单图模式下不走弹窗 |

### 发布页·底部开关

⚡ 只能用 evaluate 遍历 input 元素 + DOM click 勾选开关。不能用 Playwright locator('text=...').click()——text= 会在多个元素间引发 strict mode 冲突，静默吞异常后开关未实际勾上。
⚡ 检测方法：遍历 input 元素读取 .checked 属性。
⚡ 2026-07-15 已修复：ensureSwitch 只用 evaluate 方案，不再回退 Playwright locator。

| 元素 | 操作 | ⚠️ 注意 |
|---|---|---|---|
| 投放广告赚收益 | ensureSwitch(page, '投放广告赚收益') | 必勾 |
| 头条首发 | ensureSwitch(page, '头条首发') | 必勾 |
| 授权平台自动维权 | ensureSwitch(page, '授权平台自动维权') | 头条首发勾选后建议勾 |
| 发布得更多收益 | ensureSwitch(page, '发布得更多收益') | 必勾 |
| 个人观点，仅供参考 | ensureSwitch(page, '个人观点，仅供参考') | 必勾 |
| 引用AI | aiChecked 检测 → input.click() | 禁止勾选，检测到勾选则取消 |
| 取材网络 | 条件勾选 | 有引用非原创内容时勾选 |
| 虚构演绎，故事经历 | 不操作 | 默认不选 |
| 投资观点，仅供参考 | 不操作 | 默认不选 |
| 健康医疗分享，仅供参考 | 不操作 | 默认不选 |

### 发布页·发文设置折叠区

| 元素 | CSS 定位 | Playwright 操作 | ⚠️ 注意 |
|---|---|---|---|
| 展开发文设置 | text=发文设置 | locator('text=发文设置').click() | 新版默认已展开，折叠时才需操作 |
| 收起（回到顶部） | text=回到顶部 | locator('text=回到顶部').click() | 展开后发文设置变为回到顶部 |

### 发布页·底部按钮

正常状态（进入发布页时）按钮顺序：预览 → 定时发布 → 预览并发布。顺序不对 → 停止操作。

| 元素 | CSS 定位 | Playwright 操作 | ⚠️ 注意 |
|---|---|---|---|
| 预览 | button:has-text('预览') | 不点 | - |
| 定时发布 | button:has-text('定时发布') | locator('button:has-text("定时发布")').click() | ✅ 点击弹出定时弹窗 |
| 预览并发布 | button:has-text('预览并发布') | 🚫 禁止点击 | 与定时发布紧邻，点错直接发布 |

预览后状态（点弹窗预览并定时发布后）：

| 元素 | CSS 定位 | Playwright 操作 | ⚠️ 注意 |
|---|---|---|---|
| 定时发布（最终确认） | button.publish-btn:has-text("定时发布") | locator('button.publish-btn:has-text("定时发布")').waitFor + .click() | ⚡ 预览浮层上的按钮，class=byte-btn-primary publish-btn（不是 byte-btn-default，那个是"返回编辑"） |
| 返回编辑 | button:has-text('返回编辑') | 不点 | class：byte-btn-default.publish-btn |

### 🚨 定时发布弹窗

| 元素 | CSS 定位 | Playwright 操作 | ⚠️ 注意 |
|---|---|---|---|
| 弹窗触发 | button:has-text("定时发布") | 底部 locator.click() | 预览并定时发布也含"定时发布"文本，必须用 first() |
| 弹窗开启标志 | 底部按钮变为取消和预览并定时发布 | evaluate 检测按钮文本变化 | ⚡ 不要检查 [role="dialog"] |
| 日期选择器 | .day-select | 评估→DOM click（Playwright locator.click() 不可见时），setTimeout 800ms 后遍历 .byte-select-option 匹配 | ⚡ 用正则精确匹配日期，避免匹配到其他包含相同文字的选项。⚡ .day-select 在 page.evaluate 中 offsetParent=null，Playwright locator.click() 报 timeout 不可见→改用 evaluate DOM click + 异步 setTimeout 轮询选项 |
| 小时选择器 | .hour-select | 评估→DOM click（locator.click() 不可见），setTimeout 800ms 后遍历 .byte-select-option 匹配 /^{hour}$/ | ⚡ {hour} 纯数字（6 或 18），必须用正则 /^6$/ 排除"18"。getByRole('option') 不可用 |
| 分钟选择器 | .minute-select | 评估→DOM click，setTimeout 800ms 后遍历 .byte-select-option 匹配 /^0$/ | ⚡ 必须设为 0 |
| 预览并定时发布（弹窗内） | [role="dialog"] button:has-text('预览并定时发布') | dispatchEvent（mouse+click） | ⚡ 此按钮只打开预览浮层，不直接发布 |
| 取消 | button:has-text('取消') | 不点 | - |

两步确认流程：弹窗 dispatchEvent「预览并定时发布」→ 预览浮层打开 → 底部按钮变为【返回编辑】【定时发布】→ 点击【定时发布（最终确认）】→ URL 跳转到 /graphic/articles → ✅ 成功

⚡ 最终确认按钮的 class 是 `byte-btn-primary publish-btn`（预览浮层内的「定时发布」）。"返回编辑"才是 `byte-btn-default publish-btn`。选择器用 `button.publish-btn:has-text("定时发布")` 即可。

### 遮罩/遮挡层

| 层 | CSS 选择器 | 影响范围 | 应对 |
|---|---|---|---|
| 底部固定栏遮罩 | .garr-footer-publish-content | 遮挡底部所有 checkbox/radio 和按钮 | 全部 { force: true } |
| 弹窗遮罩 | .byte-modal-wrapper / .byte-modal-content | 拦截 Playwright click 到弹窗内元素 | 弹窗内用 dispatchEvent |
| 右侧面板遮罩 | .byte-tabs-content-inner | 拦截 AI 配图点击 | 用 { force: true } |

### 页面签名检查（打开发布页后验证）

browser_navigate('https://mp.toutiao.com/profile_v4/graphic/publish') → 验证全部：

- [ ] URL 含 /profile_v4/graphic/publish
- [ ] .ProseMirror 存在
- [ ] DOM 含文本 "展示封面"
- [ ] DOM 含文本 "投放广告"
- [ ] DOM 含文本 "作品声明"
- [ ] DOM 含文本 "预览"
- [ ] DOM 含文本 "定时发布"
- [ ] DOM 含文本 "预览并发布"
- [ ] 按钮顺序正确：预览 → 定时发布 → 预览并发布

任一缺失 → 页面加载失败或 DOM 结构变更，刷新或检查后重试。

## 📱 手机端排版铁律（强制执行 · 不可跳过）

排版不是好看不好看的问题——一段文字在手机屏上糊了 = 读者在那一秒就划走了。以下每一条都有具体的字数/行数/间隔标准。

### 铁律一：视觉呼吸法则

读者在手机上看了6-8段纯文字后会产生视觉疲劳。每6-8段纯文字之后，安排配图、短总结或自然转折作为呼吸点（不制造无意义短段）。

### 铁律四：图文锚点规则

| 规则 | 标准 | 违反后果 |
|---|---|---|
| 配图间隔 | 全文固定 3 张，按 25% / 50% / 75% 等距投放 | ≤3张→视觉疲劳，退回重排 |
| 图片位置 | 图在段落之间，不在段中，不堆在文末 | - |
| 第1张图位置 | 前3段内，但**不得在第1段之后**（放在第2-4段的段落后，让读者先读完开头再呼吸） | 开头无图=降低留人率；在第1段后立即插=割裂感 |
| 文末无图 | 最后3段不能有图 | 文末堆图=收尾无力 |
| 图前后文字 | 图前至少1段引文，图后至少1段承接 | 孤立无援的图不插 |

### 铁律五：造句约束

| 指标 | 标准 | 手机端原因 |
|---|---|---|
| 单句长度 | ≤30字，每句不超过2个逗号（，），枚举用顿号（、） | 手机端超过30字的句子换行后视线跳行 |
| 复合句 | 一句话不超过2个逗号 | 手机窄屏读长句=晕 |
| 转折词使用 | 每段至少1个"但/不过/结果/后来/其实"类转折 | 没有转折=平铺直叙 |
| 段末留钩子 | 每个方法段的末尾暗示"还有更好的" | 驱动力让读者往下划 |

## 📚 标题·开头·框架·结尾 规则速查表

### 标题公式（Phase 1 选题用）

**公式1：数字 + 人群/场景 + 结果承诺**（奇数>偶数，数字≤2个放前部，具体金额>抽象概念）
- ✅ 每天下班花半小时做这3件事，一年能多存2万块

**公式2：身份定位 + 痛点 + 解决方案**（身份词：租房党/打工人/宝妈/新手）
- ✅ 租房党别乱买收纳了！这6样东西反而越收越乱

**公式3：颠覆认知 + 悬念钩子**
- ✅ 冰箱这5个位置放错，菜两天就烂

**公式4：数字 + 对比 + 低成本高回报**
- ✅ 睡前4个习惯坚持一周，比周末补觉管用10倍

**标题硬性要求**（写完逐条核验）

| 指标 | 标准 |
|---|---|
| 长度 | 16-28汉字（超28字信息流截断） |
| 数字 | ≥1个（带数字标题CTR高30%+） |
| 身份词 | ≥1个（你/租房/打工人/宝妈） |
| 价值承诺 | 读完能得到什么 |
| ❌ 禁止 | "你是不是也这样""你有过吗"类反问开头 |

⚠️ 不得连续两篇使用同一标题公式（2026-07-17）

### 开头钩子（Phase 2 写作用，连续两篇不得同类型）

| # | 类型 | 示例 |
|---|---|---|
| 1 | 颠覆认知 | "做了这么多年饭，最近才发现炒菜放盐的顺序错了" |
| 2 | 自嘲踩坑 | "说出来不怕你们笑话，这个空调遥控器我研究了一个夏天" |
| 3 | 场景代入 | "下午三点，你打开冰箱想拿瓶水，一股闷热扑面而来" |
| 4 | 真实数据 | "月薪7500，一年存下5万。同事都很疑惑" |
| 5 | 悬念故事 | "上个月我一个朋友装修，签合同时多问了4句话，省了2万块" |
| 6 | 精准痛点 | "换了好几个枕头还是睡不好，颈椎反而越来越疼" |
| 7 | 反常识结论 | "冰箱的冷藏室中间层是最容易串味的位置" |

**开头禁止**：❌"随着…""在…的今天""你是不是也这样…"❌大段描写超100字不入题

### 叙事框架（连续两篇不得同类型）

| 框架 | 结构 | 适用方向 |
|---|---|---|
| A 踩坑修复对比 | 犯错X年→幡然醒悟→正确做法→效果对比 | 省钱/厨房/收纳/家电 |
| B 场景问题解法 | 具体场景→困境→处理方法→结果验证 | 职场/装修/租房/医保 |
| C 认知升级 | 以为…→实际…→为什么→怎么做 | 社会民生/生活观察/理财 |
| D 串珠叙事 | 触发事件→方法1→方法2→方法3→串联收束 | 旅行/备餐/习惯/健康 |

### 结尾类型（连续两篇不得同类型）

| # | 类型 | 写法 | 示例 |
|---|---|---|---|
| 1 | 闭环感悟 | 回到开头场景，轻收 | "写这篇的时候回头看，发现自己以前真能忍" |
| 2 | 数据验证 | 用自家效果收尾 | "去年七月三百多，今年同一套房子两百出头" |
| 3 | 延伸思考 | 留一个值得想的角度 | "但很多好用的方法其实是免费的" |
| 4 | 自嘲总结 | 用自己收尾 | "买的收纳神器有一半是智商税" |

**❌ 结尾禁止**："评论区说说""来评论区说说""你学会了吗""你觉得呢""评论区见""转发给需要的人"

> **复盘按 CLAUDE.md 技能修复标准流程执行**

## 🎨 Agens 配图管线

### API 配置

```json
{
  "endpoint": "https://apihub.agnes-ai.com/v1/images/generations",
  "model": "agnes-image-2.1-flash",
  "key": "sk-37fc8R90O1p5YQy7py4vQpmbWywfsnqg3qLJxxJg2cO8y3Ui"
}
```

### 配图规则

每篇配图固定 3 张（1500字文章标准），auto-relocate 脚本自动按 25%/50%/75% 计算插入位置：

| 位置 | 投放比例 | 图片作用 |
|---|---|---|
| 第1张 | 全文 25% 处 | 让读者看到"文章配了图，不是纯文字墙" |
| 第2张 | 全文 50% 处 | 打断视觉疲劳，作为呼吸点 |
| 第3张 | 全文 75% 处 | 增强可信度（效果对比图/场景图） |
| ❌ 最后3段 | 不能有图 | 结尾清洁 |

### 配图风格规范（必须统一）

- 写实摄影风格（不要插画/漫画/3D渲染）
- 中国家庭生活场景（厨房/卧室/客厅/超市）
- 自然光，暖色调
- 俯拍或平视视角
- 手机摄影质感（不要专业影棚感）
- 有人气但没有人（美食/场景图，不要模特）
- 尺寸：1024x1024（正方形，移动端友好）

### 提示词模板

从图片周围的 2-3 段内容提取关键词，填入以下框架：
写实摄影风格，中国家庭[场景]，[关键物品/动作]，[视角]，自然光，暖色调，手机摄影质感，生活化

## 操作故障处理

| 条件 | 现象 | 处理 |
|---|---|---|
| 3014 | 审核中 | timeline 列表获取不到最新文章时 → 3x5s 重试，仍取不到 → 标记"待手动确认"后继续下一篇 |
| 定时弹窗无响应 | 点击定时发布按钮后弹窗不出现 | 等待3s → evaluate 直接点定时按钮 → 仍不出现 → 检查标题是否为空（空标题阻止弹窗弹出），若为空用 locator.fill() 重写标题 |
| 定时发布分钟错误 | 已设置日期/小时，未设分钟 | 用 .minute-select 选择器设置分钟为0 |
| 操作卡住 | 连续2次同一操作无效果 | 退出当前步骤重进，或刷新发布页 |
| 发布页DOM异常 | 按钮顺序不对/关键元素缺失 | 记录变化，更新固定坐标表后重试 |
| 标题写入后仍为空 | 用 value+dispatchEvent 后检测 value 为空 | byte-component 不接受 JS 赋值。必须改用 `locator('textarea[placeholder*="请输入文章标题"]').fill('{title}')`，不可回退到 JS 方案 |
| 图片直写 CDN URL 到 innerHTML 后加载失败 | img 有 className="error"、width=0 或 16 | 截图显示破坏。不能用 innerHTML 写 `<img src="CDN_URL">`——头条CDN需上传流程认证。必须走 Step 1.6 的 browser_drop 上传本地文件 |
| ProseMirror不接受增量插段 | insertAdjacentElement插入的段落不生效（被内部状态覆盖） | 只替换已有段落的innerHTML加长内容，不可重建全文或用insertAdjacentElement插新段 |
| browser_drop 后 imgCount 为 6-8 | ProseMirror 每张图片生成 2 个 img 标签 | 用 uniqueCount（按 src 中的图片 ID 去重）代替 totalImgCount 核验。核验标准：uniqueCount ≥ 4 |
| 正文结尾缺少呼吸感 | 连续6-8段纯文字 > 130字无短段或穿插 | 在结尾部分安排配图或自然转折，不让长堆砌在最后 |
