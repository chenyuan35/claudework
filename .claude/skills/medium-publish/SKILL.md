---
name: medium-publish
description: "自动创作并发布一篇英文 Medium 文章到 @chenyuan19920509"
---

# /medium-publish SOP

全自动 Medium 英文文章发布 SOP。**启动后按步骤依次执行，不询问用户。** 每步完成后自动进入下一步。

## 核心约束

- **全英文**
- **绝对禁止草稿**：只直接发布。开始前检查并删除所有草稿。
- **不重复发布**：发布前检查 Published tab 确认同标题未出现过。
- **不自毁**：登录失效/发布按钮不可用/浏览器断连之外，不停下来问用户。

## P0：文章内容和标题（每次执行前先确定）

### 当前活跃系列
Production AI: Patterns That Actually Work — 下一篇文章 #16

### 标题格式
结果 + 转折：I Thought X Was Y. Here's What Actually Broke.
个人经验前置：What I Learned After...
具体 + 数字：I Built X in 30 Minutes. Here's What Broke.

### 文章结构与语气规则

**结构（指南，不是死框）**：

| 段落 | H2 标题（示例） | 推荐词数 |
|------|----------------|---------|
| Hook（无 H2） | — | 100-150 |
| Problem | The Setup That Bit Me | 200-400 |
| Data/Examples | What I Actually Built to Fix It | 400-700 |
| Solution | The Pattern I Reuse Now | 200-400 |
| Closing | What I Still Haven't Figured Out | 150-300 |
| **总计** | | **≥1,500** |

需要 3 个或 5 个 H2 就写 3 个或 5 个，不卡框架。

**语气（每条都不可违反）**：
- 第一人称：I, you, don't, can't, I've
- 每个 H2 段下至少一句真实经历
- 每篇至少一个开放问题
- 禁止词：delve / leverage / landscape / moreover / furthermore / testament / game-changer / seamless / elevate / empower / unlock / dive into / "in today's rapidly evolving" / "let's break it down" / "in conclusion" / "it's worth noting" / "this raises the question"

**段落扫读规则**：长段落（3-5 句）之间插短段落（1-2 句）。每篇至少一个 `<blockquote>`。第一段开门见山。

---

## §1 执行前：准备正文

### 1.1 写正文

在 `C:\Users\59314\claudework\medium_body.html` 写入格式化 HTML：
- 支持标签：`<h2> <p> <strong> <em> <code> <pre> <a> <ul>/<ol> <blockquote>`
- 不能包含：`<script> <style> <img> <iframe>`
- 目标词数：**1,500-2,500 词**

### 1.1.5 本地预核验门（不可跳过）

```bash
cd "C:/Users/59314/claudework" && python -c "
import re
html=open('medium_body.html',encoding='utf-8').read()
text=re.sub(r'<[^>]+>',' ',html).replace('&lt;','<').replace('&gt;','>').replace('&amp;','&')
words=re.findall(r\"[A-Za-z0-9']+\",text)
wc=len(words); h2=len(re.findall(r'<h2',html)); pre=len(re.findall(r'<pre',html)); bq=len(re.findall(r'<blockquote',html))
banned=['delve','leverage','landscape','moreover','furthermore','testament','game-changer','seamless','elevate','empower','unlock','dive into','in today','let us break','in conclusion','it is worth','this raises']
low=text.lower(); hit=[b for b in banned if b in low]
ok = wc>=1500 and pre>=1 and not hit
print(f'words={wc} H2={h2} codeblocks={pre} blockquotes={bq} banned_words={hit}')
print('PREVALIDATION', 'PASS' if ok else 'FAIL')
"
```

**判定**：词数<1,500 / 代码块<1 / 有禁词 → 直接改 `medium_body.html` 补足，重跑直到 PASS。不允许带着 FAIL 进浏览器。

### 1.2 base64 编码 + 启动 HTTP 服务器

```bash
# 先清理旧进程
taskkill //F //IM python //FI "CPUVERSION ne 0" 2>/dev/null || true

# 编码
node -e "const fs=require('fs');const c=fs.readFileSync('medium_body.html','utf-8');fs.writeFileSync('medium_body.b64',Buffer.from(c,'utf-8').toString('base64'));console.log('done')"

# 启动 HTTP 服务器（端口 8748），验证服务器就绪后再继续
python -c "
import http.server, socketserver, threading, time
PORT = 8748
class H(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/body.b64':
            self.send_response(200); self.send_header('Content-Type','text/plain'); self.end_headers()
            with open('medium_body.b64','rb') as f: self.wfile.write(f.read())
        else: self.send_error(444)
    def log_message(self,*a): pass
httpd = socketserver.TCPServer(('127.0.0.1',PORT),H)
threading.Thread(target=httpd.serve_forever,daemon=True).start()
time.sleep(600)
" &
sleep 2 && curl -s http://127.0.0.1:8748/body.b64 > /dev/null && echo "Server ready" || echo "Server FAIL"
```

