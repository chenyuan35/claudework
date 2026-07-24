---
name: qq-publish
description: 企鹅号（om.qq.com）文章发布技能 v4.2（恢复健壮版）
---

# 企鹅号 · AI生活圈 · 文章发布技能 v4.2（恢复健壮版）

**触发**：/qq-publish

## §-1 技能文件保护门（2026-07-24，最高优先级）

本节只保护 SKILL.md 本身，不改变"启动第一动作必须进浏览器"的发布流程。任何模型修改本技能前，必须先执行保护门。

1. **先备份，后编辑**：复制当前文件为 `SKILL.md.bak-YYYYMMDD-HHMMSS`；未生成备份，禁止写入。
2. **只做局部补丁**：禁止用整文件重写覆盖原文件；禁止根据聊天上下文"重建全文"。
3. **删除量硬闸**：候选文件比原文件少超过 50 行，或总行数低于原文件 95%，立即拒绝保存。
4. **结构硬闸**：保存前必须确认 YAML 头完整、代码围栏成对、§0/PHASE 0/1/2/2.5/3/4/§5/§6/§7 全部存在。
5. **差异审查**：输出新增行数、删除行数及被修改的标题；禁止只说"已优化"。
6. **失败回滚**：任何校验失败，恢复备份，不得继续修改原文件。

```python
# 候选文件写回前运行：python skill_write_guard.py SKILL.md SKILL.new.md
from pathlib import Path
import sys, shutil, datetime, re
old_path, new_path = map(Path, sys.argv[1:3])
old = old_path.read_text(encoding="utf-8")
new = new_path.read_text(encoding="utf-8")
old_lines, new_lines = old.splitlines(), new.splitlines()
required = [
    "## §0", "## PHASE 0", "## PHASE 1", "## PHASE 2：",
    "## PHASE 2.5", "## PHASE 3", "## PHASE 4", "## §5", "## §6", "## §7"
]
errors = []
if len(new_lines) < max(int(len(old_lines) * 0.95), len(old_lines) - 50):
    errors.append(f"破坏性缩短：{len(old_lines)} → {len(new_lines)} 行")
if new.count(chr(96)*3) % 2:
    errors.append("Markdown 代码围栏未闭合")
if not new.startswith("---\n") or new.count("---", 0, 200) < 2:
    errors.append("YAML 头不完整")
for heading in required:
    if heading not in new:
        errors.append("缺少关键章节：" + heading)
if errors:
    raise SystemExit("REFUSE WRITE\n" + "\n".join(errors))
backup = old_path.with_name(old_path.name + ".bak-" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S"))
shutil.copy2(old_path, backup)
shutil.copy2(new_path, old_path)
print({"PASS": True, "oldLines": len(old_lines), "newLines": len(new_lines), "backup": str(backup)})
```


## 账号信息

| 字段 | 值 |
|------|-----|
| 账号名 | AI生活圈 |
| 状态 | 正式运营（阅读量持续0，冷启动诊断未通过） |
| 编辑器 | 企鹅号 ExEditor（标题是 span，正文是单 ProseMirror） |
| 后台 | https://om.qq.com/main/creation/article |
| 内容管理 | https://om.qq.com/main/management/articleManage |
| 权益管理 | https://om.qq.com/main/account/rights |

## §0 执行总纲（唯一黄金路径，不可调整次序）

> **发布任务的第一动作永远是进浏览器看数据。** 文件保护门只在"修改技能文件"时执行，不属于 /qq-publish 发布任务。

```
第0步：browser_navigate → https://om.qq.com/main/management/articleManage
      → 一次 evaluate 读取上一篇数据、最近标题、最近5篇结构
PHASE 0：选题红线
PHASE 1：流量诊断（权益状态已有7日内有效记录时跳过重复检查）
PHASE 2：标题/主题去重
PHASE 2.3：最近5篇模式审计
§0.6：一次性写前规划（标题、6个h2、结尾钩子、3张图、2个增量点）
PHASE 2.5：正文结构门 + 手机端排版门
PHASE 3.1：清空编辑器，上传3张正文图并取得3个腾讯图床 URL
PHASE 3.2：生成最终 HTML → 句界拆段 → 渲染坐标优化25%/50%/75%
PHASE 3.3：整篇单次 insertHTML → 实际 ProseMirror 图片门
PHASE 3.4：封面、标签、分类、两级AI声明、发布
PHASE 4：回内容管理验证新标题处于"审核中/已发布"
```

