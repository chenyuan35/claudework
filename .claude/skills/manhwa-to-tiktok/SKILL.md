---
name: manhwa-to-tiktok
description: TikTok热梗→韩漫风格图文轮播全自动管线。每天抓TikTok热榜、挑活梗、Agens出7-9张韩漫画风的图、Playwright自动发布。不是漫画连载，是热梗二创。
version: 2.1
platform: TikTok Creator（creator.tiktok.com）
model: Agens（agnes-image-2.1-flash）
browser: Playwright Extension（mcp__playwright__*）
entry: `/manhwa-to-tiktok`
related: 无（Step4 发布流程已内联自包含于本技能，不依赖外部图文技能）

铁律：
  1. 这不是漫画连载。是单条TikTok图文轮播，7-9张，一个梗，完事。
  2. 选题只来自今天TikTok热榜，不拍脑袋编。
  3. 不发连续剧，不建世界观，不做角色记忆。
  4. 每次执行后复盘：这篇数据怎么样？下篇怎么调？
  5. 所有流程结论直接改本技能，不留记忆。
---

# 韩漫风 → TikTok热梗图文轮播 全自动管线 v2.1

## 核心逻辑

一条TikTok图文轮播 = 一个热梗 + 7-9张韩漫风格图 + 标题文案 + 标签

不是"开始连载一部漫画"，是"今天这个梗火了，做一条"。

---

## 韩漫视觉语言参考（每次生成前必须读）

### 1. 面板结构（Panel Layout）
- **条漫**是一张长图里包含1-2格画面，不是"每张图一页"
- 标准WEBTOON canvas：800×1280px（手机全屏），画图时用1600宽再缩小
- 每格画面占画面的60%-80%，其余是留白/背景/间隔
- **格间间距**（gutter）也是一格：控制阅读速度，短间距=快速，长间距=停顿

### 2. 角色构图
- 角色集中在画面中下部，**顶部留空**给气泡或背景
- 特写+中景+远景交错，每话至少3种镜头
- 韩漫最标志性构图：特写眼神+半张脸 → 情绪冲击
- 不要让角色占满整个画面，留30%空间

### 3. 台词与气泡（这页最重要）
- **气泡位置**：放在画面空白处（通常是顶部/左侧/右上角），绝不能盖脸
- **气泡样式**：白底+细黑边框，圆形或椭圆，尾部指向说话者
- **每格气泡数**：≤3个，太多就拥挤
- **文字量**：每气泡≤2句话，约10-20字。长台词需要拆成多个气泡
- **阅读顺序**：上→下，左→右
- **旁白/内心独白**：用长方形框，放在画面顶部或底部，不带尾部
- **语气变化**：喊叫=锯齿边框，轻声=虚线，思考=云朵形

### 4. 角色一致性（最容易被忽视）
- 发型、脸型、瞳色、服装在每一格必须完全一致
- AI生图必须用相同的prompt描述+固定seed
- 同一话里角色不要换衣服（省去AI混淆）
- 多人场景要指定每个人的位置（左/右/前/后）

### 5. 韩漫画风关键词（Agens prompt用）
```
Korean webtoon style, manhwa art style, 
clean bold line art, flat colors with soft cell shading, 
slender elegant proportions, large expressive eyes, sharp jawline, 
smooth skin texture, glossy rendering, cinematic lighting, 
soft gradients, muted sophisticated color palette
```

### 6. 配色方向参考
| 氛围 | 色彩 | 场景例子 |
|------|------|---------|
| 温暖治愈 | 米白+暖橙+浅棕 | 餐厅、居家、咖啡店 |
| 浪漫甜美 | 粉+薰衣草紫+奶白 | 约会、校园 |
| 冷峻悬疑 | 深蓝+石板灰+冷白 | 办公室、夜晚 |
| 活力搞笑 | 亮黄+薄荷绿+珊瑚粉 | 喜剧、吐槽场景 |
| 暗黑动感 | 深红+黑+霓虹紫 | 变身、夜店、逆袭 |

启动时自动抓取当前TikTok热榜，筛选适合做图文的梗。
适合图文化的话题特征：
- 生活场景型（"和我吃饭从不A钱之人"）
- 神转折型（"我以为……结果……"）
- 吐槽型（"当代年轻人的XX"）
- 共鸣型（"干什么都一个人"）

不适合的：新闻时事、明星八卦、政策类。

筛选结果：
- 选1-2个可做梗
- 判断标准：画面感强不强？能不能用7-9张图讲清楚？评论区能不能吵起来？

---

## Step 1：拆梗 → 7张分镜（不做起承转合）

不要传统"起承转合"故事结构。TikTok轮播的节奏更简单：

