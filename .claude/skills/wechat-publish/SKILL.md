---
name: wechat-publish
description: 公众号谋生与人性全自动生产管线 v8.0 — 状态机驱动，无人值守
vars:
  siliconflow_api_key: sk-fhyebysadetapteypeklskautvwwpcizruxnqhbwmrqbacfy
---

# 公众号「谋生与人性」v8.0 — 状态机发布引擎

**唯一入口**：`run_wechat_publish.py`（禁止绕过脚本手工操作）
**架构**：状态机引擎驱动 22 个状态。AUTO 步骤脚本自动执行，BROWSER 步骤由 Claude 调用 Playwright 操作后标记完成。
**排版核心**：`bake_wechat_html.py` — `split_blocks()` 句子级拆分 + `--auto-position` 自动算图 + `<p id="pN">` 防 ProseMirror 合并

---

## 执行流程

### 第 0 步：启动会话

```bash
cd C:/Users/59314/claudework
python run_wechat_publish.py --init "选题关键词"
# 重置状态机，开始新会话
```

### 第 1 步：状态机循环

```bash
while true; do
  python run_wechat_publish.py --status   # 读取 current_state
  # AUTO  → python run_wechat_publish.py --step
  # BROWSER → 执行下方对应 Playwright 代码 → python run_wechat_publish.py --complete
  # terminal(done) → 退出循环
  # terminal(error) → 判断错误类型：终局错误则通知用户，其余自动重试或回滚
done
```

---

## 完整状态定义（22 个状态）

| 序号 | 状态名 | 类型 | 描述 | 最大重试 | 恢复点 |
|---|---|---|---|---|---|
| 0 | init | auto | 检查目录/依赖 | 1 | ✅ |
| 1 | topic | auto | 选题: 确定文章主题和标题 | 2 | ✅ |
| 2 | write | auto | 写作: 生成文章并保存 .txt | 2 | ✅ |
| 3 | qa_para | auto | 段长闸: check_wechat_para.py | 2 | |
| 4 | qa_ai | auto | AI味闸: ai_score.py ≤45 | 2 | |
| 5 | image_gen | auto | 生图: cover.jpg + inline1-3 | 2 | ✅ |
| 6 | dedup | browser | 去重: Playwright提取已发表标题 | 2 | ✅ |
| 7 | cors | auto | CORS服务: 启动HTTP服务器 :8768 | 2 | ✅ |
| 8 | editor_open | browser | 编辑器: 打开新文章编辑页 | 2 | ✅ |
| 9 | title_author | browser | 标题作者: 填入编辑器 | 2 | |
| 10 | image_upload | browser | 插图上传: 3张一次传完获取CDN | 2 | ✅ |
| 11 | bake | auto | 烘焙: bake_wechat_html.py | 2 | |
| 12 | validate | auto | 门禁: validate_wechat_html.py | 2 | ✅ |
| 13 | insert | browser | 插入正文: fetch→清空→insertHTML | 2 | ✅ |
| 14 | visual_check | browser | 视觉检查: 截图验证排版 | 2 | ✅ |
| 15 | cover | browser | 封面: 上传并设置封面图 | 2 | ✅ |
| 16 | final_verify | browser | 终极验证: DOM+CDN+表情+封面 | 2 | ✅ |
| 17 | save | browser | 保存草稿 | 2 | ✅ |
| 18 | review | auto | 复盘: 更新选题账本 | 1 | |
| 19 | skill_fix | auto | 技能修复: 固化本次经验 | 1 | |
| 20 | cleanup | auto | 清理: 临时文件+备份轮换 | 1 | |
| 21 | done | terminal | 完成 | 0 | ✅ |

---

## BROWSER 步骤实现

### dedup — 去重

导航到已发表记录页，提取标题列表比对。

```javascript
// 导航到发布列表页（token 从当前页面获取）
browser_navigate → https://mp.weixin.qq.com/cgi-bin/appmsgpublish?sub=list&begin=0&count=20&token={token}&lang=zh_CN
// 从 snapshot 提取所有已发表文章的标题 → 与当前标题比对
// 重复则熔断（通知用户主题重复），不重复则 → python run_wechat_publish.py --complete
```

