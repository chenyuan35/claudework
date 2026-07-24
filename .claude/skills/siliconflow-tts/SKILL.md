---
name: siliconflow-tts
description: 硅基流动免费中文配音（CosyVoice2-0.5B）。纯云端 API 合成，不吃本地配置，适合烂电脑/1vCPU 服务器。给一段中文文本，输出 wav/mp3 语音。段子配音、旁白、画外音都用它。
version: 1.0
model: FunAudioLLM/CosyVoice2-0.5B（硅基流动 10B 以下免费档）
entry: `/siliconflow-tts` 或直接 `python scripts/tts.py`
---

# 硅基流动免费中文配音管线 v1.0

## 核心事实（实测 2026-07-14）

- **接口**：`POST https://api.siliconflow.cn/v1/audio/speech`（OpenAI 兼容）
- **模型**：`FunAudioLLM/CosyVoice2-0.5B` — 免费（硅基流动 10B 以下免费档）
- **认证**：`Authorization: Bearer $SILICONFLOW_API_KEY`（**硬编码在 scripts/tts.py 的 get_api_key() 中**，不从 env/settings 读取，避免被覆盖）
- **不吃本地配置**：纯云端合成，本机只收音频文件，1vCPU/1GB 服务器可用
- **语言**：中文 + 方言（粤语/四川话/上海话/天津话）、英文、日语、韩语

## 🔑 voice 字段铁律（踩过的坑）

`voice` 必须是 **`模型id:说话人名`** 完整格式，**不能只传说话人名**：

- ✅ 正确：`"voice": "FunAudioLLM/CosyVoice2-0.5B:alex"`
- ❌ 错误：`"voice": "alex"` → `20047 Invalid voice`
- ❌ 错误：`"voice": "中文女"` / `"female"` / `"zh-CN"` → 全部 invalid

### 可用说话人（8 个，全部能读中文）

| 说话人 | 性别 | | 说话人 | 性别 |
|--------|------|--|--------|------|
| alex | 男 | | claire | 女 |
| anna | 女 | | david | 男 |
| bella | 女 | | diana | 女 |
| benjamin | 男 | | charles | 男 |

## 主流程（self-contained）

```bash
# 单条配音
python scripts/tts.py --text "你今天咋这么倒霉呢，笑死我了" --voice anna --output clip.wav

# 批量（文件每行一段，输出到目录）
python scripts/tts.py --file lines.txt --voice alex --out-dir ./vo

# mp3 格式
python scripts/tts.py --text "..." --voice bella --format mp3 --output clip.mp3
```

## curl 直调（无 python 时）

```bash
curl -s -k -H "Authorization: Bearer $SILICONFLOW_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"FunAudioLLM/CosyVoice2-0.5B","input":"文本","voice":"FunAudioLLM/CosyVoice2-0.5B:alex","response_format":"wav"}' \
  -o clip.wav https://api.siliconflow.cn/v1/audio/speech
```
⚠️ 该接口 `Transfer-Encoding: chunked`，用 curl 时确保 `-o` 落文件；本地 TLS 证书链可能验不过，加 `-k` 跳过。

## 输出规格

- WAV: PCM s16le, 24000Hz, mono
- 时长 ≈ 文本长度（中文约 4~5 字/秒）

## 已知问题 / 边界

- **本地 TLS**：直连 api.siliconflow.cn 若证书验不过，curl 加 `-k`；requests 库正常。
- **短文本**：极短文本（如"你好"）可能只有 0.8s，正常。
- **方言**：需在 `prompt` 字段加自然语言指令（如"用四川话说："），未充分实测。
- **音色克隆**：CosyVoice2 支持传 `reference_audio`(base64) 做 zero-shot 克隆，本技能未封装（字段格式待实测）。

## 质量门（v1.0 实测通过）

- [x] key 有效（DeepSeek-V3 + TTS 均通）
- [x] voice 格式 `模型id:说话人名` 确认（GitHub MoneyPrinterTurbo/DeepTutor 交叉验证）
- [x] 8 个说话人中文出声（anna 9.6s / alex / bella / benjamin / claire 全 audio/wav）
- [x] 脚本端到端（段子文本→5.5s 中文 wav，257KB）
- [x] key 已入 settings.json env（备份 settings.json.bak_20260714）

## 关联

- 合成进视频：`animation-pipeline`（ffmpeg 把配音叠到动画/漫画画面上）
- 漫画画面：`manhwa-to-tiktok`（Agens 生图）— 待 sese-ai workspace 解封或走 Agens 网页
- 组合目标：段子文案(Claude) + 漫画画面(Agens) + 配音(本技能) + 合成(ffmpeg) = 搞笑短视频


---

## 收尾核验（强制末步）

- 回看核心规则①（`~/.claude/CLAUDE.md` 永久原则第一条）：平台技术细节（DOM/API/坐标/SOP/已知问题）只进本技能文件，不进内置记忆；本次修正与复盘已直接编入本 SKILL.md，未写多余记忆文件。
- 反馈即修技能——若本次暴露新堵塞点/选择器/绕过方案，当场写入对应章节（留版本号），不依赖记忆回看。
