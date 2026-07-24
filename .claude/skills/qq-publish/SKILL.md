---
name: qq-publish
description: 企鹅号（om.qq.com）文章发布技能 v4.0 — 状态机引擎版
---

# 企鹅号 · 文章发布技能 v4.0 — 状态机收敛版

**唯一入口**：`run_qq_publish.py`（禁止绕过脚本手工操作）

**架构**：状态机引擎驱动 19 个状态。AUTO 步骤脚本自动执行，BROWSER 步骤由 Claude 调用 Playwright 操作后 `--complete`。全程不询问用户。

---

## 状态定义（19 状态摘要）

| 序号 | 状态名 | 类型 | 描述 | 恢复点 |
|------|--------|------|------|--------|
| 0 | init | auto | 检查目录/依赖 | ✅ |
| 1 | dedup | browser | 进内容管理提取已发布标题 | ✅ |
| 2 | topic | browser | 选游戏话题+写文章 | ✅ |
| 3 | write_verify | auto | 汉字数≥3000质量门 | ✅ |
| 4 | image_gen | auto | 生图：5元素随机组合cover.jpg | ✅ |
| 5 | cors | auto | CORS服务器 8768端口 | ✅ |
| 6 | editor_open | browser | 导航到新建文章编辑页 | ✅ |
| 7 | title_input | browser | 填入标题到标题span | |
| 8 | cover_upload | browser | DataTransfer注入封面图 | ✅ |
| 9 | body_insert | browser | 整段insertHTML入ProseMirror | ✅ |
| 10 | body_img_upload | browser | DataTransfer逐张传文中图 | ✅ |
| 11 | tags | browser | 输入3个标签chip | |
| 12 | category | browser | 选「游戏」分类 | |
| 13 | ai_declaration | browser | OP7自主声明+OP8素材声明 | |
| 14 | publish | browser | 点发布按钮 | ✅ |
| 15 | publish_verify | browser | 确认发布成功 | |
| 16 | review | auto | 更新选题账本 | |
| 17 | cleanup | auto | 清理临时文件 | |
| 18 | done | terminal | 完成 | ✅ |
| 19 | error | terminal | 异常终止 | ✅ |

---

## 账号信息

| 字段 | 值 |
|------|-----|
| 后台 | https://om.qq.com/main/creation/article |
| 内容管理 | https://om.qq.com/main/management/articleManage |
| 编辑器 | 企鹅号 ExEditor（标题是 span，正文是单 ProseMirror） |

## 编辑器真实 DOM 坐标

| 字段 | 真实选择器 |
|------|------------|
| 标题 | `span[data-placeholder*="标题"]`（class `.omui-inputautogrowing__inner`，contenteditable） |
| 正文 | `document.querySelector('.ProseMirror')`（class `.ExEditor-basic`，全页只有 1 个） |
| 封面按钮 | `button.omui-button--add`（`#articlePublish-coverinfo` 内，无封面时） |
| 封面缩略图 action | `.omui-thumb__action`（已有封面时点「更换」） |
| 标签 input | `.omui-suggestion__input.is--multi input.omui-suggestion__value` |
| 分类 input | `.omui-suggestion__input.is--single input.omui-suggestion__value` |
| 自主声明按钮 | `#articlePublish-selfDeclaration button.omui-button--dashed` |
| 发布按钮 | `button` 中 textContent 精确 `=== '发布'` |

---

## 内容硬指标（写文章必须达标）

- **汉字数** ≥ 3000（`len(re.findall(r'[一-鿿]', text))`）
- **每段汉字** ≤ 150（超过需拆段）
- **h2 数量** ≥ ceil(汉字数/600)，3000字→至少5个h2
- **每h2区块** ≥ 3 段文字，≥1 个短段（汉字 ≤ 50）
- **文中图** ≥ 3 张，src 必须不同，不得重复
- **段长中位数** ≤ 90，超长段(>120)占比 ≤ 10%
- **聊天体**，禁止 AI 味、禁止新闻腔、禁止标准式结尾

---

## BROWSER 步骤 SOP（BROWSER = Claude 通过 Playwright MCP 执行）

### dedup — 提取已发布标题

**输入**：浏览器已进入 contentManage（`python run_qq_publish.py --step` 输出 `NEEDS_BROWSER:dedup`）
1. 若当前不在内容管理页，`browser_navigate` → `https://om.qq.com/main/management/articleManage`
2. `evaluate` 用 `body.innerText` 逐行解析「全部」列表的标题（每行格式：`标题\n[原创/创作声明]\n日期\n[来源]\n已发布\n[未声明?]\n阅读\n0...`）
3. 把标题列表写入状态：
   ```
   python -c "json.dump({'dedup_result': titles}, open('session_state.json','w'))"
   python run_qq_publish.py --complete
   ```

**成功标准**：`session_state.json.dedup_result` 含 ≥1 个标题。
**失败处理**：重试 2 次后熔断。

