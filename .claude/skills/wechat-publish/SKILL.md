---
name: wechat-publish
description: 公众号谋生与人性全自动生产管线 v7.0 — 状态机驱动，无人值守
vars:
  siliconflow_api_key: sk-fhyebysadetapteypeklskautvwwpcizruxnqhbwmrqbacfy
---

# 公众号「谋生与人性」v7.0 — 状态机发布引擎

**唯一入口**：`run_wechat_publish.py`（禁止绕过脚本手工操作）

**架构**：状态机引擎驱动 22 个状态，AUTO 步骤脚本自动执行，BROWSER 步骤由 Claude 调用 Playwright 操作后标记完成。

---

## 执行流程

### 第 0 步：启动会话

```bash
cd C:/Users/59314/claudework
python run_wechat_publish.py --init "选题关键词"
# 重置状态机，开始新会话
```

### 第 1 步：状态机循环

```
while true; do
  python run_wechat_publish.py --status
  # 读取 current_state
  # 如果是 AUTO → python run_wechat_publish.py --step
  # 如果是 BROWSER → 执行下方对应 Playwright 代码 → --complete
  # 如果是 terminal(done) → 退出循环  
  # 如果是 terminal(error) → 判断错误类型，决定重试或报告
done
```

### 第 2 步：AUTO 步骤（脚本自动完成）

以下步骤由 `run_wechat_publish.py --step` 一键执行，无需干预：

| 状态 | 执行内容 |
|------|---------|
| init | 检查目录和依赖 |
| topic | 选题（Claude 写文后调用 --step 确认） |
| write | 验证 article.txt 存在且 ≥2000 汉字 |
| qa_para | check_wechat_para.py 段长闸 |
| qa_ai | ai_score.py ≤45 分 |
| image_gen | 生图 cover.jpg + inline1-3 |
| cors | 启动 8768 HTTP CORS 服务 |
| bake | bake_wechat_html.py 烘焙 |
| validate | validate_wechat_html.py 7 项门禁 |
| review | 复盘 |
| skill_fix | 技能修复 |
| cleanup | 清理临时文件 + 备份轮换 |

### 第 3 步：BROWSER 步骤（Playwright 驱动）

每步 Claude 执行 Playwright 代码后调用 `python run_wechat_publish.py --complete` 推进状态机。

---

## BROWSER 步骤实现

### dedup — 去重

```javascript
// 导航到已发表记录页，提取标题列表
browser_navigate → https://mp.weixin.qq.com/cgi-bin/appmsgpublish?sub=list&begin=0&count=20&token={token}&lang=zh_CN
// 从 snapshot 提取所有链接标题 → 与当前标题比对
// 重复则熔断，不重复则 → python run_wechat_publish.py --complete
```

### editor_open — 打开编辑器

token 已在 URL 中。导航到新文章页：
```
browser_navigate → https://mp.weixin.qq.com/cgi-bin/appmsg?t=media/appmsg_edit_v2&action=edit&isNew=1&type=77&createType=0&token={token}&lang=zh_CN
```

### title_author — 填标题和作者

**标题**：`PM[0]` + `execCommand('insertText')`（禁止 [contenteditable] / fill_form）
**作者**：`input[placeholder="请输入作者"]` + native value setter → "谋生与人性"

### image_upload — 上传 3 张正文图片

工具栏 `li#js_editor_insertimage` → DataTransfer 一次 3 张 inline1-3 → 等 8s 取 CDN URL → 存 state.cdn_urls

### insert — 插入正文

```javascript
fetch('http://127.0.0.1:8768/article_final.html')
  .then(r => r.text())
  .then(html => {
    bodyPM = document.querySelectorAll('.ProseMirror')[1];
    bodyPM.focus(); execCommand('delete');
    // 逐块 insertHTML
  })
```

### visual_check — 截图验收

`preview_screenshot` 截开头/中间/结尾 → 检查 Markdown 残留、段落堆积、图片位置
（由当前模型自动判断，不需要用户查看截图）