### editor_open — 打开编辑器

```javascript
browser_navigate → https://mp.weixin.qq.com/cgi-bin/appmsg?t=media/appmsg_edit_v2&action=edit&isNew=1&type=77&createType=0&token={token}&lang=zh_CN
// 等待 editor 加载（.ProseMirror 出现）
```

### title_author — 填标题和作者

```javascript
// 标题
const pm0 = document.querySelectorAll('.ProseMirror')[0];
pm0.focus();
document.execCommand('selectAll');
document.execCommand('insertText', false, '文章标题');

// 作者
await page.locator('input[placeholder="请输入作者"]').fill('谋生与人性');
```

### image_upload — 上传 3 张正文图片

```javascript
// Step 1: 点击工具栏插入图片按钮
document.querySelector('li#js_editor_insertimage')?.click();
await new Promise(r => setTimeout(r, 1000));

// Step 2: 找到文件 input，用 setInputFiles 一次上传 3 张（Playwright 原生方式）
// 注意：此处需要在 Playwright 的 browser_run_code_unsafe 中执行
const fileInput = page.locator('input[type="file"]');
await fileInput.setInputFiles([
  'C:\\Users\\59314\\claudework\\inline1.jpg',
  'C:\\Users\\59314\\claudework\\inline2.jpg', 
  'C:\\Users\\59314\\claudework\\inline3.jpg'
]);

// Step 3: 等待上传完成（8-10s，取决于文件大小和网速）
await page.waitForTimeout(10000);

// Step 4: 从 ProseMirror 正文中提取 CDN URL
const cdnUrls = await page.evaluate(() => {
  const bodyPM = document.querySelectorAll('.ProseMirror')[1];
  if (!bodyPM) return [];
  return Array.from(bodyPM.querySelectorAll('img'))
    .map(img => img.src)
    .filter(src => src && src.startsWith('http'));
});

// Step 5: 写入 state → Claude 执行
// 取 cdnUrls[0..2] 写入 session_state.json 的 cdn_urls 字段
// 然后 python run_wechat_publish.py --complete

### insert — 插入正文

```javascript
const resp = await fetch('http://127.0.0.1:8768/article_final.html');
const html = await resp.text();

const bodyPM = document.querySelectorAll('.ProseMirror')[1];
bodyPM.focus();
document.execCommand('selectAll');
document.execCommand('delete');
// 一次性 insertHTML（id="pN" 阻止 ProseMirror 合并）
document.execCommand('insertHTML', false, html);

// 验证
const withSrc = Array.from(bodyPM.querySelectorAll('img')).filter(i => i.src).length;
// withSrc !== 3 → 重试
```

### visual_check — 视觉检查

预览截图检查：开头段落正常、中间图片位置正确、结尾完整。用 `preview_screenshot` 截取。
检查项：
1. Markdown 残留（无 `#`、`*`、`---` 等原始符号）
2. 段落堆积（连续空段 ≤2）
3. 图片已渲染（img 元素存在）

### cover — 封面上传（**加固版 2026-07-21**）

**核心原则**：全部用 Playwright 原生 `page.locator().click()`，不用 `page.evaluate` 内 .click()（Vue 弹窗对 evaluate 内 click 不响应）。每步均验证，任何一步失败→刷新页面从头重试。

**黄金路径：点封面+ → 从图片库选择 → 选 cover.jpg → 下一步 → 确认 → 验证预览**