### topic — 选题+写作

**输入**：
- 选题目录（`python run_qq_publish.py --topic-ledger`）：rotation_index 决定类别
- 去重列表（`session_state.json.dedup_result`）：已发标题

**写作规则**：
1. 查账本 → 确定 rotation 类别
2. 选题不与去重列表重复
3. 写文章到 `qq_article_<主题>.txt`（纯文本，无 HTML 标签，分段自然）
4. 每写完一段用 `python -c "cnt=len(re.findall(r'[一-鿿]', open('qq_article_*.txt').read())); print(cnt)"` 确认汉字数进度
5. 汉字数 ≥ 3000 后写入 state：`topic`、`title`
6. `python run_qq_publish.py --topic-category "游戏"`
7. `python run_qq_publish.py --complete`

**标题规则**：痛点+具体场景（不与 dedup_result 重复），含游戏热词。
**写作要求**：聊天体，段落长短交替，每h2区块含1个≤50汉字短段，全文中位数≤90。

### editor_open — 打开编辑器

`browser_navigate` → `https://om.qq.com/main/creation/article`
等待 `.ProseMirror` 元素出现。

### title_input — 填标题

```playwright
page.evaluate(() => {
  const titleSpan = document.querySelector('span[data-placeholder*="标题"]');
  if (titleSpan) { titleSpan.focus(); document.execCommand('selectAll'); document.execCommand('insertText', false, '文章标题'); }
});
```
验收：标题 span 显示文字。执行 `python run_qq_publish.py --complete`

### cover_upload — 封面上传（DataTransfer 注入）

**前置**：CORS 服务器已在 step 5 启动（`127.0.0.1:8768`，cover.jpg 已在 image_gen 步骤生成）。

1. 点 `button.omui-button--add` → 弹窗
2. 点 `.omui-tab__label` 中 textContent='本地上传'
3. DataTransfer 注入：
```playwright
const r = await fetch('http://127.0.0.1:8768/cover.jpg');
const f = new File([await r.blob()], 'cover.jpg', {type:'image/jpeg'});
const dt = new DataTransfer(); dt.items.add(f);
const fileInput = document.querySelector('.omui-upload-image-trigger input[type=file]');
Object.defineProperty(fileInput, 'files', {value: dt.files, configurable:true});
fileInput.dispatchEvent(new Event('change', {bubbles:true}));
```
4. 等 5s → 弹窗出现缩略图
5. 点缩略图（`.omui-thumb`）→ 点「确认」button
6. 验收：`#articlePublish-coverinfo` 内出现 img（src=inews.gtimg.com/om_ls/...）
7. `python run_qq_publish.py --complete`

**失败处理**：弹窗遮罩拦截 → evaluate 关残留弹窗 `.omui-dialog-wrapper.open button.cancel` 再重试。

### body_insert — 正文插入

**输入**：`qq_article_<主题>.txt` → 需转为 HTML（含 `<h2>`、`<p>`、`<img src="__BODY_IMG_N__">` 占位符）

1. 读取文章文本，转换为 HTML：
   - 标题行加 `<h2>` 标记
   - 每段 `<p>`
   - 在 25%/50%/75% 位置插入 `<img src="__BODY_IMG_1__">`、`<img src="__BODY_IMG_2__">`、`<img src="__BODY_IMG_3__">`
2. 单次整段 insertHTML（禁止逐块 append）：
```playwright
const pm = document.querySelector('.ProseMirror');
pm.focus();
document.execCommand('selectAll');
document.execCommand('delete');
// 单次插入整篇 HTML
const fullHtml = `...`;
document.execCommand('insertHTML', false, fullHtml);
```
3. 验收：`evaluate document.querySelectorAll('.ProseMirror img').length ≥ 3`
4. `python run_qq_publish.py --complete`

### body_img_upload — 文中图上传（DataTransfer 注入）

**逐张操作**（每张图 src 必须不同）：
1. 点编辑器工具栏「插入图片」button
2. 弹窗→点 textContent='本地上传'
3. DataTransfer 注入（同 cover_upload 步骤 3）
4. 等 5s → 弹窗出现缩略图列表
5. 点缩略图选中 → 点「确认」
6. **重复 1-5 共 3 次**，每次换不同的图片文件（inline1.jpg、inline2.jpg、inline3.jpg）
7. 验收：evaluate `.ProseMirror img` 的 naturalWidth > 0，去重 src 数 ≥ 3
8. 检查未通过 → 退回重传，最多 3 轮
9. `python run_qq_publish.py --complete`

### tags — 输入标签

```playwright
await page.focus('.omui-suggestion__input.is--multi input.omui-suggestion__value');
await page.type('.omui-suggestion__input.is--multi input.omui-suggestion__value', '标签1', {delay:50});
await page.keyboard.press('Enter');
// 重复 2 次
```
验收：出现 3 个 chip。`python run_qq_publish.py --complete`

