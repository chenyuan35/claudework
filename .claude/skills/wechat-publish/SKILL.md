---
name: wechat-publish
description: 公众号谋生与人性全自动生产管线 v9.0 — 减法收敛版
vars:
  siliconflow_api_key: sk-fhyebysadetapteypeklskautvwwpcizruxnqhbwmrqbacfy
---

# 公众号「谋生与人性」v9.0 — 减法收敛版

**唯一入口**：`run_wechat_publish.py`（禁止绕过脚本手工操作）

**架构**：状态机引擎驱动 21 个状态。AUTO 步骤脚本自动执行，BROWSER 步骤由 Claude 调用 Playwright 操作后 `--complete`。全程不询问用户。

---

## 状态定义（21 状态摘要）

| 序号 | 状态名 | 类型 | 描述 | 恢复点 |
|------|--------|------|------|--------|
| 0 | init | auto | 检查目录/依赖 | ✅ |
| 1 | dedup | browser | 提取已发表标题到 state | ✅ |
| 2 | topic | browser | 基于账本 rotation 选题+写文章（分节追加，见下方增量规则） | ✅ |
| 3 | write | auto | 验证汉字数≥3000；不足时报各章节汉字数引导追加 | ✅ |
| 4 | split_paras | auto | 将段落拆为≤60汉字短段，不删改内容 | |
| 5 | qa_para | auto | 段长闸（<150 汉字/段，无连续短段） | |
| 6 | qa_ai | auto | AI 味闸（ai_score.py ≤45） | |
| 7 | image_gen | auto | 生图：cover.jpg + inline1-3.jpg | ✅ |
| 7 | cors | auto | 启动 CORS 服务器 | ✅ |
| 8 | editor_open | browser | 导航到新建文章编辑页 | ✅ |
| 9 | title_author | browser | 填入标题和作者 | |
| 10 | image_upload | browser | 上传 inline1-3.jpg，提取 CDN URL | ✅ |
| 11 | bake | auto | bake_wechat_html.py 烘焙 | |
| 12 | validate | auto | validate_wechat_html.py 门禁 | ✅ |
| 13 | insert | browser | fetch CORS → 清空 → innerHTML 插入 | ✅ |
| 14 | cover | browser | 上传并设置封面图 | ✅ |
| 15 | final_verify | browser | DOM 检查 4 项 | ✅ |
| 16 | publish_ready | browser | 页面留给用户发表 | ✅ |
| 17 | review | auto | 更新选题账本 | |
| 18 | cleanup | auto | 清理临时文件 | |
| 19 | done | terminal | 完成 | ✅ |
| 20 | error | terminal | 异常终止 | ✅ |

完整状态定义在 `run_wechat_publish.py` 第 51-73 行的 `STATES_DEF`，SKILL.md 不再重复。

---

## BROWSER 步骤 SOP（BROWSER = Claude 通过 Playwright MCP 执行）

### dedup — 提取已发表标题

**输入**：微信公众平台已登录状态
**动作**：
1. `browser_navigate` → `https://mp.weixin.qq.com/`（落地页 token 形如 700980744）
2. `python -c "json.load(open('session_state.json'));s['token']='{token}';json.dump(s,...)"` 写入 state
3. `browser_navigate` → `https://mp.weixin.qq.com/cgi-bin/appmsgpublish?sub=list&begin=0&count=20&token={token}&lang=zh_CN`
4. `evaluate(提取脚本)` → 得到去重标题列表
5. `python -c "s['dedup_result']=json.dumps(titles,ensure_ascii=False);json.dump(s,...)"` 写入 `session_state.json`
6. `python run_wechat_publish.py --complete`

**提取脚本**：querySelectorAll `a, .title, h4, span, strong, [class*="title"]` → 过滤掉导航按钮和系统文字 → 去重 → 去掉「原创」后缀。详见 `run_wechat_publish.py` 步骤 1-3 的 JS。

**成功标准**：`session_state.json.dedup_result` 含 ≥1 个标题。
**失败处理**：重试 2 次后熔断（token 失效则需用户重新登录）。

### topic — 选题+写作（增量规则，禁止覆盖全文）