```
[封面] 标题大字 + 钩子画面
[1-2] 铺垫/场景建立：这人啥情况？
[3-4] 冲突/反转：事情不对劲了
[5-6] 高潮/爆点：笑点/扎心/名场面
[7] 结尾：神补刀/反转/互动钩子
```

每张图只说一件事。文字直接怼图上，大字，少字。

---

## Step 2：Agens 出图

### 2.1 Prompt 铁律
每张图 prompt 结构必须严格遵循：
```
[角色卡 完全不变] + [场景+动作+镜头+情绪] + [调色板 完全不变] + [风格标签 完全不变] + "clean composition, space for dialogue"
```

**关键**：
- 引用具体韩漫名作为风格参考：`"manhwa art style similar to True Beauty"` —— 效果远好于泛泛的 "Korean webtoon style"
- 风格标签：`"semi-realistic Korean manhwa art style, full color, clean linework, cel shading, soft skin rendering, dramatic lighting"`
- 每张图必须包含 `"clean composition, space for dialogue"` —— 空出位置给台词
- 绝对不变：角色卡一个词都不能改；调色板一个词都不能改

### 2.2 角色卡模板（一字不改）
```json
{
  "name": "小美",
  "physical": "Young Korean woman, 22 years old. Oval face with soft jawline, straight slim nose, full lips. Large almond-shaped eyes with double eyelids, long curled lashes, naturally arched eyebrows.",
  "hair": "Shoulder-length straight dark espresso brown hair, center part, tucked behind ears. Shiny healthy texture.",
  "body": "Slender elegant figure, 170cm. Long neck, slim shoulders. Model proportions.",
  "clothing": "Beige oversized single-breasted blazer, white silk camisole underneath, high-waisted light blue straight-leg jeans.",
  "expression_anchors": {
    "happy": "smiling crescent eyes, slightly parted lips, raised apple cheeks",
    "annoyed": "flat neutral mouth, one eyebrow slightly raised, half-lidded eyes",
    "dead": "droopy half-closed eyes, slack jaw, slight dark circles under eyes",
    "mischievous": "one eyebrow arched, one-sided smirk, sparkling eyes"
  }
}
```

### 2.3 完整 prompt 示例
```
Young Korean woman 22 years old. Oval face with soft jawline, straight slim nose, full lips. Large almond-shaped eyes with double eyelids, long curled lashes, naturally arched eyebrows. Shoulder-length straight dark espresso brown hair, center part, tucked behind ears. Slender elegant figure 170cm. Beige oversized blazer, white silk camisole, light blue jeans. 
{sitting at desk looking exhausted, droopy half-closed eyes, slack jaw, head resting on hand, grey office background, medium shot}
{muted desaturated palette, cool grey and beige tones} 
semi-realistic Korean manhwa art style, full color, clean linework, cel shading, soft skin rendering, dramatic lighting. manhwa art style similar to True Beauty.
clean composition, space for dialogue. no text, no watermark
```

### 2.4 角色锁定流程（新角色必做）
1. 写角色卡
2. 用角色卡 + seed 生成3种表情测试（开心/不爽/死鱼眼）
3. 检查一致性：如果3张图的脸不同 → 改角色卡直到一致
4. 锁定 seed 值，后续所有图用同一个 seed + 同一张角色卡

### 2.5 台词处理
- AI 无法正确生成中文文字，**不在 prompt 里写中文**
- AI 出图时用 `"clean composition, space for dialogue"` 留出空白
- 出图后用 Python 检测空白区域，填入正确中文（楷体/可爱字体）
- 每个气泡≤2句话，≤3个气泡/格

---

## Step 3：加文字（Pillow 处理）

文字规则：
- 对话/旁白：微软雅黑粗体 36-48px
- 封面标题：72-96px，白字+黑色描边，覆盖底部偏左
- 每张图文字 ≤ 20字
- 文字不是气泡，是直接叠图上

---

## Step 4：发布

复用 tiktok-image-ops 的 Playwright 发布流程：
1. 导航 creator.tiktok.com → 登录检查
2. 点"发布作品"→"图文"
3. 按顺序拖入图片
4. 填文案（从梗出发，带话题标签）
5. 确认发布

---

## 选题库 & 迭代

每次执行后记录到 `references/选题数据.md`：

```
日期 | 选题 | 来源热榜 | 图片数 | 文案 | 播放量 | 点赞 | 评论 | 复盘
```

复盘分析维度：
- 这个梗的评论率为什么高/低？
- 哪张图流失率最高？
- 下次同类梗怎么调整？

---

## 熔断

- Agens 连续超时 3 次 → 停
- Playwright 发布失败 2 次连续 → 停
- 选题筛不出可做梗 → 不硬做，报告今天热榜不适合
