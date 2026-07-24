---
name: agnes-image
description: Agnes AI 免费生图（agnes-image-2.1-flash）。纯云端 API 合成，不吃本地配置，适合烂电脑/1vCPU 服务器。给一段 prompt 出图，韩漫/webtoon 风格可用。漫画画面、段子配图都走它。
version: 1.0
model: agnes-image-2.1-flash（兼容 agnes-image-2.0-flash / agnes-video-v2.0）
endpoint: https://apihub.agnes-ai.com/v1/images/generations
entry: `/agnes-image` 或 `python scripts/generate.py`
---

# Agnes AI 免费生图管线 v1.1（+sese-ai 回退）

## 核心事实（实测 2026-07-22）

- **主接口**：`POST https://apihub.agnes-ai.com/v1/images/generations`（OpenAI 兼容）
- **回退接口**：`POST https://api.sese-ai.com/api/generate`（Agnes 失败时自动切换）
- **主模型**：`agnes-image-2.1-flash`（生图）、`agnes-image-2.0-flash`、`agnes-video-v2.0`（视频）
- **回退模型**：`z-image`（sese-ai，稳定；wai/Pony-3/R-1.5/Turbo-3.5 空响应不可用）
- **认证**：两个 key 都**硬编码在 scripts/generate.py 中**（不从 env/settings 读取，避免被覆盖）
  - Agnes key: `sk-37fc8...`（get_api_key() 函数）
  - sese-ai key: `AADDCC001122`（SESE_API_KEY 常量）
- **不吃本地配置**：纯云端生成，本机只下载结果图，1vCPU/1GB 服务器可用
- **延迟**：单次约 40-60s（两个接口都差不多）
- **返回**：
  - Agnes：图片 URL（在 `platform-outputs.agnes-ai.space`），需二次下载
  - sese-ai：JSON + base64（直接解码保存）

## 主流程（self-contained，自动回退）

```bash
# 默认：先试 Agnes，失败自动回退 sese-ai
python scripts/generate.py --prompt "a cute cat, korean webtoon style" --out cat.png

# 强制用 sese-ai
python scripts/generate.py --prompt "..." --provider sese --out cat.png

# 禁用回退（Agnes 失败直接报错）
python scripts/generate.py --prompt "..." --no-fallback --out cat.png

# 竖版韩漫尺寸
python scripts/generate.py --prompt "..." --size 768x1024 --out panel.png

# 批量（文件每行一条 prompt）
python scripts/generate.py --prompt-file prompts.txt --out-dir ./panels
```

## curl 直调

```bash
curl -s -k -X POST https://apihub.agnes-ai.com/v1/images/generations \
  -H "Authorization: Bearer $AGNES_API_KEY" -H "Content-Type: application/json" \
  -d '{"model":"agnes-image-2.1-flash","prompt":"a cat","n":1,"size":"1024x1024"}'
# 返回 {"data":[{"url":"https://platform-outputs.agnes-ai.space/images/t2i/xxx.png"}]}
# 再 curl -k -o out.png <url>
```
⚠️ 本地 TLS 可能验不过，curl 加 `-k` 跳过。超时设 120s。

## 实测输出规格

- 1024x1024 prompt → 1024×1024 PNG（实测 1.3MB）
- 768x1024 prompt → 864×1152 PNG（实测，按比例微调）

## 韩漫风格提示词（配合 manhwa-to-tiktok）

```
Korean webtoon style, [角色/场景/情绪], clean lineart, cel shading,
soft pastel colors, clean composition, space for dialogue
```

## 质量门（v1.1 实测通过）

- [x] agnes key 有效（硬编码在 scripts/generate.py 的 get_api_key() 中，2026-07-22 从旧会话恢复后硬编码）
- [x] sese-ai key 有效（硬编码 SESE_API_KEY = "AADDCC001122"）
- [x] 回退流程：agnes 401/超时 → sese-ai 自动接管（实测通过）
- [x] 生图端点通（agnes-image-2.1-flash 返回真实图片 URL）
- [x] 回退端点通（sese-ai z-image 返回 JSON+base64，1.19MB PNG）
- [x] 二次下载成功（1024² / 864×1152 真 PNG）
- [x] 韩漫风格出图（竖版可用）
- [x] 脚本端到端（段子配图 864×1152 PNG）

## 已知问题 / 边界

- Agnes 返回的是 **URL 不是 base64**，必须二次下载（和 sese-ai 的 base64 模式不同）
- sese-ai 返回 **JSON+base64**，直接解码保存（无需二次下载）
- 尺寸是「建议值」，实际输出可能按比例微调（768x1024 → 864x1152）
- sese-ai 延迟较高（40-60s），网络不稳定时可能 524（Cloudflare 超时），已设 300s 超时
- sese-ai 只有 `z-image` 模型稳定（wai/Pony-3/R-1.5/Turbo-3.5 返回空响应）
- 回退逻辑：Agnes 任何异常（401/429/500/超时）→ 自动切 sese-ai

## 关联

- 配音：siliconflow-tts（CosyVoice2 中文配音，免费不吃配置）
- 合成：animation-pipeline（ffmpeg 把图/配音组合成视频）
- 目标管线：段子文案(LLM) + 漫画画面(本技能) + 配音(siliconflow-tts) + 合成(ffmpeg)


---

## 收尾核验（强制末步）

- 回看核心规则①（`~/.claude/CLAUDE.md` 永久原则第一条）：平台技术细节（DOM/API/坐标/SOP/已知问题）只进本技能文件，不进内置记忆；本次修正与复盘已直接编入本 SKILL.md，未写多余记忆文件。
- 反馈即修技能——若本次暴露新堵塞点/选择器/绕过方案，当场写入对应章节（留版本号），不依赖记忆回看。
