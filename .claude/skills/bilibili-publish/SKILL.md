---
name: bilibili-publish
description: B站视频投稿全流程：GSAP/程序化动画上传→封面→创作声明→标题/描述/标签→发布。Vue 2 组件直接操控 onFileSelected + handleUpload 绕过 file input 限制。
version: 2.2
platform: bilibili 创作中心（member.bilibili.com）
mode: 半自动 · Vue 2 组件操控 + Element Plus el-select
---

# B站视频投稿技能

> 本技能适用于 GSAP 程序化角色动画/创意编程视频发布到 B站。
> ⚠️ 2026-06-30 端到端全链路测试通过（上传→封面同步→创作声明→发布→管理页"已通过"确认）

---

## 1. 访问入口

- **投稿页**：`https://member.bilibili.com/york/videoup?new`
- 必须先已登录（显示"成为UP主的第 N 天"）
- 注意：直接从子域名访问，不要在 `member.bilibili.com/platform/upload/video/frame`（micro-app 沙箱环境）操作
- 导航离开投稿页可能触发 `beforeunload` 对话框 → `browser_handle_dialog({accept: true})`

---

## 2. 视频上传（关键步骤）

### 2.1 依赖：本地 HTTP 文件服务器（视频用 port 18888，封面用 port 18889）

B站的上传组件使用 Vue 2，file input 被 `display: none` 隐藏，Chrome 的 `DOM.setInputFiles` 被安全策略拦截。

**解法**：通过 Vue 组件的 `onFileSelected` / `handleUpload` 方法直接注入 File 对象。

```python
# 视频 CORS 服务器（port 18888）
# ⚠️ 模板脚本，每次执行前替换两处：① DIR = 视频所在目录的绝对路径；② 'energy-core-60.mp4' = 本次视频文件名
# DIR 必须写绝对路径（如 r'C:\Users\59314\claudework\gsap-character-template\exports'），不要用相对路径计算——依赖 CWD 会 404
python -c "
import http.server, socketserver, os
DIR = r'C:\Users\59314\claudework\gsap-character-template\exports'  # ← 每次替换为实际目录
PORT = 18888
class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        filepath = os.path.join(DIR, 'energy-core-60.mp4')  # ← 每次替换为实际文件名
        if not os.path.isfile(filepath): self.send_error(404); return
        with open(filepath, 'rb') as f: data = f.read()
        self.send_response(200)
        self.send_header('Content-Type', 'video/mp4')
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        self.end_headers(); self.wfile.write(data)
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
    def log_message(self, fmt, *a): pass
socketserver.TCPServer(('127.0.0.1', PORT), Handler).serve_forever()
" &
```

```python
# 封面 CORS 服务器（port 18889）
python -c "
import http.server, socketserver, os
DIR = r'C:\Users\59314\claudework'
PORT = 18889
class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        filepath = os.path.join(DIR, '_bilibili_cover.jpg')
        if not os.path.isfile(filepath): self.send_error(404); return
        with open(filepath, 'rb') as f: data = f.read()
        self.send_response(200)
        self.send_header('Content-Type', 'image/jpeg')
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers(); self.wfile.write(data)
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
    def log_message(self, fmt, *a): pass
socketserver.TCPServer(('127.0.0.1', PORT), Handler).serve_forever()
" &
```

### 2.2 视频上传执行

```javascript
// Step 1: fetch 视频文件
const response = await fetch('http://127.0.0.1:18888/energy-core-60.mp4');
const blob = await response.blob();
const file = new File([blob], 'energy-core-60.mp4', { type: 'video/mp4' });

// Step 2: 找到 BccUpload 组件
const vm = document.querySelector('.bcc-upload.upload').__vue__;

// Step 3: 确保 draggable 打开
vm.draggable = true;

// Step 4: 注入文件
vm.onFileSelected([file]);

// 上传中 → 上传完成（8.7MB 约 2-5s）
```

### 2.3 上传成功后页面信号

- 左侧视频列表出现文件名项，状态为"上传完成"
- 出现"更换视频"按钮
- 右侧出现投稿编辑表单

⏱ **等待时间建议（v2.2 修正）**：40MB+ 视频需等待 **10-15 秒**（此次 41.6MB 约 13 秒）。不要只等 5 秒，需轮询检测"上传完成"文本或"更换视频"按钮出现。

---

## 3. 封面上传（关键步骤）

### 3.1 触发封面编辑器

```javascript
// 点击"封面设置"打开封面上传面板
// 选择器：text=封面设置
// 面板从右侧滑入，内含 cover-upload 组件
```