**输入**：
- 选题账本（`python run_wechat_publish.py --topic-ledger`）：rotation_index 决定类别
- 去重列表（`session_state.json.dedup_result`）：已发标题

**增量写作规则**（硬性，无例外）：
1. **先写大纲**：确定 3-5 个章节标题和目标汉字数（每节 600-1000 汉字，总 ≥3000）
2. **分节生成**：每写完一节立即执行以下命令追加：
   ```
   python run_wechat_publish.py --section-append "章节标题" "章节内容"
   ```
   - `--section-append` 会先备份当前版本、追加内容、验证汉字数上升
   - 如果汉字数下降（不应发生），自动回滚上一版本
3. **每节达标**：`python run_wechat_publish.py --write-status` 确认当前汉字数满足该节预算后，再写下一节
4. **附录优先**：正文写完前禁止拆段；写满 3000 汉字后再 `--split-paras`
5. **不足时只追加**：全文写完后 `python run_wechat_publish.py --status` 如果 write 步骤失败（<3000），只向指定章节追加内容
6. **字数下降→回滚**：连续两次修改汉字数不增反降，立即停止并恢复上一版本版本
7. **保留每次合格版本**：`_article_versions/` 目录自动备份，不需要手动操作

**具体步骤**：
1. 查账本 → 确定 rotation 类别
2. 写大纲 → 写入 `wechat_article_<主题>.txt`
3. 按大纲分节写 → 每节用 `--section-append` 追加
4. 每节后用 `--write-status` 确认汉字数增长
5. 全部节写完 → `--split-paras` 拆段
6. 写入 state：`topic`、`title`、`article_file`
7. `python run_wechat_publish.py --topic-category "类别"`
8. `python run_wechat_publish.py --complete`

**标题规则**：
- 格式：痛点+具体场景（不与 dedup_result 重复）
- 含类别相关热词

**成功标准**：article_file 存在且汉字数≥2400。
**失败处理**：重试 2 次，超过则熔断。

### editor_open — 打开编辑器

`browser_navigate` → `https://mp.weixin.qq.com/cgi-bin/appmsg?t=media/appmsg_edit_v2&action=edit&isNew=1&type=77&createType=0&token={token}&lang=zh_CN`

等待 `.ProseMirror` 元素出现。

### title_author — 填标题和作者

```playwright
page.evaluate(() => {
  document.querySelectorAll('.ProseMirror')[0].focus();
  document.execCommand('selectAll');
  document.execCommand('insertText', false, '文章标题');
});
page.locator('input[placeholder="请输入作者"]').fill('谋生与人性');
```

### image_upload — 上传正文图片

1. 移除遮挡层（`evaluate: document.querySelector('.media_list_box_mask')?.remove()`）
2. 点击 `li#js_editor_insertimage` → 点击「本地上传」
3. filechooser 选择 `inline1.jpg` + `inline2.jpg` + `inline3.jpg`
4. 等待 10s 上传
5. `evaluate` 提取正文中所有 `<img>` 的 `src`（前 3 个含 CDN 的 URL）
6. `python -c "s['cdn_urls']=cdn_list;json.dump(s,...)"` 写入 state（注意：存为 list，不是 json.dumps 字符串）
7. `python run_wechat_publish.py --complete`

### insert — 插入正文

```playwright
const resp = await fetch(`http://127.0.0.1:{cors_port}/article_final.html`);
const html = await resp.text();
const bodyPM = document.querySelectorAll('.ProseMirror')[1];
bodyPM.innerHTML = '';
await new Promise(r => setTimeout(r, 200));
bodyPM.innerHTML = html;
bodyPM.dispatchEvent(new Event('input', {bubbles: true}));
await new Promise(r => setTimeout(r, 500));
// 验证：正文中带 src 的 img 数 == 3
```

**注**：CORS 端口从 `_cors_port.txt` 或 `session_state.json.cors_port` 读取，非固定值。

### cover — 上传并设置封面

**Phase A：传 cover.jpg 到图片库**

步骤同 image_upload（点击 `li#js_editor_insertimage` → 本地上传 → filechooser `cover.jpg` → 等待 15s）。
传完后用 CORS fetch `article_final.html` 覆盖正文（cover.jpg 上传后会被插入正文末尾），验证正文图片数恢复为 3。