### category — 选分类

```playwright
await page.locator('.omui-suggestion__input.is--single input.omui-suggestion__value').click();
await page.locator('.omui-suggestion__input.is--single input.omui-suggestion__value').fill('游戏');
// 等下拉出现，选第一个
await page.locator('[class*="suggestion__list"] div:first-child').click();
```
验收：分类显示「游戏」。`python run_qq_publish.py --complete`

### ai_declaration — 自主声明 + AI 素材声明

**OP7 文章级声明**：
```playwright
// 点「添加内容自主声明」
await page.locator('#articlePublish-selfDeclaration button.omui-button--dashed').click({force:true});
// 选中「该文章由AI生成」
await page.locator('text=该文章由AI生成').click();
// 点「确认」
await page.locator('text=确认').click();
```
验收：显示「作者声明：该文章由AI生成」

**OP8 素材级声明**：
```playwright
// 点「进行补充>」
await page.locator('text=进行补充').click();
// 全选图片素材
await page.evaluate(() => document.querySelectorAll('figure').forEach(f => f.click()));
// 点「提交」
await page.locator('text=提交').click();
```
验收：页面无「存在未进行AI生成声明素材」文本。`python run_qq_publish.py --complete`

### publish — 发布

```playwright
// 精确匹配「发布」按钮
const allButtons = document.querySelectorAll('button');
const publishBtn = Array.from(allButtons).find(b => b.textContent.trim() === '发布');
if (publishBtn) publishBtn.click();
```
验收：URL 跳转到 `/main/management/articleManage`。`python run_qq_publish.py --complete`

### publish_verify — 验证发布

1. URL 含 `/main/management/articleManage` → 发布成功（审核中）
2. 列表顶部出现新标题
3. 记录本次发布到笔记
4. `python run_qq_publish.py --complete`

---

## 终局错误（需通知用户）

1. 登录失效/验证码
2. Playwright 连续两次真实调用失败
3. 平台接口连续两次 5xx
4. 文件读写异常
5. 质量门重试 2 次仍不通过

其他一切错误由状态机自动重试或回滚到 recovery point。

---

## §7 已知坑（硬性映射表）

| 编号 | 症状 | 根因 | 解法 |
|:-----|:-----|:-----|:-----|
| K1 | 发布按钮匹配多个 | React DOM 含隐藏按钮 | textContent 精确 `=== '发布'` |
| K3 | radio 选中后提交不生效 | React 未检测 change | click + `dispatchEvent(new Event('change', {bubbles:true}))` |
| K6 | 封面传不上 | 浏览器禁 file chooser 脚本操作 | DataTransfer 注入 + CORS server fetch |
| K8 | 点发布无反应 | 标题为空校验先触发 | 发布前 evaluate 确认标题已填 |
| K19 | 正文逐块 append insertHTML 被吞 | ExEditor ProseMirror schema 合并后续块 | **单次整段 insertHTML** |
| K20 | 自主声明按钮 evaluate .click() 不弹窗 | 部分 React 按钮需真实手势 | `locator.click({force:true})` |
| K22 | 发布报「请选择分类」「请选择自主声明」 | 分类/声明是必填 | 先设分类再自主声明再发布 |
| K23 | 分类/标签 input 键入不生效 | React 受控输入，仅 `.value=` 不更新 state | `browser_type` slowly + 候选 click |
| K25 | 点自主声明/封面时弹窗被遮罩拦截 | 之前弹窗未关 | evaluate `.omui-dialog-wrapper.open .cancel` 关闭残留弹窗 |
| K26 | 封面上传弹窗打不开 | 草稿已有封面则显示「更换」非「添加」 | `browser_click` 真实手势点 `.omui-thumb__action` |
| K29 | 发布后有「未声明」告警 | OP7 已设但 OP8 图片级声明未做 | OP7+OP8 都要做 |
| K32 | 发布后文中图全裂（0张渲染） | insertHTML 用了外链非图床 src | src 用 `inews.gtimg.com` 图床链接，验收 naturalWidth |

### 新坑记录模板
```
新坑编号：Kxx
症状：
根因：
唯一解法：
关联步骤：
```

---

## CLI 命令（全部）

```
python run_qq_publish.py --status             # 查看当前状态
python run_qq_publish.py --step               # 执行当前 AUTO 步骤
python run_qq_publish.py --complete           # 标记 BROWSER 步骤完成
python run_qq_publish.py --dry-run            # 测试所有非浏览器步骤
python run_qq_publish.py --init TOPIC         # 初始化新会话
python run_qq_publish.py --topic-ledger       # 查看选题账本
python run_qq_publish.py --topic-category     # 记录选题类别
python run_qq_publish.py --rollback           # 回退到上一个恢复点
python run_qq_publish.py --reset              # 重置状态机
python run_qq_publish.py --abort REASON       # 异常终止
```