### 3.2 handleUpload 注入封面

```javascript
// Step 1: 从 CORS 服务器获取封面
const response = await fetch('http://127.0.0.1:18889/_bilibili_cover.jpg');
const blob = await response.blob();
const file = new File([blob], '_bilibili_cover.jpg', { type: 'image/jpeg' });

// Step 2: 找 cover-upload 组件（⚠️ 不能调 BccUpload.onFileSelected）
const el = document.querySelector('.bcc-upload.cover-upload');
let vm = el.__vue__;
let coverUpload = null;
for (let i = 0; i < 5; i++) {
  vm = vm.$parent;
  if (vm?.$options?.name === 'cover-upload') {
    coverUpload = vm;
    break;
  }
}
if (!coverUpload) throw new Error('cover-upload 组件未找到');

// Step 3: 调用 handleUpload
coverUpload.handleUpload([file]);
```

### 3.3 封面同步确认（4:3 → 16:9）

上传封面后，编辑器内出现双比例预览（首页推荐 4:3 / 个人空间 16:9），底部有同步复选框和提交按钮：

```
div.button.submit:has-text("完成")  →  browser_click  ✅
```

⚠️ **按钮文本是"完成"，不是"确认同步"**（v2.2 修正）。必须先点"完成"再关闭封面编辑器，否则发布时报"请先上传封面"。

### 3.4 关闭封面编辑器

同步确认后，编辑器自动关闭回到投稿主表单。若未自动关闭，可用：

```javascript
// 方式 A：点编辑器外的遮罩层关闭
document.querySelector('.cover-cropper-mask')?.click();

// 方式 B：点编辑器标题栏关闭按钮（需先查找具体类名）
document.querySelector('.cover-editor-close')?.click();
// 或 button:has-text("关闭")
```

### 3.5 Vue 组件层级

```
VideoCover
  └── CoverEditor
        └── cover-upload (name='cover-upload', 有 handleUpload/handleDragOver/handleDrop)
              └── BccUpload (有 onFileSelected，但绕过 cover-upload 校验链会报错)
```

⚠️ 严禁对封面上传使用 `BccUpload.onFileSelected` → `cover-upload` 包了文件 type 校验，直调内部组件触发 **"empty type or file"**。

### 3.6 封面图片生成（Pillow 参考代码）

```python
from PIL import Image, ImageDraw, ImageFont
img = Image.new('RGB', (1280, 720), '#1a1a2e')
draw = ImageDraw.Draw(img)
for i in range(720):
    c = int(26 - 26 * i / 720)
    draw.line([(0, i), (1280, i)], fill=(c, c, 46))
font = ImageFont.truetype('C:/Windows/Fonts/msyhbd.ttc', 48)
draw.text((640, 360), '动画标题 / 副标题', fill='white', font=font, anchor='mm')
img.save('_bilibili_cover.jpg')
```

---

## 4. 创作声明（Element Plus el-select 下拉）

发布前**必须**选择创作声明，否则 B站提示"请添加创作声明"。

### 4.1 选择"内容无需标注"

创作声明是 Element Plus `<el-select>` 组件，不是原生 `<select>`。输入框为 readonly，点击触发下拉。

**Playwright 操作（推荐——需先展开下拉再选项）：**

```javascript
// Step 1: 点击触发器打开下拉（text 选择器可能不稳定，备选 evaluate）
await page.locator('text=请选择符合您视频内容的创作声明').click();
await page.waitForTimeout(300); // 等待 el-select-dropdown 动画展开

// Step 2: 选择 "内容无需标注"
await page.locator('text=内容无需标注').click();
```

**浏览器 evaluate 操作（更稳健——直接定位到输入框父元素点击）：**

```javascript
// Step 1: 通过文本内容定位触发器父元素并点击
const allElements = document.querySelectorAll('*');
for (const e of allElements) {
  if (e.textContent && e.textContent.includes('请选择符合您视频内容的创作声明')) {
    e.parentElement?.click();
    break;
  }
}
await new Promise(r => setTimeout(r, 300));

// Step 2: 选项出现后点击
document.querySelector('.el-select-dropdown__item')?.click();
// 或精确文本匹配
Array.from(document.querySelectorAll('.el-select-dropdown__item'))
  .find(e => e.textContent.includes('内容无需标注'))?.click();
```

⚠️ **卡点记录（v2.2）**：`text=请选择符合您视频内容的创作声明` 直接 `browser_click` 偶发失效（元素被遮挡或未渲染）。**推荐 evaluate 策略**：先全量扫描文本内容定位触发器，再点父元素展开下拉，等待 300ms 后点选项。