**Phase B：从图片库选封面**

1. 点击封面「+」按钮（`.select-cover__btn.js_cover_btn_area`）→ 弹出菜单
2. 点击「从图片库选择」
3. 在「选择图片」弹窗中点「最近使用」→ 选第一张图
4. 点「下一步」→ 裁剪弹窗中点「确认」
5. 验证：预览区 `.js_cover_preview_new` 的 `backgroundImage` 含 `mmbiz`

**成功标准**：封面 mmbiz CDN 存在。
**失败处理**：任何一步失败 → 刷新编辑页 → 从 Phase A 重试。连续 2 次失败回滚到 `image_upload` 恢复点重走全序列。

### final_verify — 终极验证

```playwright
const bp = document.querySelectorAll('.ProseMirror')[1];
const text = bp.innerText;
const preview = document.querySelector('.js_cover_preview_new');
const checks = {
  hasCover: preview ? /mmbiz/.test(getComputedStyle(preview).backgroundImage) : false,
  imgsWithSrc: Array.from(bp.querySelectorAll('img')).filter(i => i.src).length,
  cnCount: (text.match(/[一-鿿]/g) || []).length,
  hasAuthor: document.querySelector('input[placeholder="请输入作者"]')?.value === '谋生与人性'
};
return { pass: checks.hasCover && checks.imgsWithSrc === 3 && checks.cnCount >= 2400 && checks.hasAuthor, checks };
```

**不通过 → 回滚到 `editor_open` 恢复点重走全序列。**

### publish_ready — 通知用户

页面保持在编辑状态。告知用户：文章已准备就绪，可在编辑页审核后发表。

---

## 质量门（硬性，不通过即重试或熔断）

1. 汉字数≥3000（`len(re.findall(r'[一-鿿]', text))`，只计 CJK 统一表意字符）
2. 段长闸：check_wechat_para.py — 无段落超 150 汉字，无连续短段（<20 汉字）
3. AI 味闸：ai_score.py ≤45
4. 标题与已发表不重复
5. 正文图数=3
6. 封面上传含 mmbiz CDN

## 终局错误（需通知用户）

1. 登录失效/扫码页面/验证码
2. Playwright 连续两次真实调用失败
3. 平台接口连续两次 5xx
4. 文件读写异常
5. 质量门重试 2 次仍不通过

其他一切错误由状态机自动重试或回滚恢复点。

---

## CLI 命令（全部）

```
python run_wechat_publish.py --status             # 查看当前状态
python run_wechat_publish.py --step               # 执行当前 AUTO 步骤
python run_wechat_publish.py --complete           # 标记 BROWSER 步骤完成
python run_wechat_publish.py --dry-run            # 测试所有非浏览器步骤
python run_wechat_publish.py --init               # 初始化新会话（自动选题）
python run_wechat_publish.py --topic-category     # 记录选题类别
python run_wechat_publish.py --topic-ledger       # 查看选题账本
python run_wechat_publish.py --rollback           # 回退到上一个恢复点
python run_wechat_publish.py --reset              # 重置状态机
python run_wechat_publish.py --abort REASON       # 异常终止
python run_wechat_publish.py --section-append     # 追加章节（自动备份+验证汉字数增长）
python run_wechat_publish.py --write-status       # 显示汉字数/章节分布/版本数
python run_wechat_publish.py --split-paras        # 段落拆分为≤60汉字短段（不删改内容）
python run_wechat_publish.py --write-backup       # 主动备份当前文章版本
python run_wechat_publish.py --write-rollback     # 回滚到上一文章版本
```

## 排版管道（不变）

`bake_wechat_html.py`：`split_blocks()` 按 `。！？` 拆句 → `--auto-position` 自动算图位置（25%/55%/82%）→ 输出 `<p id="p/h/i{N}">` 三种块。`<p id="p/h/i{N}">` 的 `id` 递增，ProseMirror 不合并不同 id 的 `<p>`，且 `<p>` 不被套 `<section>`。
