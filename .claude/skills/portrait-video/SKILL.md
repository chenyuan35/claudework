---
name: portrait-video
description: sese-ai 美女写真人像 → GSAP Spring 弹性动画 → Canvas 帧捕获 → ffmpeg 渲染 MP4 → (可选)发抖音。内置复盘升级机制。
version: 1.0
platform: 本地 (Python + GSAP + Playwright + ffmpeg)
mode: 半自动 · 生图→动画→审核→发布
entry: `/portrait-video [n=8]` — 生成 n 张同角色不同动作图片 → GSAP 弹性动画 → 帧捕获 → MP4
---

# 写真人像 → 弹性动画视频管线 v1.0

> **一次调用，全链路执行**：sese-ai 批量生图 → 质量审查 → GSAP spring 动画 → Canvas 帧捕获 → ffmpeg 渲染 MP4 → 用户审核 → (可选)发抖音

## 管线总览

```
/portrait-video [图片数量]
  |
  +- Phase 0：前置检查
  |    +- ffmpeg / Node 环境确认
  |    +- 清理上次临时文件
  |    +- sese-ai API 连通性
  |
  +- Phase 1：批量生图（sese-ai）
  |    +- 选角色特征 + seed 族
  |    +- 每条 prompt = 角色基座 + 不同动作/场景
  |    +- 写入 items 数组批量请求
  |    +- 保存到 temp/images/
  |
  +- Phase 1.5：质量审核
  |    +- 逐张预览，check：五官一致性 / 皮肤质感 / 构图 / 光线
  |    +- 不满意的局部重生成（换 seed）
  |    +- 用户确认通过才继续
  |
  +- Phase 2：GSAP Spring HTML 生成
  |    +- back.out(1.7) 弹性 overshoot → settle
  |    +- power2.inOut 1.0s crossfade 过渡
  |    +- canvas drawImage + 帧捕获（sendBeacon）
  |    +- 可选：zoom 范围 / 过渡节奏 / 总时长
  |
  +- Phase 3：帧捕获管线
  |    +- 启动 capture server（端口 18998）
  |    +- Playwright Extension 打开 HTML 页面
  |    +- canvas sendBeacon → Python server 收集 base64 PNG
  |    +- ⚠️ server 不能走 bash 后台（会被 kill）
  |
  +- Phase 4：ffmpeg 渲染 MP4
  |    +- base64 解码写入帧目录
  |    +- ffmpeg -framerate 30 → libx264 yuv420p
  |    +- 检查输出大小 / 时长
  |
  +- Phase 5：审核 → 发抖音
  |    +- 用户预览 MP4
  |    +- 通过 → `/character-douyin` 发抖音
  |    +- 不通过 → 复盘 → 迭代
  |
  +- Phase 6：复盘（强制！）
       +- 填写 Retro Block
       +- 有阻塞点 → 立即修改 SKILL.md
       +- 质量提升点 → 更新 Prompt 工程 / 参数
```

## 前提条件

- sese-ai API token 有效（`Bearer AABBCC112233`）
- Playwright Extension (mcp__playwright__*) 连接正常
- ffmpeg 8.1.1+ 在 PATH
- Python 3.13 + requests / http.server (stdlib)
- 抖音浏览器登录有效（发抖音时需要）

---

## Phase 0：前置检查

```python
import os, shutil, subprocess, requests

# 0.1 清理上次生成
for d in ["v8_temp/images", "v8_frames", "temp_frames"]:
    if os.path.exists(d): shutil.rmtree(d)

# 0.2 确认 ffmpeg
subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)

# 0.3 测试 sese-ai 连通性
resp = requests.post("https://api.sese-ai.com/api/generate", headers={
    "Authorization": "Bearer AABBCC112233",
    "Content-Type": "application/json"
}, json={"prompt": "test", "steps": 1}, timeout=15)
assert resp.ok, f"sese-ai 不通: {resp.status_code}"
```

---

## Phase 1：批量生图（sese-ai API）

### 1.1 API 参数（Z-Image-Turbo 强制锁定）