---

## 5. 投稿编辑表单 — 选择器总表（坐标点位）

| 步骤 | 操作 | 精确选择器 | 备注 |
|------|------|-----------|------|
| **上传视频** | 注入 File | `.bcc-upload.upload.__vue__.onFileSelected([file])` | 先 fetch + new File |
| **一键填写** | 点击 | `text=一键填写` | AI 自动填标题/简介/标签 |
| **标题** | set value | `input[placeholder*="请输入稿件标题"]` → `.value = ...` + `dispatchEvent(new Event('input'))` | 手动填 |
| **简介** | set textContent | `.ql-editor` → `.textContent = ...` + `dispatchEvent(new Event('input'))` | contenteditable |
| **标签** | type + Enter | `input[placeholder*="按回车键Enter创建标签"]` → `browser_type` 文本 + `browser_press_key('Enter')` | 逐标签添加 |
| **分区** | click | `text=动画` 或 `text=知识` 的 `paragraph` | 按分类选 |
| **封面设置** | click 打开面板 | `text=封面设置` | 右侧滑入面板 |
| **上传封面** | 注入 File | 见 §3.2 `cover-upload.handleUpload` | ⚠️ 非 BccUpload |
| **封面同步** | click btn | `div.button.submit:has-text("完成")` | 4:3→16:9，⚠️ 文本为"完成" |
| **创作声明** | click 下拉选项 | `text=请选择符合您视频内容的创作声明` → click → `text=内容无需标注` → click | el-select |
| **存草稿** | click | `text=存草稿` | 测试用 |
| **立即投稿** | click | `text=立即投稿` | 最终发布 |
| **更换视频** | click | `text=更换视频` | 重选视频文件 |
| **添加分P** | click | `button:has-text("添加分P")` | 多 P 编辑 |

### 5.1 对话框/弹窗处理

```javascript
// 通用对话框隐藏（⚠️ 选择器来源于 v1.0 测试，本次测试未全覆盖验证）
document.querySelectorAll('.bcc-dialog, .bcc-dialog__wrap, .mask').forEach(d => {
  if (getComputedStyle(d).display !== 'none') d.style.display = 'none';
});
```

| 弹窗 | 内容 | 处理方式 |
|------|------|---------|
| 批量上传提示 | "批量上传将生成多条动态" | 隐藏或点"暂不设置" |
| 通知权限 | "想要显示通知" | 点"禁止" |
| 草稿保存 | "已存入草稿箱" | alert，自动消失 |
| beforeunload | 导航拦截 | `browser_handle_dialog({accept: true})` |
| 发布成功 | "稿件投递成功" | 确认后自动消失 |

---

## 6. 完整发布流程（坐标化 Step-by-Step）

```
[0] 导航投稿页 → [1] 上传视频 → wait 10-15s (轮询"上传完成")
→ [2] 标题 → [3] 简介 → [4] 标签 → [5] 点击封面设置
→ [6] handleUpload 封面 → [7] 点击"完成"同步封面 → [8] 编辑器自动关闭
→ [9] 创作声明(evaluate 策略) → [10] 立即投稿
→ [11] 点击"查看进度" → [12] 管理页确认"已通过"
```

### 6.1 执行代码

```javascript
// === [0] 导航 ===
await page.goto('https://member.bilibili.com/york/videoup?new');
await page.waitForTimeout(2000);

// === [1] 上传视频（§2.2）===
// ... vm.onFileSelected([file]) ...
// 轮询等待上传完成
for (let i = 0; i < 30; i++) {
  await page.waitForTimeout(500);
  const done = document.querySelector('text=上传完成') || document.querySelector('text=更换视频');
  if (done) break;
}

// === [2] 标题 ===
const tInput = document.querySelector('input[placeholder*="请输入稿件标题"]');
tInput.value = 'GSAP 程序化角色动画 — 能量核心 60s';
tInputEvent('input', { bubbles: true }));

// === [3] 简介 ===
const editor = document.querySelector('.ql-editor');
editor.textContent = '用 GSAP 程序化生成的 Canvas 像素角色动画展示...';
editor.dispatchEvent(new Event('input', { bubbles: true }));

// === [4] 标签 ===
// browser_type → Enter, 逐标签

// === [5] 封面设置 ===
await page.locator('text=封面设置').click();

// === [6] 上传封面（§3.2）===
// 执行 handleUpload 注入

// === [7] 确认同步（§3.3）===
await page.locator('div.button.submit:has-text("完成")').click();
// 编辑器自动关闭，等待 1s 确保回到主表单
await page.waitForTimeout(1000);

// === [9] 创作声明（§4 evaluate 策略）===
await page.evaluate(() => {
  const all = document.querySelectorAll('*');
  for (const e of all) {
    if (e.textContent?.includes('请选择符合您视频内容的创作声明')) {
      e.parentElement?.click();
      break;
    }
  }
});
await page.waitForTimeout(300);
await page.locator('text=内容无需标注').click();

// === [10] 发布 ===
await page.locator('text=立即投稿').click();

// === [11] 点击查看进度 ===
await page.waitForTimeout(3000); // 等弹窗出现
await page.locator('text=查看进度').click();

// === [12] 管理页确认已通过 ===
await page.waitForTimeout(2000);
const passed = document.querySelector('text=已通过');
console.log('发布完全成功:', !!passed);
```