---

## §2 执行流（按顺序执行，不可跳过）

### Step 0: 登录检查
1. `browser_navigate("https://medium.com/new-story")`
2. `browser_snapshot` → 确认页面已加载、非登录页
3. 若跳转到 `/sign-in` 或 `accounts.google.com` → 熔断

### Step 0.5: 24h 发布配额检查
1. 导航到 `https://medium.com/me/stories`
2. 点击 Published tab：`page.getByRole('tab', { name: /Published/ }).click()`
3. 等 2s → `page.evaluate` 获取每一行的发布时间文本（如 "Published 1d ago"）
4. **判定**：
   - 过去 24h ≥ 2 篇 → 熔断，报告"Medium 每日上限 2 篇"并停止
   - 0-1 篇 → 继续
5. 熔断后不写正文、不启动服务器、不创建草稿。

### Step 1: 删除草稿 + 标题去重
1. `browser_navigate("https://medium.com/me/stories")`
2. 检查 Drafts tab 数字：若为 0 → 跳过删草稿
3. 删每个草稿（`browser_run_code_unsafe`）：
   - `page.getByRole('button', { name: 'Toggle actions menu' }).first().click()`
   - 等 800ms → `page.getByRole('button', { name: 'Delete story' }).click()`
   - 等 1.5s → `page.locator('[role="dialog"]').getByRole('button', { name: 'Delete' }).click()`
   - 等 2s → 检查 Drafts 数字，重复直到 0
4. 切换到 Published tab → 获取所有 h2 标题文本
5. 若本篇标题已存在 → 选下一篇，停止
6. 回到 `https://medium.com/new-story`

### Step 2: 写标题
```js
async (page) => {
  const title = '<本篇标题>';
  const titleEl = page.locator('h3.graf--title');
  await titleEl.click();
  await page.waitForTimeout(500);
  await titleEl.evaluate(el => el.querySelectorAll('span.defaultValue').forEach(s => s.remove()));
  await page.waitForTimeout(200);
  for (const char of title) {
    await page.keyboard.type(char, { delay: 40 + Math.random() * 40 });
  }
  return { titleWritten: true };
}
```

如果 `h3.graf--title` 3s 内不存在 → 熔断。

### Step 3: 粘贴正文
```js
async (page) => {
  const response = await page.request.get('http://127.0.0.1:8748/body.b64');
  const b64 = await response.text();
  const html = await page.evaluate((b) => {
    const chars = atob(b);
    const nums = new Array(chars.length);
    for (let i = 0; i < chars.length; i++) nums[i] = chars.charCodeAt(i);
    return new TextDecoder().decode(new Uint8Array(nums));
  }, b64);
  await page.evaluate(async (htmlContent) => {
    const blob = new Blob([htmlContent], { type: 'text/html' });
    await navigator.clipboard.write([new ClipboardItem({ 'text/html': blob })]);
  }, html);
  await page.waitForTimeout(800);
  const bodyEl = page.locator('p.graf--p').first();
  await bodyEl.click();
  await page.waitForTimeout(600);
  await bodyEl.evaluate(el => el.querySelectorAll('span.defaultValue').forEach(s => s.remove()));
  await page.waitForTimeout(400);
  await page.keyboard.press('Control+V');
  await page.waitForTimeout(5000);
  return { bodyPasted: true };
}
```

HTTP 服务器不可达 → 重启服务器（§1.2）后重试。

### Step 3.5: 字数核验
```js
async (page) => {
  const text = await page.evaluate(() => document.querySelector('.postArticle-content').innerText);
  const wordCount = text.split(/\s+/).filter(Boolean).length;
  return { wordCount, passed: wordCount >= 1200 };
}
```

**判定**：
- wordCount ≥ 1,200 → 进入 Step 4
- wordCount < 1,200 → 删当前草稿 → 重写 medium_body.html → 重编码 → 重启 HTTP 服务器 → 回到 new-story 全新开始 → 循环直到通过

### Step 4: 加封面图（弹层前）

> 封面图必须在打开 Publish 弹层之前添加到编辑器。

**配图方式：从文章取段落直接生图，不走抽象模板。**

1. 从 `medium_body.html` 选一段有视觉感的段落（通常第一段），以此作为 prompt
2. 调 Agnes API 生图：
```bash
python -c "
from openai import OpenAI
paragraph = '<段落原文>'
client = OpenAI(api_key='sk-37fc8R90O1p5YQy7py4vQpmbWywfsnqg3qLJxxJg2cO8y3Ui', base_url='https://apihub.agnes-ai.com/v1')
resp = client.images.generate(model='agnes-image-2.1-flash', prompt=paragraph, n=1, size='1792x1024')
import requests; r = requests.get(resp.data[0].url)
with open('medium_cover.jpg','wb') as f: f.write(r.content)
print('Cover saved')
"
```
3. 启动 HTTP 服务器（端口 8747）serve `medium_cover.jpg`
4. 浏览器内插入图片（**不用 clipboard**）：
   - 点击标题区域（`h3`）→ `ArrowUp` → `Enter` → `ArrowUp` 在标题上方创建空行
   - 点击空行的 "+" 按钮：`page.getByTestId('editorAddButton').click()`
   - 菜单中点击 "Add an image"（exact: true）→ 文件选择器弹出
   - `browser_file_upload` → 选择 `medium_cover.jpg`
   - 等 3s