| 参数 | 值 | 说明 |
|------|-----|------|
| url | `POST https://api.sese-ai.com/api/generate` | |
| auth | `Bearer AABBCC112233` | |
| 模型 | — | 强制使用 Tongyi-MAI/Z-Image-Turbo，传 model/base 被忽略 |
| steps | **2-4** | Turbo 模型的最佳步数，>4 无改善且可能降质 |
| cfg | **1.0** | Turbo 下 cfg=1 效果最好 |
| sampler | euler | |
| width/height | 768×1024 或 720×1280 | 适配 9:16 竖屏构图；1024×1024 也可（需裁剪） |
| batch | `items: [{prompt, width, height, steps, seed}]` | 批量生图 |

### 1.2 角色 Prompt 工程

**权重排序（从高到低）：**
1. **镜头参数**（单反+焦距+光圈）— 最高权重
2. **胶片模拟**（Kodak Portra 400 / Fuji Pro 400H）
3. **光线方向**（soft window light / Rembrandt / butterfly）
4. **皮肤质感**（natural skin texture / subtle skin details）
5. **画质标记**（photorealistic / 8k / highly detailed）
6. **情绪/状态**（relaxed / thoughtful / gentle smile）
7. **禁止词**（no makeup / no plastic / no airbrush）

**角色基座模板：**
```
cinematic shot of a beautiful [国籍] woman, [年龄] years old,
[发型/颜色], [肤色/肤质], [五官特征], wearing [服装],
photorealistic, 8k quality, [镜头], [胶片], [光线], [皮肤质感]
```

**实战验证过的基座（seed 300 族）：**
```
cinematic shot of a beautiful Asian woman, 25 years old,
long black hair, fair skin, elegant features, wearing a white silk blouse,
photorealistic, 8k quality
+ 85mm f/1.4, Kodak Portra 400, soft window light, natural skin texture
```

### 1.3 动作/场景变化

每张图追加不同动作描述，共享角色基座 + seed 族（seed 300+n）：

| # | 动作 |
|---|------|
| 1 | standing by window, holding coffee cup, morning sunlight, soft smile |
| 2 | sitting at desk, typing on laptop, concentrated, warm lamp light |
| 3 | walking in park, looking back, autumn leaves falling |
| 4 | leaning against bookshelf, reading, cozy library |
| 5 | lying on sofa, scrolling phone, afternoon sunlight |
| 6 | stretching arms in bedroom, messy hair, morning |
| 7 | cooking in kitchen, stirring pot, steam rising |
| 8 | sitting on balcony, watching sunset, wind blowing |

### 1.4 sese-ai API 调用（Python 批次）

```python
items = [{
    "prompt": f"{BASE_PROMPT}, {action}",
    "width": 768, "height": 1024,
    "steps": 4, "cfg": 1.0,
    "sampler": "euler",
    "seed": 300 + i
} for i, action in enumerate(ACTIONS)]

resp = requests.post("https://api.sese-ai.com/api/generate", headers={
    "Authorization": "Bearer AABBCC112233",
    "Content-Type": "application/json"
}, json={"items": items}, timeout=180)

for i, img in enumerate(resp.json().get("images", [])):
    if img.get("ok") and img.get("b64"):
        with open(f"v8_temp/images/img_{i+1}.png", "wb") as f:
            f.write(base64.b64decode(img["b64"]))
```

---

## Phase 1.5：质量审核（用户确认前不进动画）

**每张图检查清单：**
- [ ] 五官一致（同一人的脸型/眼型/嘴型？）
- [ ] 皮肤自然（有质感 vs AI 光滑塑料感？）
- [ ] 构图合理（人物在画面中的位置？）
- [ ] 光线统一（所有图的光源方向一致？）
- [ ] 没有变形/崩坏（手指、眼睛、背景？）

**不满意的图：** 单独重生成（换 seed，微调 prompt），不重跑全部。

**只有用户说「过了」才进入 Phase 2。**

---

## Phase 2：GSAP Spring HTML 生成

### 2.1 动画参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| 图片数 N | 8 | |
| 每张停留 DUR | 4.0s | |
| 总时长 | N × DUR = 32s | |
| 分辨率 | 720×1280 | 9:16 竖屏 |
| FPS | 30 | |
| zoom 范围 | 1.0 → 1.18 | back.out(1.7) spring |
| crossfade | 1.0s power2.inOut | 图片间过渡 |
| 帧采样 | gsap.ticker.frame%2===0 | 每 2 tick 一帧 ≈15fps |

### 2.2 Canvas 绘制逻辑