### 6.2 发布后确认信号（完整验证链路 v2.2）

点击"立即投稿"后依次出现：

```
1. loading 状态："提交中..."
2. 弹窗："稿件投递成功" ✅
   ├── button "查看进度"
   └── button "再投一个"
3. 点击"查看进度" → 跳转管理页 https://member.bilibili.com/platform/upload-manager/article
4. 管理页筛选"已通过"标签 → 视频列表显示该视频 ✅
5. 视频行显示 BV 号、投稿时间、状态"已通过" → 发布完全成功 ✅
```

这 5 步信号全部出现才算发布成功。弹窗出现只是"投递成功"，还需确认管理页"已通过"才算完整上架。

---

## 7. 内容管理操作（坐标点位）

### 7.1 查看已发布视频

```
URL: https://member.bilibili.com/platform/upload-manager/article
→ 自动加载全部稿件列表
→ 已通过标签显示已发布视频
```

### 7.2 删除草稿

```
URL: https://member.bilibili.com/platform/upload-manager/article?group=draft

[hover] 草稿标题 → .bcc-icon-icon_tasklist_delete_ 从 visibility:hidden → visible
[click]  .bcc-icon-icon_tasklist_delete_  first()
[wait]   弹窗 "确定要删除这个草稿吗？"
[click]  button:has-text("确定")
[verify] alert "删除草稿成功" + 草稿计数 -1
```

### 7.3 更多操作按钮（⚠️ 已知不可靠）

B站管理页视频卡片右侧 `a.more-btn` 内含操作菜单（编辑/数据/下架）：

| 操作 | 选择器 | 状态 |
|------|--------|------|
| more 按钮 | `a.more-btn`（或内部 `i.bcc-icon-icon_list_more_x`） | ❌ 点击不触发 Vue 事件 |
| 编辑 | `text=编辑`（行内可见） | ✅ 可直接点击 |
| 数据 | `text=数据` 或 `a[href*="/data/"]` | ✅ 直接导航 |
| 下架/删除 | 需 more-btn 弹出菜单 | ❌ 无法触发 |

💡 **替代方案**：编辑视频可点击行内可见的 `text=编辑` 按钮，直接导航到编辑页。

### 7.4 已发布视频管理页去重

已发布视频列表的筛选 tab：

```
全部稿件  →  text=全部稿件 [N]
草稿      →  text=草稿 [N]
进行中    →  text=进行中 [N]
已通过    →  text=已通过 [N]
未通过    →  text=未通过 [N]
```

排序下拉：

```
投稿时间排序  →  textbox "请选择内容"（el-select）
播放数排序
收藏数排序
...
```

---

## 10. 故障排查与常见卡点（v2.2 新增）

| 现象 | 原因 | 解决方案 |
|------|------|----------|
| `browser_click('text=内容无需标注')` 超时/不可见 | el-select dropdown 选项未渲染或被遮挡 | 先 evaluate 点击触发器父元素展开，wait 300ms 再 click 选项 |
| `text=请选择符合您视频内容的创作声明` 点击无反应 | 文本节点非交互元素，或被遮挡 | 用 evaluate 全量扫描文本内容，点击 `parentElement` |
| 视频上传后长时间"上传中..." | 40MB+ 视频需 10-15s，5s 等待不够 | 轮询检测"上传完成"文本或"更换视频"按钮，最长等 30s |
| 封面同步按钮找不到 | 按钮文本是"完成"非"确认同步" | 用 `div.button.submit:has-text("完成")` 选择器 |
| 点击"完成"后编辑器未关闭 | 异步关闭需等待 | 点击后 `waitForTimeout(1000)` 确保回到主表单 |
| 发布后仅见"稿件投递成功"弹窗 | 仅是投递成功，未确认审核通过 | 必须点击"查看进度"→管理页确认"已通过"标签 |
| CORS 服务器端口占用 | 上次运行未清理进程 | 运行前先执行清理脚本，或换端口 |
| `browser_file_upload` 报 "Not allowed" | file input 被 `display:none` 隐藏 | 必须用 Vue 组件 `onFileSelected` / `handleUpload` 注入 |
| 管理页 more-btn 点击无反应 | Vue 事件绑定在微应用沙箱中失效 | 直接点击行内可见的"编辑"/"数据"链接 |