```javascript
// ========== 封面上传 — 加固 6 步序列 ==========
// 要求：cover.jpg 已存在于微信图片库（由 image_gen 步骤预先上传）

// Step 0: 检查当前封面状态，避免重复操作
const initCheck = await page.evaluate(() => {
  const preview = document.querySelector('.js_cover_preview_new');
  if (!preview) return 'no_element';
  return /mmbiz/.test(getComputedStyle(preview).backgroundImage) ? 'already_set' : 'empty';
});
if (initCheck === 'already_set') {
  // 封面已存在，跳过
} else {
  // ---------- Step 1: 点封面"+"按钮 ----------
  // 用精确选择器避免 ambiguity（.js_cover_btn_area 匹配 3 个元素）
  await page.locator('.select-cover__btn.js_cover_btn_area').first().click();
  await page.waitForTimeout(2000);

  // ---------- Step 2: 点"从图片库选择" ----------
  const libClicked = await page.evaluate(() => {
    // 选择可见的 a.pop-opr__button.js_imagedialog（3 个匹配中只有 1 个可见）
    const links = [...document.querySelectorAll('a.pop-opr__button.js_imagedialog')];
    for (const link of links) {
      if (link.offsetParent !== null) { link.click(); return true; }
    }
    return false;
  });
  if (!libClicked) throw new Error('封面步骤: 找不到可见的"从图片库选择"');
  await page.waitForTimeout(3000);

  // ---------- Step 3: 等待图片库弹窗 → 选择 cover.jpg ----------
  // 确认弹窗已渲染
  await page.locator('.weui-desktop-dialog__title').filter({ hasText: '选择图片' }).waitFor({
    state: 'visible', timeout: 5000
  });
  // 选中有"cover.jpg"字样的图片项
  await page.locator('.weui-desktop-img-picker__item').filter({ hasText: 'cover.jpg' }).first().click();
  await page.waitForTimeout(1500);

  // ---------- Step 4: 点"下一步"进入裁剪 ----------
  await page.locator('button:has-text("下一步"):not([disabled])').click();
  await page.waitForTimeout(3000);

  // ---------- Step 5: 等待裁剪弹窗 → 点"确认" ----------
  await page.locator('.weui-desktop-dialog__title').filter({ hasText: '编辑封面' }).waitFor({
    state: 'visible', timeout: 5000
  });
  await page.locator('button:has-text("确认"):not([disabled])').click();
  await page.waitForTimeout(3000);

  // ---------- Step 6: 验证封面 ----------
  const coverResult = await page.evaluate(() => {
    const preview = document.querySelector('.js_cover_preview_new');
    if (!preview) return { pass: false, reason: 'preview元素不存在' };
    const bg = getComputedStyle(preview).backgroundImage;
    return { pass: /mmbiz/.test(bg), url: bg.slice(0, 100) };
  });
  if (!coverResult.pass) {
    throw new Error(`封面验证失败: ${coverResult.reason || '无mmbiz CDN'}`);
  }
}

// ========== 完成后标记状态 ==========
// → python run_wechat_publish.py --complete
```

### 失败恢复策略

| 故障点 | 表现 | 恢复动作 |
|--------|------|----------|
| Step 1: 找不到封面按钮 | 选择器无匹配 | 刷新页面回 draft（appmsgid 不变）→ 从头重试 |
| Step 2: 菜单不弹出 | 点击后 no visible link | 刷新页面 → 重试，增 wait 到 3s |
| Step 3: 图片库弹窗空白 | Vue 组件未渲染 | 刷新页面 → 重试，增 wait 到 5s |
| Step 4: cover.jpg 不在库中 | 选择器无匹配 | 重新 image_gen 步骤生图 → 手动上传 cover.jpg → 重试 |
| Step 5: 裁剪弹窗/确认按钮不可用 | waitFor 超时 | 刷新页面 → 重试 |
| Step 6: 验证失败 | 预览图无 mmbiz CDN | 刷新页面 → 重试整个序列 |

**连续 2 次失败**：回滚到 `editor_open` 恢复点，走 `image_upload → bake → validate → insert → visual_check → cover` 重新跑。

**禁止新增分支或跳过验证**。失败就重试全序列，不另辟蹊径。

### final_verify — 终极验证

```javascript
const bp = document.querySelectorAll('.ProseMirror')[1];
const text = bp.innerText;
const preview = document.querySelector('.js_cover_preview_new');
const hasCover = preview ? /mmbiz/.test(getComputedStyle(preview).backgroundImage) : false;
const imgsWithSrc = Array.from(bp.querySelectorAll('img')).filter(i => i.src).length;
const cnCount = (text.match(/[一-鿿]/g) || []).length;
const authorInput = document.querySelector('input[placeholder="请输入作者"]');
const hasAuthor = authorInput?.value === '谋生与人性';

return {
  pass: hasCover && imgsWithSrc === 3 && cnCount >= 2400 && cnCount <= 3200 && hasAuthor,
  checks: { hasCover, imgsWithSrc, cnCount, hasAuthor }
};
```