```
draw(idx, zoom, nextIdx, crossAlpha):
  1. clearRect + fill('black')
  2. scale = 1 + zoom × 0.18 → drawImage main
  3. if crossAlpha > 0.01:
     draw next image with globalAlpha=crossAlpha
     next zoom = 1 + (1-crossAlpha) × 0.12 (反向缩小)
```

### 2.3 帧捕获（sendBeacon → Python）

HTML 端每 2 tick 调用 `sendFrame()`:
```javascript
C.toBlob(b => {
  const r = new FileReader();
  r.onload = () => navigator.sendBeacon(
    `http://127.0.0.1:18998/`,
    JSON.stringify({b64: r.result.split(',')[1], w:720, h:1280})
  );
  r.readAsDataURL(b);
}, 'image/png');
```

### 2.4 HTML 嵌入到 Python 生成

使用 `agent_v8.py` 的 `make_html()` 函数：把输出分辨率、端口号、图片路径、动画参数全部硬编码到 HTML 字符串中，避免加载外部文件。

---

## Phase 3：帧捕获管线

### 3.1 启动帧捕获 Server

```python
# ⚠️ 关键：必须在主线程/daemon thread 启动，不能走 bash &
server = HTTPServer(("127.0.0.1", 18998), FrameHandler)
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()
```

**⚠️ 已知问题：之前失败因为走 `python script.py &` → bash 结束 → Python 进程被杀。已修复：用 daemon thread 启动 server（见上方代码），不走 `start /B`（Windows Git Bash 下 `/B` 被误读为 B 盘路径）**

### 3.2 Playwright 打开 HTML → 自动捕获

```python
# 用 preview_start 或直接 browser_navigate 到 HTML
browser_navigate("file:///C:/Users/59314/claudework/v8_temp/gsap_spring.html")
# 等待 done 信号
time.sleep(85)  # 32s动画 + buffer
```

或者用 preview 面板：
1. `preview_start` 一个静态文件 server 或直接 file://
2. HTML 内 GSAP 自动播放 → 自动 sendBeacon → server 收帧
3. 动画结束后发 `{_done: true}` 信号

### 3.3 帧数预期

- 总帧数 = N × DUR × FPS = 8 × 4 × 30 = 960
- 实际捕获（15fps 采样）≈ 480 帧
- 少于 100 帧 → 有问题，检查 server 是否存活

### 3.4 帧写入 + ffmpeg

```python
for i, fr in enumerate(frames):
    with open(f"v8_frames/f_{i:06d}.png", "wb") as f:
        f.write(base64.b64decode(fr["b64"]))