---

## 8. 技术要点

### 8.1 Chrome 安全策略三连坑

1. `DOM.setInputFiles` → "Not allowed"（`display:none` 的 file input 被 CDP 安全策略拦截）
2. `DragEvent('drop')` → `dataTransfer.files` 为空（合成事件不携带文件数据）
3. `playwright browser_file_upload` → 对 `display:none` 的 input 报"Not allowed"（Playwright MCP 的安全检查，非 Chrome 原生策略）

### 8.2 Vue 2 组件注入原理

- B站 york/videoup 使用 Vue 2 开发，组件实例挂在 DOM 的 `__vue__` 属性上
- `onFileSelected` 接受普通 `File[]` 数组，不经过 input 元素
- `cover-upload.handleUpload` 额外做了 `file.type` 检查（必须为 image/jpeg 或 image/png）
- `el-select` 是 Element Plus 组件，点击触发器弹出 `el-select-dropdown`

### 8.3 已知局限

| 项目 | 状态 | 说明 |
|------|------|------|
| 管理页 more-btn 菜单 | ❌ 不可点击 | Vue 事件绑定不触发 |
| 已发布视频删除 | ❌ 无 API | 所有已知 API 端点返回 404 |
| El-select 下拉选项 | ⚠️ 不稳定 | 需等待 `el-select-dropdown` 完全展开 |
| beforeunload 拦截 | ⚠️ 需处理 | 编辑页离开时触发 |

---

## 9. 清理

```bash
# 停止 CORS 服务器
# Linux/macOS
kill $(ps aux | grep "1888[89]" | grep -v grep | awk '{print $2}')

# Windows (PowerShell)
Get-Process | Where-Object { $_.MainWindowTitle -like "*18888*" -or $_.MainWindowTitle -like "*18889*" } | Stop-Process -Force
# 或
netstat -ano | findstr "18888 18889" | ForEach-Object { $pid = $_.Split()[-1]; taskkill /F /PID $pid }

# 删除临时文件
rm -f _bilibili_cover.jpg _bilibili_cover_b64.txt
```

### 9.1 自动化清理模板（推荐集成到脚本末尾）

```javascript
// 在 Playwright 脚本末尾加入
async function cleanup() {
  // 1. 关闭浏览器上下文
  await context?.close();
  
  // 2. 杀掉 CORS 服务器（跨平台）
  const { execSync } = require('child_process');
  try {
    // Windows
    execSync('taskkill /F /FI "WINDOWTITLE eq *18888*" /FI "WINDOWTITLE eq *18889*"', { stdio: 'ignore' });
  } catch {
    try {
      // Linux/macOS
      execSync('pkill -f "1888[89]"', { stdio: 'ignore' });
    } catch {}
  }
  
  // 3. 清理临时文件
  const fs = require('fs');
  ['_bilibili_cover.jpg', '_bilibili_cover_b64.txt'].forEach(f => {
    if (fs.existsSync(f)) fs.unlinkSync(f);
  });
}
```

---

## 版本历史

- v2.2 (2026-06-30)：新增**封面同步确认按钮选择器修正**（"完成"而非"确认同步"）；新增**创作声明下拉触发器定位策略**（文本定位失效需用 evaluate 点击父元素）；新增**文件上传超时等待策略**（视频 40MB+ 需 10-15s）；新增**发布后验证完整链路**（投递成功弹窗 → 点击"查看进度" → 管理页"已通过"标签）；新增**CORS 服务器自动清理模板**
- v2.1 (2026-06-27)：坐标化全部选择器点位；新增 el-select 下拉机制；新增内容管理操作坐标（§7）；新增发布确认信号（§6.2）；新增 Chrome 三连坑（§8.1）；新增已知局限表（§8.3）
- v2.0 (2026-06-26)：新增封面上传（cover-upload.handleUpload）、创作声明选择、封面同步确认；更新选择器总表；端到端全链路测试通过 ✅
- v1.0 (2026-06-26)：初版，基础上传 + 编辑 + 存草稿流程已验证