### save — 保存草稿

```javascript
// Escape × 3 回到顶层（如有弹窗遮挡）
await page.keyboard.press('Escape');
await new Promise(r => setTimeout(r, 500));
await page.keyboard.press('Escape');
await new Promise(r => setTimeout(r, 500));

// 点击"保存为草稿"按钮
await page.locator('button:has-text("保存为草稿")').click();
await new Promise(r => setTimeout(r, 2000));

// 验证：历史版本记录中出现"手动保存"
const historyCheck = await page.evaluate(() => {
  const cells = [...document.querySelectorAll('td')];
  const saveRow = cells.find(c => c.innerText.includes('手动保存'));
  return { saved: !!saveRow, detail: saveRow?.innerText || '' };
});
// saved === true 证明保存成功
// 保存 appmsgid（从 URL 中提取）到 session_state.json
```

---

## 排版管道（v8.0 — 极简固化）

排版由 `bake_wechat_html.py` 完成，三行 CSS 常量，三种块类型：

```
split_blocks() → auto_position → 渲染 → 全文 = 三种 <p>
  ↑按。！？拆句      ↑82%/55%/25%    ↑ body / sub / img
```
| 元素 | HTML | 关键 CSS |
|------|------|----------|
| 正文 | `<p id="p{N}">` | `font-size:18px;line-height:2;margin:0 0 24px;` |
| 子标题 | `<p id="h{N}">` | `font-size:22px;font-weight:700;color:#1677ff;text-align:center;margin:32px 0;` |
| 图片包裹 | `<p id="i{N}"><img>` | `margin:28px 0;text-align:center;` |

`<p id="p/h/i{N}">` 的 `id` 唯一（N 递增），ProseMirror 不合并不同 id 的 `<p>`，且 `<p>` 不被套多层 `<section>`。只输出 `<p>`+`<img>`，通过 8 项门禁。

---

## 回归测试

检查项：
| 检查 | 预期 |
|------|------|
| 封面存在 | 有 mmbiz 背景图 |
| 无点号段 | dotCount === 0 |
| 3 张有效图片（有 src） | imgsWithSrc === 3 |
| 图片位置误差 ≤5% | [25, 55, 82] 正负 5 |
| 小标题 4-7 个 | 一二三四... |

pass=false → 回滚到上一个恢复点重新执行黄金路径。

---

## 质量门

1. **段长闸**：`check_wechat_para.py` — 无段落超 150 汉字，无连续短段（<20 汉字）
2. **AI味闸**：`ai_score.py` ≤45 分
3. **字数闸**：2400~3200 汉字
4. **去重闸**：与已发表文章标题不重复
5. **封面闸**：封面上传后验证 mmbiz CDN 存在
6. **视觉闸**：截图检查无 Markdown 残留、图片可见
7. **回归闸**：5 项回归测试全部 pass

---

## 终局错误（需通知用户）

1. 登录失效 / 扫码页面 / 验证码
2. Playwright 连续两次真实调用失败
3. 平台接口连续两次 5xx
4. 文件读写异常
5. 质量门自动修复两次仍不通过

其他一切错误由状态机自动重试或回滚恢复点。

---

## 状态机自动化 CLI 命令

```bash
python run_wechat_publish.py --status          # 查看当前状态
python run_wechat_publish.py --step            # 执行当前 AUTO 步骤
python run_wechat_publish.py --complete        # 标记当前 BROWSER 步骤完成
python run_wechat_publish.py --dry-run         # 测试所有非浏览器步骤
python run_wechat_publish.py --init "主题"      # 初始化新会话
python run_wechat_publish.py --rollback        # 回退到上一个恢复点
python run_wechat_publish.py --reset           # 重置状态机
python run_wechat_publish.py --abort REASON    # 异常终止
python run_wechat_publish.py --regression-test # 打印回归测试 JSON
```