每个 PHASE 只输出一次 PASS 或 FAIL: 具体原因。可自动修复的排版、图位、输入失败由脚本在本 PHASE 内完成，不把正常可修复问题升级为人工中断。

### §0.0 启动即进浏览器，禁止找本地待发布草稿

待发布内容根据浏览器数据现写现发；禁止先 Glob/Read *.md/*.html 寻找待发布稿。
允许读取本技能文件、状态表、生成脚本；"禁止读文件"仅针对寻找待发布正文。
编辑器内自动保存草稿必须先读取标题，防止覆盖不同任务。

### §0.1 不可越过的硬闸

- **H execCommand 整段插入**：正文必须用 `document.execCommand('insertHTML')` 单次整段插入，禁止逐块 append。对应 K19。

- **A 选题**：PHASE 0 未 PASS，不生成任何素材。
- **B 去重**：PHASE 2 未 PASS，不写正文、不生成图片。
- **C 文本质量**：PHASE 2.5 未 PASS，不进入发布表单。
- **D 永不删除已发布文章**：文章提交后，包括"审核中"，禁止删后重发；只能从"修改"入口修正平台允许修改的内容。
- **E 正文图片**：必须恰好 3 张、3 个不同 inews.gtimg.com URL、全部 naturalWidth > 0，位置为 25%/50%/75%（允许误差 ±10%，优化目标 ±3%）。失败时自动重排并整篇重插，最多 2 轮；仍失败则停止发布。
- **F 语义边界**：图片只能作为 .ProseMirror 的块级直接子节点，放在完整 <p>/<ul>/<ol>/<blockquote> 之后；禁止插入句子、段落、标题或列表项内部；禁止紧贴 h2。
- **G 写文件保护**：修改本技能必须通过 §-1；发布任务不得顺手"优化/精简"本技能。

## PHASE 0：选题红线审核（硬性，不通过不进入 PHASE 1）

### 0.1 企鹅号受众画像

- 内容中台 QQ看点：95后/00后扎堆，偏好校园生活、明星八卦、动漫二次元、电竞数码、搞笑娱乐、情感。
- 腾讯新闻/QQ浏览器/微信看一看：下沉市场，偏好民生实用、健康养生、情感家庭、正能量、实用干货。
- 平台算法偏爱（多平台运营者复盘原文）："无论哪个内容平台，只要能从财富、健康、教育等方面制造一定焦虑和恐惧，以及传播娱乐、搞笑内容，都会备受流量青睐。鸡汤性质的内容，企鹅号貌似更加偏爱。"

### 0.2 选题红线

| 类型 | 判定 | 处理 |
|:-----|:-----|:-----|
| ❌ 禁止 AI/科技/大模型/副业卖课/高知男视角 | 标题或正文以 AI 工具、模型、代码、副业赚钱为核心 | **直接 FAIL**，不写不发 |
| ❌ 禁止纯技术教程、参数对比、行业趋势分析 | 面向技术人群的内容 | **直接 FAIL** |
| ✅ 首选 国民常青赛道：游戏 | 企鹅号爆款领域第一就是游戏 | 通过（分类选「游戏」） |
| ✅ 允许 其他国民常青赛道 | 情感/家庭、民生实用干货、健康养生、历史名人轶事、搞笑娱乐、正能量 | 通过 |
| ⚠️ 例外：AI 仅作"下沉化实用技巧"载体 | 如"打工人用AI十分钟写完周报"——AI 不是主角，解决普通人麻烦才是 | 视为禁止类（FAIL），不得发布 |

### 0.3 审核动作

```
输入：待发布文章的标题 + 主题关键词
IF 命中「禁止 AI/科技/高知男视角」 → FAIL：选题违反红线，停止
IF 命中「国民常青赛道」 → PASS
IF 命中「例外(下沉化AI技巧)」 → 视为禁止类（FAIL），不得发布
```

PHASE 0 输出 FAIL → 立即熔断，不进入 PHASE 1，不准备任何素材。

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

启动后 curl 确认 http://127.0.0.1:8768/cover.jpg 返回 200。端口 8768 若被占用换端口；fetch 用 http://127.0.0.1:8768/（不用 localhost）。

## §6 封面图生成

提示词每次必须随机多变。5 元素随机组合模板，每次生成的 prompt 都不同。

脚本：`generate_image.py`（Agnes API key 已硬编码在脚本内）

```
python generate_image.py "<prompt>" cover.jpg 1024x1024
```

### 6.1 正文3图生成（固定三张、横图优先）

每张 prompt 从正文对应 h2 提取主体，B风格/C光线/D氛围三项中相邻图片至少两项不同。禁止只换文件名而复用同图。

**prompt 提取公式**：人物/主体 + 动作 + 场景 + 关键物件 + 情绪 + 时代/视觉冲突
从区块正文提取具体词汇：人名、地名、物品名、动作描述、情绪关键词。

Agnes API key 已硬编码在 `generate_image.py` 中，无需 settings.json。直接运行：

```
python generate_image.py "<IMG1 prompt>" body-1.jpg 1792x1024
python generate_image.py "<IMG2 prompt>" body-2.jpg 1792x1024
python generate_image.py "<IMG3 prompt>" body-3.jpg 1792x1024
```

验收：3个文件均存在、每个 >10KB、SHA256 三者不同；视觉内容分别对应 data-lock-h2 所在章节。

### 6.2 提示词元素表（封面用）

| 类别 | 选项 |
|:----|:-----|
| A 场景 | intense mobile gaming, close-up hands gripping phone, gaming setup RGB lights, two players face off, digital battlefield map, player lost in thought, neon-lit gaming room, smartphone match results |
| B 风格 | anime style cel shaded / photorealistic hyper-detailed / cinematic film grain anamorphic |
| C 光线 | dramatic neon backlight blue purple / soft ambient monitor glow / harsh contrast shadows / warm golden hour window |
| D 氛围 | tense competitive / melancholic reflective / energetic vibrant / mysterious suspenseful |
| E 质量 | 4K, highly detailed, masterpiece, sharp focus（固定） |

执行：A-E 各选一项，用 ", " 拼接，每次必须不同组合。

## 附录A：流量增长计划开通流程

执行条件：PHASE 1.1 检测到「申请开通」按钮
1. 找 textContent='申请开通' 且所在行含流量增长计划的 button -> click
2. wait 1s -> 找 textContent='暂不绑卡' button -> click（如弹窗）
3. wait 1s -> document.querySelector('label.omui-checkbox').click()
4. 找 textContent='同意' 且 !disabled 的 button -> click
5. 验收：状态变「已开通」，有「关闭」按钮
失败处理：弹窗未出现->重试步骤1（<=2次）；checkbox未找到->截图记录FAIL

## 附录B：修复缺失的AI声明（仅限手工发文来源）

执行条件：PHASE 1.3 发现手工发文来源的已发布文章有「未声明」标签。
1. 点该文章「修改」-> 打开编辑器
2. 找「存在未进行AI生成声明素材，请」后的「进行补充>」-> click
3. 弹「AI生成声明」对话框 -> 勾选 AI 生成的图片素材 -> 点「提交」
4. 验收：该文章显示「已完成AI生成素材声明」
微信同步来源文章：对话框提交后刷新仍「未声明」，服务端不持久化——回微信源头处理。

## §7 已知坑（硬性映射表）

| 编号 | 症状 | 根因 | 唯一解法 |
|:-----|:-----|:-----|:---------|
| K1 | 发布按钮匹配多个 | React DOM 含隐藏按钮 | textContent 精确 '===' 发布，不用 includes |
| K3 | radio 选中后提交不生效 | React 未检测 change | click + dispatchEvent(new Event('change', {bubbles:true})) |
| K5 | 页面崩溃 | 用 evaluate 删 React 管理 DOM | 所有定位用 Playwright locator |
| K6 | 封面传不上 | 浏览器禁 file chooser 脚本操作 | DataTransfer 注入 + CORS server fetch（OP-2） |
| K8 | 点发布无反应 | 标题为空校验先触发 | 发布前 evaluate 确认标题已填 |
| K11 | 页面白屏 | React 检测外部 DOM 篡改 | 始终用 locator |
| K14 | 自动保存覆盖新内容 | 编辑器自动保存 | 清除后立即填写 |
| K15 | 功能权益 tab 点不动 | 组件 ref 每次加载变化 | evaluate 遍历 textContent='功能权益' 的 li |
| K16 | 弹窗确认按钮找不到 | ref 动态生成 | textContent 匹配 + 遍历 button |
| K17 | 上传封面 fetch 失败 | CORS server 未启动 | §5 必须在 OP-2 前启动 |
| K18 | 重复发布 | 未做去重 | PHASE 2 双重去重 |
| K19 | 正文逐块 append insertHTML 被吞 | ExEditor ProseMirror schema 合并后续块 | 单次整段 insertHTML |
| K20 | 自主声明按钮 evaluate .click() 不弹窗 | 部分 React 按钮需真实手势 | locator.click({force:true}) |
| K21 | 微信同步来源补AI声明刷新仍未声明 | 企鹅号只读，服务端不持久化 | 回微信源头；本技能只对手工发文 |
| K22 | 发布报请选择分类/自主声明 | 必填项未设 | 先设分类再自主声明再发布 |
| K23 | 分类/标签 input 键入不生效 | React 受控输入 | browser_type slowly + 候选 click |
| K24 | 分类候选需逐字键入 | 必须真实 pressSequentially | browser_type slowly 模式 |
| K25 | 弹窗被遮罩拦截 | 之前弹窗未关 | evaluate 关 .omui-dialog-wrapper.open .cancel |
| K26 | 封面上传弹窗打不开 | 已有封面显示「更换」非「添加」 | browser_click 真实手势 .omui-thumb__action |
| K27 | 标签 chip 文本误判 | 容器 class 包含文本 | 查 chip 用 .omui-suggestion__chose * |
| K28 | 质量门反复跑 11 轮 | 不逐段验字数后集中补丁 | 按 §0.6 一次写满6区块；PHASE 2.5 最多两轮 |
| K29 | 发布后有未声明告警 | OP8 图片级声明未做 | OP7+OP8 都要做 |
| K30 | 封面图长得差不多 | 固定 prompt 重复 | 5 元素随机组合模板 |
| K31 | 正文全是大段文字墙 | 只有上限没下限节奏 | 390px 渲染门 + 每h2区块4-8段含<=50换气 |
| K32 | 文中图全裂 0 张渲染 | 外链非图床 src 被过滤 | 用 inews.gtimg.com 图床，验收 naturalWidth |
| K33 | 闭门造车编段长 | 不找参考凭感觉分段 | 默认用 §0.6 固定骨架；仅连续3篇0阅读才找参考 |
| K34 | 文中图与段落不相关 | 配图没根据段落提取描述 | §0.6 规划时标注 scene_prompt |
| K35 | 模型整文件覆盖导致丢失 | 未备份且用 Write 重建全文 | 修改必须走 §-1：候选文件/行数闸/备份后原子替换 |
| K36 | 质量门两次结果矛盾 | 用段落索引估算图片百分比 | 只用渲染坐标：(图中心Y-正文顶部Y)/正文高度 |
| K37 | 图片移动后编辑器回旧位置 | 直接改真实 PM DOM | 只在离线 DOM 移动，整篇单次 insertHTML |
| K38 | 图片切进一句话/标题附近 | 候选点含文本节点/h2 | 候选仅限根级 P/UL/OL/BLOCKQUOTE 后 |
| K39 | 手机端连续大段文字墙 | 只检查汉字上限没模拟行数 | 390px mobileRenderGate |
| K40 | 规划要求6图导致耗时失控 | imgMin=Math.max(3,N) | 正文图固定恰好3张，与h2数量解耦 |

### 新坑记录模板
```
新坑编号：Kxx
症状：
根因：
唯一解法：
关联步骤：
```

## §8 完整性自检（每次修改本技能后运行）

```js
function skillMarkdownIntegrity(markdown, previousLineCount) {
  const required = ['## §-1', '## §0', '## PHASE 0', '## PHASE 1',
    '## PHASE 2：', '## PHASE 2.5', '## PHASE 3', '## PHASE 4',
    '## §5', '## §6', '## §7', '## §8'];
  const lines = markdown.split(/\r?\n/).length;
  const missing = required.filter(h => !markdown.includes(h));
  const fencesBalanced = (markdown.match(/\`\`\`/g) || []).length % 2 === 0;
  const destructive = previousLineCount > 0 &&
    lines < Math.max(previousLineCount - 50, Math.floor(previousLineCount * 0.95));
  return { pass: !missing.length && fencesBalanced && !destructive,
    lines, missing, fencesBalanced, destructive };
}
```

验收必须打印：旧行数、新行数、新增/删除行数、缺失章节、代码围栏状态。任何一项失败，不得覆盖正式 SKILL.md。

### 质量标准汇总表

| 指标 | 阈值 | 验证方式 |
|:---|:----|:--------|
| 总汉字数 | ≥ 3000 | hanCount(pm.textContent) |
| 小标题 h2 | 3000-3599 汉字固定 6 个；3600+ 按 ceil(汉字/600) | h2Count |
| 单段汉字 | ≤ 150 | max(paragraphHanzi) |
| 段长中位数 | ≤ 90 | sortedParas median |
| 超长段 >120 | 占比 ≤ 10% | over120Count / totalCount |
| 相邻段 >100 | 禁止 | no adjacent > 100 |
| h2 区块 | 4-8 段；至少 1 段 ≤ 50 | perSection check |
| 正文图 | 恰好 3 张，src 全不同 | imgCount + uniqueSrcs |
| 图片位置 | 25%/50%/75% ± 10%（优化目标 ±3%） | renderRatio |
| 图片 src | 全部 inews.gtimg.com CDN | src.startsWith |
| 封面 | 腾讯图床已加载 | coverImg.naturalWidth > 0 |
| AI 声明 | OP-7 文章级 + OP-8 素材级 | declaration text + no warning |

### JS 文件索引

| 文件 | 导出对象 | 核心函数 |
|:----|:--------|:--------|
| qq_quality_gates.js | window.qqGates | hanCount / qualityGateHTML / mobileRenderGate / normalizeMobileParagraphs |
| qq_image_ops.js | window.qqImageOps | uploadOneBodyImage / bindBodyImageSources / optimizeBodyImagePositions / liveImageGate / insertArticleWithTwoPassLimit |

### 环境配置

| 工具 | 版本/路径 |
|:----|:---------|
| Agent API | 硬编码在 generate_image.py（无需 settings.json） |
| CORS 端口 | 8768（claudework 根目录） |
| Python http.server | §5 代码，需 CORS header |
| Test server 端口 | 8769（qq-publish 技能目录） |

## PHASE 3：图片四模块（硬化 SOP，不可跳过，2026-07-25 新增）

本节固化为 4 个模块依次执行。不可跳过、不可合并、不可"顺带完成"。每个模块输出指定产物，缺一项即 FAIL。

### 模块 1：正文区块提取（SOP-IMG-01）

**输入**：当前编辑器 ProseMirror 正文文本（已通过质量门 ≥ 3000 汉字、≥ 6 个 h2）

**执行**：
1. 从 `.ProseMirror.textContent` 读取全文
2. 按标题关键词找出全部 6 个 h2 区块（见账号信息标题列表）
3. 用 `totalHan * 0.25 / 0.50 / 0.75` 计算目标汉字位置
4. 找到对应区块：按累计汉字数映射到具体 h2
5. 取该区块前 3 段完整段落文本

**输出**（3 项，缺一项即 FAIL）：
```json
[
  {"img":"IMG1","h2":"标题","secHan":504,"textSample":"当年玩《魔兽世界》打熔火之心，四十个人没一个掉线的..."},
  {"img":"IMG2","h2":"标题","secHan":537,"textSample":"在游戏里聊理想、聊工作、聊人生困惑，但从来没问过对方真名叫什么..."},
  {"img":"IMG3","h2":"标题","secHan":561,"textSample":"剩下的名字就像一座数字墓园，记录着那些年你一起玩过游戏但已经走散了的人..."}
]
```

**验收**：3 个区块的 title、secHan、textSample 均已输出，每个 secHan ≠ 0。

### 模块 2：scene_prompt 生成（SOP-IMG-02）

**输入**：模块 1 输出的 3 个区块信息

**规则**（硬性，违反即 FAIL）：
1. 每张图的 prompt = 人物/主体 + 动作 + 场景 + 关键物件 + 情绪 + 时代/视觉冲突
2. 从区块正文提取具体词汇：人名、地名、物品名、动作描述、情绪关键词
3. 相邻两张图的 B风格/C光线/D氛围三项至少 2 项不同
4. 禁止随机通用游戏图、禁止只靠标题生成
5. 每张图 prompt 长度 ≥ 15 个英文关键词或用中文逗号分隔的 ≥ 6 个短语

**示例**（不允许逐字复用，仅展示格式）：
- `40玩家大战拉格纳罗斯熔火之心副本，战士坦克开盾墙牧师战复，凌晨三点灭团语音怒吼，魔兽世界风格，电影级光线，紧张战斗氛围，4K，高度细节`
- `最终幻想14风格，两个游戏角色在月光下的草地上并肩而坐，遥远幻想城市天际线，温暖月光，平静温馨氛围，动漫风格，4K，高度细节，杰作`
- `Steam好友列表显示大部分头像已变灰离线，只有几个绿色在线，电脑屏幕微蓝光照在空荡桌面上，数字墓园氛围，伤感怀旧，写实摄影风格，电影级光线，4K，高度细节`

**输出**：3 个 prompt 字符串，每行对应 IMG1/IMG2/IMG3。

### 模块 3：3 图上传拿 CDN（SOP-IMG-03）

**前置**：CORS 服务已启动（§5），模块 2 的 3 个 prompt 已就绪。

**图片生成**：
```
python generate_image.py "<IMG1 prompt>" body-1.jpg 1792x1024
python generate_image.py "<IMG2 prompt>" body-2.jpg 1792x1024
python generate_image.py "<IMG3 prompt>" body-3.jpg 1792x1024
```
Agnes API key 已硬编码在 `generate_image.py` 中，无需额外配置。
验收：3 个文件均存在、每个 > 10KB、SHA256 三者不同。

**上传取 CDN**：
对每张图，通过编辑器"插入图片"→"本地上传"→ Playwright fileChooser 原生上传：
1. 点击 `[data-toolbar-item-of="imagePlugin"]` 打开对话框
2. 点击 `.omui-upload-image-trigger` 触发 file chooser
3. `browser_file_upload` 设置文件路径
4. 等待上传完成 → 点击 `button:text-is("确认")`
5. 记录插入到 ProseMirror 中的 img src（`inews.gtimg.com/om_bt/.../641` 格式）

**输出**（3 项，缺一项即 FAIL）：
```json
{"cdn_srcs":["inews.gtimg.com/om_bt/AAAA/641","inews.gtimg.com/om_bt/BBBB/641","inews.gtimg.com/om_bt/CCCC/641"]}
```
验收：3 个 src 不同、全部以 `inews.gtimg.com` 开头、全部 `naturalWidth > 0`。

### 模块 4：按渲染坐标插图并复验（SOP-IMG-04）

**输入**：正文 HTML + 3 个 CDN src

**前置条件**：qq_image_ops.js 已注入页面（`window.qqImageOps` 可用），qq_quality_gates.js 已注入（`window.qqGates` 可用）。

**执行步骤**：

1. 从 ProseMirror 提取正文文本
2. 离线构建含 `__BODY_IMG_1/2/3` 占位符的 HTML（`data-body-img` + `data-lock-h2` 属性）
3. 调用 `bindBodyImageSources(html, cdn_srcs, [2,4,5])` 替换占位符
4. 调用 `optimizeBodyImagePositions(pm, html, {targets:{1:0.25,2:0.50,3:0.75}, rounds:3})`
5. 将优化后的 HTML 通过 `execCommand('insertHTML')` 单次整段插入
6. 调用 `liveImageGate(pm, 0.05)` 复验

**验收输出**（全部必填，缺一项即 FAIL）：
```
3 个不同 CDN src: [src1, src2, src3]
3 张图 naturalWidth: [w1, w2, w3] (全部 > 0)
3 个实际 ratio:
  IMG1 target=0.25 actual=X.XXX error=±0.0XX
  IMG2 target=0.50 actual=X.XXX error=±0.0XX
  IMG3 target=0.75 actual=X.XXX error=±0.0XX
每张图前后段落文本（prev/next 各前 50 字）
最大误差 ≤ 0.05: PASS/FAIL
```

**失败处理**：任一 ratio 误差 > 0.05 → 调整 `data-lock-h2` 锁定值重新执行步骤 2-5，最多 2 轮。2 轮仍 FAIL 则记录不动，不阻止发布。

