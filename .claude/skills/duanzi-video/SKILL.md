---
name: duanzi-video
description: 段子+配音+漫画 短视频管线（TikTok 练手）。四块组件全部实测跑通、免费、不吃本地配置。本文件是这条管线的唯一执行源与组件关联入口，流程/分镜/提示词规则在此沉淀。
version: 1.0
platform: TikTok（练手场，跑通稳定再推其他）
entry: `/duanzi-video`
---

# 段子短视频管线 v1.0

## 铁律

1. 用户不懂分镜/提示词，**全靠本技能沉淀规则**，Claude 摸索后写进本文件。
2. 四块组件**全部免费、纯云端 API、不吃本地配置**（1vCPU/1GB 服务器 + 烂电脑可跑）。
3. 技术细节只进本文件，不进内置记忆（违反全局规则1）。
4. 每个组件独立成技能，本文件只做**组件关联 + 分镜/提示词方法论 + 端到端编排**。

## 四块组件（全部实测跑通）

| 环节 | 技能 | 实测状态 |
|------|------|----------|
| 段子文案/分镜 | Claude 或 硅基流动 LLM（10B以下免费） | ✅ |
| 漫画生图 | `agnes-image`（agnes-image-2.1-flash） | ✅ 2026-07-14 跑通 |
| 中文配音 | `siliconflow-tts`（CosyVoice2-0.5B） | ✅ 跑通，8 说话人 |
| 视频合成 | animation-pipeline（ffmpeg） | ✅ 修好 4 崩溃点 |

Key 均在 settings.json env，启动自动注入。

## 架构（对标 GitHub 业界标准）

调研多个「AI 短视频生成」开源项目（RianNegreiros/AiShortsVideosGenerator、kolligopinath/AI_short_video_generator 等），流程一致：

```
主题/段子 → LLM 生成脚本+分镜
每句台词 → TTS 配音
每场景   → 生图
图+音+字幕 → 拼视频（Remotion / moviepy / ffmpeg）
```

**我们的架构 = 业界标准，且更省**：那些项目用 Google Cloud + ElevenLabs + DALL-E + AWS（全付费），我们全免费不吃配置。

## 分镜方法论（Claude 摸索沉淀）

- **颗粒度**：一句台词 = 一张图 + 一段配音 + 一行字幕。按这个单位切。
- **数量**：短视频 3-7 张图。TikTok 轮播参考 manhwa-to-tiktok 的 7 张结构（封面钩子 → 铺垫 → 冲突反转 → 高潮爆点 → 结尾补刀）。
- **节奏**：每张图只说一件事，大字少字，字幕压在画面留白处。
- **对齐**：图时长 = 该句配音时长（ffmpeg 按音轨长度定每张图持帧）。

## 漫画提示词（agnes-image）

```
Korean webtoon style, [角色/场景/情绪], clean lineart, cel shading,
soft pastel colors, clean composition, space for dialogue
```

尺寸：竖版 768x1024（实际输出按比例微调，如 864x1152）。

## 配音提示词（siliconflow-tts）

- voice 格式铁律：`模型id:说话人名`（如 `FunAudioLLM/CosyVoice2-0.5B:alex`），只传人名必 invalid。
- 8 说话人：alex/anna/bella/benjamin/charles/claire/david/diana（4男4女，全读中文）。

## 端到端编排（self-contained）

1. 写段子 + 拆分镜（每张图一句台词）。
2. `agnes-image` 逐张出图。
3. `siliconflow-tts` 逐句配音。
4. `animation-pipeline` 拼：图按音轨时长持帧 + 叠配音 + 加字幕 → 竖版 MP4。
5. 预览给用户审，再发 TikTok。

## 已知边界 / 搁置

- **sese-ai 生图（群主接口）**：workspace disabled 停机中，已用 agnes-image 替代；恢复后可做备选。
- **ChatCut（akhil-datta/ChatCut）**：Adobe PR 插件，吃配置需 PR，不适用，排除。
- 字幕叠加、图音对齐的接缝问题，待第一次端到端跑通时暴露并固化。

## 质量门（v1.0）

- [x] 四块组件各自端到端实测通过
- [x] 架构对标业界、确认免费不吃配置
- [ ] 四块首次串成一条完整短视频（待跑）
- [ ] TikTok 发布（待合成跑通稳定）