subprocess.run([
    FFMPEG, "-y", "-framerate", str(FPS),
    "-i", "v8_frames/f_%06d.png",
    "-c:v", "libx264", "-preset", "medium",
    "-crf", "18", "-pix_fmt", "yuv420p",
    "agent_v8.mp4"
], check=True)
```

### 3.5 视频规格

| 规格 | 值 |
|------|-----|
| 格式 | MP4 (H.264) |
| 分辨率 | 720×1280 (9:16) |
| 帧率 | 30fps |
| CRF | 18（高质量） |
| 色域 | yuv420p |
| 文件大小 | ~15-25MB（32s） |

---

## Phase 4：用户审核

- 用 `preview_*` 播放 MP4 给用户看
- 用户确认「过」→ 进 Phase 5 发抖音
- 用户说「改」→ 复盘 → 调整参数重跑
- 用户说「不要再来幻灯片忽悠我」→ **反思是否又回到了 slideshow 模式，考虑换动画方案**

---

## Phase 5：发抖音（复用 character-douyin 技能）

```
/character-douyin C:\Users\59314\claudework\agent_v8.mp4
```

把生成的 MP4 放到项目路径下，调用抖音发布技能上传。

---

## Phase 6：复盘（强制！每轮必须执行）

### Retro Block

| 字段 | 填写 |
|------|------|
| 版本 | v1.0 |
| 日期 | YYYY-MM-DD |
| N | 8 |
| 种子族 | 300-307 |
| 图质评分 | ★★★☆☆ |
| 动画评分 | ★★★☆☆ |
| 用户反馈 | [用户原话] |
| MP4 路径 | agent_v8.mp4 / ❌ 未生成 |

### 复盘三问

1. **WHY 成功/失败？**
   - 图质：prompt 是否用了镜头+胶片+光线？steps/cfg 是否正确？
   - 动画：GSAP spring 效果 vs slideshow？用户是否认可？
   - 管线：server 是否存活？帧数是否达标？

2. **WHY 这次这么改？**
   - 本次调整了哪些参数/prompt/流程？依据是什么？

3. **WHY 可能错？**
   - 遗漏了什么？下次什么条件下需要换方案？

### 阻塞点 → 立即修 SKILL.md

| 发现 | 修复动作 | 已更新 |
|------|---------|--------|
| [问题] | [解决方案] | ✅/❌ |

### 质量提升点

| 领域 | 本次学到 | 下次应用 |
|------|---------|---------|
| Prompt 工程 | | |
| 动画参数 | | |
| 管线稳定 | | |
| 配乐/BGM | | |

---

## 已知问题与约束

### sese-ai
- **无视频 API**：`/api/video/generate` 和 `/api/generate/video` 均为 404
- **模型锁定**：Z-Image-Turbo (Tongyi-MAI)，参数 model/base 被忽略
- **Turbo 参数学**：steps=2-4, CFG=1.0 效果最好，>4 步无改善
- **seed 一致性**：同一 seed 族不同 prompt 生成相同角色，但 Turbo 模型角色一致性有限

### 帧捕获
- **Server 生命周期**：不能走 bash `&` 后台——bash 结束会 kill 子进程
- **帧数折损**：canvas.toBlob + sendBeacon 异步，实际捕获 ≈50% 帧率
- **90s 超时**：HTML 内 `setTimeout(()=>location.reload(), 90000)` 自动刷新

### 动画
- 本质是 still image → Ken Burns zoom + crossfade → 用户可能仍然觉得是「幻灯片」
- 真实动画方向（待探索）：nsr-engine (LivePortrait) ONNX CPU 面部驱动 / OpenMontage/Remotion

---

## 版本日志

| 版本 | 日期 | 变更 |
|------|------|------|
| v1.0 | 2026-06-29 | 初始版本。sese-ai 批量生图 + GSAP spring + Canvas 帧捕获 + ffmpeg 渲染 |

---

## 附录：快速启动脚本

### 完整手动流程（建议逐步执行）

```
Step 1: python agent_v8.py                    # 生图 + HTML + server 一次性启动
  OR:
Step 1a: python -c "batch_generate代码段"     # 只生图
Step 1b: python -c "make_html代码段"          # 只生成 HTML

Step 2: # 启动 server（必须用 daemon 方式）
        python v8_capture_server.py &

Step 3: # Playwright 打开 HTML
        browser_navigate("file:///C:/.../v8_temp/gsap_spring.html")

Step 4: # 等待 85s → 检查 v8_frames/ 是否有文件
        ls v8_frames/ | wc -l

Step 5: # 如果帧数太少 → 重来（检查 server 是否存活）
        # 如果帧数 ≥ 100 → ffmpeg 已经自动渲染
```

### 核心文件

| 文件 | 作用 |
|------|------|
| `agent_v8.py` | 完整管线：生图→HTML→server→捕获→渲染 |
| `v8_capture_server.py` | 独立帧捕获服务器（port 18998） |
| `v8_player.html` | 播放页面（v8_images/ 目录） |
| `v8_temp/gsap_spring.html` | GSAP 弹力动画页（images/ 目录） |
| `v8_temp/images/img_*.png` | 生成的角色图片 |
| `v8_frames/f_*.png` | 捕获的帧 PNG |
| `agent_v8.mp4` | 最终输出视频 |

---

## 附录：未来方向

- [ ] **nsr-engine** (LivePortrait ONNX CPU)：面部驱动——让角色眨眼、微笑、转头。这是真正的动画，不是 slideshow
- [ ] **OpenMontage/Remotion**：React 组件驱动 spring 弹性动画，更灵活的编排
- [ ] **光流变形过渡**（agent_v6 已验证）：OpenCV Farneback optical flow warp 替代 crossfade
- [ ] **PoseLandmarker 动态姿态**：MediaPipe → 姿态序列驱动角色变化
- [ ] **BGM 自动配乐**：复用抖音卡点或本地 ffmpeg 混音
- [ ] **多角色同框**：2+ 角色互动动画