5. 配图失败 → 记录，不影响发布

### Step 5: 点 Publish（弹层）
```js
async (page) => {
  await page.getByRole('button', { name: 'Publish' }).click();
  await page.waitForTimeout(3000);
  const combobox = await page.evaluate(() => !!document.querySelector('input[role="combobox"]'));
  return { publishDialogOpened: combobox, url: page.url() };
}
```

combobox 不存在 → 跳过 Topics，直接执行 Step 7 force publish。

### Step 6: 加 Topics（固定 5 个）
```js
async (page) => {
  const topics = ['Software Engineering', 'Programming', 'Technology', 'Artificial Intelligence', 'Machine Learning'];
  for (const topic of topics) {
    const combo = page.locator('input[role="combobox"]');
    await combo.click(); await page.waitForTimeout(400);
    await combo.fill(topic); await page.waitForTimeout(1500);
    await page.keyboard.press('ArrowDown'); await page.waitForTimeout(300);
    await page.keyboard.press('Enter'); await page.waitForTimeout(800);
  }
  return { topicsAdded: topics.length };
}
```

### Step 7: 最终发布
```js
async (page) => {
  await page.evaluate(() => { document.querySelectorAll('div[tabindex="-1"]').forEach(el => { el.style.display = 'none'; }); });
  await page.waitForTimeout(500);
  await page.getByRole('button', { name: 'Publish' }).click({ force: true });
  await page.waitForTimeout(8000);
  return { url: page.url() };
}
```

### Step 8: 核验
```js
async (page) => {
  await page.goto('https://medium.com/me/stories?tab=posts-published', { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(3000);
  const firstTitle = await page.evaluate(() => {
    const rows = document.querySelectorAll('table tbody tr');
    if (!rows.length) return '';
    const h2 = rows[0].querySelector('h2');
    return h2 ? h2.textContent.trim() : '';
  });
  return { firstTitle, verified: firstTitle.length > 0 };
}
```

**发布成功判定**：Stories Published 列表第一条标题匹配本篇标题。不匹配 → 报告但不熔断（可能排序延迟）。

---

## §3 Topics 基准集

固定 5 个：
1. Software Engineering
2. Programming
3. Technology
4. Artificial Intelligence（可换为 Large Language Models / AI Assistants）
5. Machine Learning（可换为 Open Source / Web Development）

---

## §4 错误处理

| 条件 | 动作 |
|------|------|
| 页面跳转到登录页 | 熔断，报告需要手动重新登录 Google OAuth |
| 本地预核验 FAIL | 改 medium_body.html 重跑直到 PASS |
| h3.graf--title 不存在 | 等 3s 重试一次，仍不存在 → 熔断 |
| HTTP 服务器 8748 不可达 | 重启服务器后重试 |
| Publish 按钮被遮挡 | evaluate 删除 div[tabindex="-1"] → click({ force: true }) |
| Topics combobox 不工作 | 跳过 Topics 直接 Publish |
| 配图失败 | 记录报错，不影响发布 |
| 字数不足 < 1,200 | 删草稿 → 改写 → 重编码 → 全新开始 |
| Rate limit | 关闭弹层 → 删草稿 → 报告配额满 |
| 连续两次同类工具调用失败 | 熔断 |

---

## §5 选择器表

| 元素 | 选择器 |
|------|--------|
| 编辑器标题 | `h3.graf--title` |
| 编辑器正文 | `p.graf--p` |
| 标题 placeholder | `span.defaultValue` |
| Publish 按钮 | `button:has-text("Publish")` |
| Topics combobox | `input[role="combobox"]` |
| Drafts tab | `getByRole('tab', { name: /Drafts/ })` |
| Published tab | `getByRole('tab', { name: /Published/ })` |
| Stories 行菜单 | `getByRole('button', { name: 'Toggle actions menu' })` |
| 删除确认 | `[role="dialog"]` 内文本为 "Delete" 的 button |
| 编辑器 + 按钮 | `getByTestId('editorAddButton')` |
| Rate limit alert | `[role="alert"]` 含 "maximum of two stories" |

---

## §6 发布后

1. 删除临时文件：`rm -f medium_body.html medium_body.b64 medium_cover.*`
2. 更新 §P0 "当前活跃系列" 进度号
3. 记录本次封面图段落来源到 `medium_last_cover.md`（供下篇避免重复场景）
4. 若执行中有任何堵塞 → 修复对应步骤的 SOP

## 复盘

> 复盘按 CLAUDE.md 技能修复标准流程执行