### cover — 封面上传（黄金路径，禁止发明新路径）

唯一序列：`点封面+ → 从图片库选择 → 选中已上传的 cover.jpg → 下一步 → 确认 → 验证预览`

```javascript
// Step 1: 点封面"+"
await page.locator('.js_cover_btn_area').first().click();
await page.waitForTimeout(1500);

// Step 2: 点"从图片库选择"
page.evaluate(() => {
  const link = [...document.querySelectorAll('a')].find(a => a.innerText?.includes('从图片库选择'));
  if (link) link.click();
});
await page.waitForTimeout(3000);

// Step 3: 选中已上传的 cover.jpg（Playwright 真实 click）
await page.locator('.weui-desktop-img-picker__item').filter({ hasText: 'cover.jpg' }).first().click();
await page.waitForTimeout(1000);

// Step 4: 下一步（进入裁剪）
page.evaluate(() => {
  const d = [...document.querySelectorAll('.weui-desktop-dialog')]
    .find(x => x.querySelector('.weui-desktop-dialog__title')?.innerText === '选择图片');
  if (!d) return;
  const n = [...d.querySelectorAll('button')].find(b => b.innerText.trim() === '下一步' && !b.disabled);
  if (n) n.click();
});
await page.waitForTimeout(3000);

// Step 5: 确认（裁剪完成）
page.evaluate(() => {
  const d = [...document.querySelectorAll('.weui-desktop-dialog')]
    .find(x => (x.querySelector('.weui-desktop-dialog__title')?.innerText || '').includes('编辑封面'));
  if (!d) return;
  const c = [...d.querySelectorAll('button')].find(b => b.innerText.trim() === '确认' && !b.disabled);
  if (c) c.click();
});
await page.waitForTimeout(3000);

// 验证：封面预览存在
page.evaluate(() => /mmbiz/.test(getComputedStyle(document.querySelector('.js_cover_preview_new')).backgroundImage));
```

失败仅刷新页面重试同一路径，禁止新增分支或跳过。

### final_verify — 终极验证

```javascript
// 检查：标题、作者、3 CDN 图、2400-3200 汉字、封面存在、在看、leafAvg≤22、over40≤5
// 全部 pass 才允许保存
```

### save — 保存草稿

Escape×3 → `button:has-text("保存为草稿")` click → 验证 URL 含 appmsgid

---

## 回归测试（每次发表前必跑）

```javascript
// 读取真实 DOM，5 项硬性检查
page.evaluate(() => {
  const bp = document.querySelectorAll('.ProseMirror')[1];
  const sections = bp.children;
  const t = bp.innerText;
  let dotCount = 0, imgIdx = [];
  for (let i = 0; i < sections.length; i++) {
    const txt = sections[i].innerText.trim();
    if (/^\.+$/.test(txt)) dotCount++;
    if (sections[i].querySelector('img')) imgIdx.push(i);
  }
  const total = sections.length;
  const imgPcts = imgIdx.map(idx => Math.round((idx / total) * 100));
  
  return {
    pass: (
      /mmbiz/.test(getComputedStyle(document.querySelector('.js_cover_preview_new')).backgroundImage) &&  // 封面
      dotCount === 0 &&                                                                                 // 无点号段
      imgIdx.length === 3 &&                                                                            // 3 张图
      imgPcts.every((p, i) => Math.abs(p - [25, 55, 82][i]) <= 5) &&                                   // 位置误差 ≤5%
      (t.match(/[一二三四五六七八九十]+、/g) || []).length >= 4 && (t.match(/[一二三四五六七八九十]+、/g) || []).length <= 7  // 小标题
    )
  };
});
// pass=false → 回滚到上一个恢复点 → 重跑黄金路径
```

## 终局错误（需要通知用户）

1. 登录失效 / 扫码页面 / 验证码
2. Playwright 连续两次真实调用失败
3. 平台接口连续两次 5xx
4. 文件读写异常
5. 质量门自动修复两次仍不通过

其他一切错误由状态机自动重试或回滚恢复点。
