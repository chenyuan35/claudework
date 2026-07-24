# CSDN 资源上传技能

**触发**：`/csdn-resource-upload` 或「上传 CSDN 资源」
**账号**：deepseek23（https://blog.csdn.net/deepseek23）
**定位**：AI 工具 / LLM 应用 / MCP 协议相关开源项目或原创代码资源上传
**页面**：https://upload.csdn.net/creation/uploadResources
**版本**：v1.3（2026-07-06）

## §0 准备工作

### §0a 从 GitHub 选择可商用开源项目

**原则**：只选明确允许重新分发的许可证，避免法律风险。

| 许可证 | 商用 | 重新分发 | 备注 |
|--------|------|---------|------|
| MIT | ✅ | ✅ | 最宽松，可改可卖 |
| Apache 2.0 | ✅ | ✅ | 需保留版权声明 |
| BSD 2/3-Clause | ✅ | ✅ | 类似 MIT |
| MIT + Apache 2.0 | ✅ | ✅ | 双许可选宽松的 |
| GPL v3 | ⚠️ 有限制 | ✅ | 传染性，整个项目必须 GPL |
| AGPL v3 | ❌ | ✅ | 网络使用也受限制 |
| CC0 | ✅ | ✅ | 公共领域，无限制 |
| 无许可证 | ❌ | ❌ | 默认保留所有权利 |

**优先选**：MIT、Apache 2.0、BSD、CC0 协议的项目。

### §0b 项目选择 + 包装增值策略

1. **GitHub 搜索**：`https://api.github.com/search/repositories?q=topic:xxx+license:mit+language:python&sort=stars&order=desc`
2. **筛选标准**：
   - ⭐ Stars ≥ 100（社区认可）
   - 📅 近期更新（近 1 年内）
   - 📄 有 README（方便生成描述）
   - 🔖 MIT / Apache 2.0 许可证
3. **推荐方向**（跟 CSDN 账号定位一致）：
   - Python 工具库（CLI 工具、代码生成器）
   - LLM / AI 相关（小型推理框架、Prompt 工具）
   - 开发效率工具（自动补全、格式化、lint 配置包）
   - MCP Server 示例（小而完整的 MCP 实现）
4. **下载后处理（关键：避免 isRepeat=true）**：
   - 直接搬运 GitHub 原始 zip → MD5 跟已有资源重复 → 提交失败
   - **必须做包装增值**：加中文 README + 中文示例脚本 → MD5 改变 → isRepeat=false
   - 压缩为 `.zip`（CSDN 读者习惯下载源码包）
   - 包内保留原 LICENSE 文件（MIT 许可证要求）

### §0c GitHub 下载（代理优先）

**⚠️ 国内访问 GitHub 直连大概率连接重置。** 检测代理端口后再下载。

```bash
# 检测常见代理端口（7890=新VPN, 1080=旧VPN）
for port in 7890 1080; do
  code=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 2 "http://127.0.0.1:$port")
  [ "$code" != "000" ] && echo "端口 $port 可用 (HTTP $code)" && PROXY_PORT=$port && break
done
[ -z "$PROXY_PORT" ] && echo "未检测到可用代理" && exit 1

# 通过代理下载 GitHub 仓库
https_proxy=http://127.0.0.1:$PROXY_PORT http_proxy=http://127.0.0.1:$PROXY_PORT \
  curl -L -o project.zip "https://github.com/{owner}/{repo}/archive/refs/heads/main.zip"
```

如果系统没有 `zip` 命令，用 Python 打包：
```bash
python -c "
import zipfile, os
src = 'Project-main'
dst = '../project-packaged.zip'
with zipfile.ZipFile(dst, 'w', zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk(src):
        for f in files:
            fp = os.path.join(root, f)
            zf.write(fp, os.path.relpath(fp, start=os.path.dirname(src)))
"
```

### §0d 文件路径格式（Playwright upload）

`setInputFiles` 必须用正斜杠路径 `C:/Users/...`，反斜杠 `C:\Users\...` 导致 ENOENT。

### 前置启动
```python
# 如果资源需要配图（封面/正文说明图），先启动图片服务器
python img_server.py
```

### 执行脚本

```javascript
// 全部操作在 https://upload.csdn.net/creation/uploadResources 执行
// 使用 Playwright MCP 工具（mcp__playwright__*）

// ========== Step 1: 上传文件 ==========
// 用 setInputFiles 注入本地文件
// 工具：browser_run_code_unsafe
const fileInput = page.locator('input.el-upload__input');
await fileInput.setInputFiles('资源文件路径.zip');
await page.waitForTimeout(2000);

// ========== Step 2: 填资源名称 ==========
// 工具：browser_run_code_unsafe — page.locator('textarea').nth(0).fill('...')
// 选择器：textarea.el-textarea__inner (第一个)
// 限制：100 字符
// 推荐格式：知识领域+技术关键词+内容关键词+用途
await page.locator('textarea').nth(0).fill('资源名称');

// ========== Step 3: 填资源描述 ==========
// 工具：browser_run_code_unsafe — page.locator('textarea').nth(1).fill('...')
// 选择器：textarea.el-textarea__inner (第二个)
// 限制：800 字符
await page.locator('textarea').nth(1).fill('资源描述...');

// ========== Step 4: 加标签 ==========
// 工具：browser_evaluate（⚠️ 注意：标签输入框是 Element Plus ElAutocomplete 组件，
// Playwright 的 locator/fill 无法定位该元素，必须用 page.evaluate 通过原生 DOM API 操作）
// 限制：最多 5 个标签，每标签 ≤16 字符
// 标签含空格会被自动去掉（如 "AI Agent" → "AIAgent"）
// ⚠️ 关键事件序列：setter + input + compositionend + keydown/press/up(Enter) + change + blur
// 缺少其中任何一个事件，标签都不会被提交

// Step 4a-4b 合并：点击添加按钮 + 输入 + 提交（全部在一个 evaluate 内完成）
// ⚠️ mcp__playwright__browser_evaluate 工具不能传递函数参数，标签文本必须硬编码在函数体内
// template（使用前把 val 常量改为目标标签文本）:
async () => {
  const val = 'AI工具';  // ← 改这里
  const btn = document.querySelector('.new-tag-btn');
  if (!btn) return 'no button';
  btn.click();
  await new Promise(r => setTimeout(r, 500));
  const auto = document.querySelector('.el-autocomplete.input-new-tag');
  if (!auto) return 'no auto';
  const input = auto.querySelector('.el-input__inner');
  if (!input) return 'no input';
  const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
  setter.call(input, val);
  input.dispatchEvent(new Event('input', { bubbles: true }));
  await new Promise(r => setTimeout(r, 200));
  input.dispatchEvent(new CompositionEvent('compositionend', { data: val, bubbles: true }));
  await new Promise(r => setTimeout(r, 100));
  ['keydown','keypress','keyup'].forEach(t => {
    input.dispatchEvent(new KeyboardEvent(t, { key: 'Enter', keyCode: 13, which: 13, bubbles: true, cancelable: true }));
  });
  input.dispatchEvent(new Event('change', { bubbles: true }));
  await new Promise(r => setTimeout(r, 200));
  input.blur();
  input.dispatchEvent(new FocusEvent('blur', { bubbles: true }));
  await new Promise(r => setTimeout(r, 300));
  return `added "${val}"`;
}

// 使用示例（逐次调用，每次硬编码不同的 val 常量）：
// 第1次：const val = 'AI工具';
// 第2次：const val = '命令行';
// 第3次：const val = 'MCP';
// 第4次：const val = 'Python';
// 第5次：const val = '开源';
// 注意：最多 5 个标签；达到上限后 .new-tag-btn 消失

// ========== Step 5: 选分类 ==========
// 工具：browser_run_code_unsafe — 级联选择器 el-cascader
// 第一步：点击分类下拉
await page.getByRole('textbox', { name: '请选择' }).first().click();
await sleep(1500);

// 第二步：点击一级类目（如"人工智能"）
await page.locator('[role="menuitem"]:has-text("人工智能")').click();
await sleep(1000);

// 第三步：点击子类目（如"自然语言处理"）
// 方法 A（推荐）：用 CSS 选择器定位第二个级联菜单的第 N 项
// 子菜单索引：机器学习→1, 深度学习→2, 搜索引擎→3, 自然语言处理→4
await page.locator('.el-cascader-menu:nth-child(2) .el-cascader-node:nth-child(4)').click();
// 方法 B（备选）：直接文本匹配（注意 [role="menuitem"] 匹配 27+ 个元素，需限定级联列表内）
// await page.locator('[role="listbox"] [role="menuitem"]:has-text("自然语言处理")').click();

// 分类级联结构（23 个一级类目）：
// 前端 / 后端 / 行业研究 / 移动开发 / 操作系统
// 人工智能→{机器学习,深度学习,搜索引擎,自然语言处理}
// 物联网 / 信息化管理 / 网络技术 / 安全技术 / 数据库
// 硬件开发 / 游戏开发 / 考试认证 / 服务器应用 / 音视频
// 大数据 / 存储 / 云计算 / 区块链 / 跨平台 / 3D模型 / 半导体

// ========== Step 6: 确认发布形式 ==========
// ⚠️ 实测发现：表单默认选中"积分资源"，但多次操作后可能自动切换到"VIP专享资源"
// 每次提交前必须强制设为"积分资源"

// Step 6a: 确保选中"积分资源"
const freeRadio = page.locator('label.el-radio').filter({ hasText: '积分资源' });
await freeRadio.click();
await page.waitForTimeout(300);

// ========== Step 7: 设置所需积分 ==========
// 默认 0（即免费下载）
// 选择器：input[placeholder="请选择"]（第二个）默认值 "0"
// 不需要额外操作

// ========== Step 8: 验重（提交前最后一关）==========
// 检查 network 中 checkUploadSource 的响应
// 响应体：{"code":200,"data":{"isRepeat":false}}
// isRepeat=true → 停止提交，返回§0b 重新打包
// isRepeat=false → 继续提交

// ========== Step 9: 提交 ==========
// ⚠️ 提交前务必验重！否则 isRepeat=true 导致静默失败
// 验证方法：检查 network 中 checkUploadSource 的响应
// 用 browser_network_request(index) 查看 response-body

// 工具：browser_run_code_unsafe
const submitBtn = page.locator('button.form-button').last();
await submitBtn.scrollIntoViewIfNeeded();
await page.waitForTimeout(500);
await submitBtn.click({ force: true });
console.log('已点击提交');

// 等待 5-8s 让后端处理
await page.waitForTimeout(5000);

// Step 10: 提交后检测
// 态 1: 弹窗 "恭喜完成上传"（dialog 含"查看资源""继续上传"按钮）
// 态 2: 页面 URL 不变，无任何反馈 → isRepeat 或表单验证失败
// 态 3: 提交按钮变为 disabled

const postResult = await page.evaluate(() => {
  const dialog = document.querySelector('[role="dialog"][aria-label*="恭喜"]');
  if (dialog) {
    const dialogText = dialog.textContent || '';
    return {
      status: 'success',
      dialogText: dialogText.substring(0, 200),
      hasViewBtn: dialogText.includes('查看资源'),
    };
  }
  return { status: 'unknown' };
});

if (postResult.status === 'success') {
  console.log('🎉 上传成功!', postResult.dialogText);
  // 可选：点击"查看资源"跳转到上传明细页
  // await page.getByText('查看资源').click();
} else {
  console.error('❌ 提交无响应，检查 network 中 checkUploadSource');
}
```

### 手动步骤表（Playwright MCP 工具）

| 步骤 | 操作 | 选择器 | Playwright MCP 工具 | 交互 |
|------|------|--------|--------------------|------|
| 1 | 上传文件 | `input.el-upload__input` | `browser_run_code_unsafe` | `page.locator('input.el-upload__input').setInputFiles('path')` |
| 2 | 资源名称 | `textarea.el-textarea__inner` (第1个) | `browser_run_code_unsafe` | `page.locator('textarea').nth(0).fill('名称')` |
| 3 | 资源描述 | `textarea.el-textarea__inner` (第2个) | `browser_run_code_unsafe` | `page.locator('textarea').nth(1).fill('描述')` |
| 4 | 添加标签 | `.new-tag-btn` (click) + `page.evaluate` 原生DOM | `browser_evaluate` | 见 §1 Step 4 完整事件序列 |
| 5 | 标签提交 | `.el-autocomplete.input-new-tag .el-input__inner` | `browser_evaluate` | ⚠️ Playwright locator 无法定位该 input，必须用 evaluate |
| 5a | 开分类选择 | `input[placeholder="请选择"]` 第1个 | `browser_run_code_unsafe` | `getByRole('textbox',{name:'请选择'}).first().click()` |
| 5b | 选一级类目 | `.el-cascader-menu:first-child [role="menuitem"]:has-text("类目")` | `browser_click` | 点击一级类目（如"人工智能"） |
| 5c | 选子类目 | `.el-cascader-menu:nth-child(2) .el-cascader-node:nth-child(N)` | `browser_click` | 子菜单在第二 panel；N=1 机器学习,2 深度学习,3 搜索引擎,4 自然语言处理 |
| **6a** | **确保积分资源** | **`label.el-radio:has-text("积分资源")`** | **`browser_run_code_unsafe`** | **`page.locator('label.el-radio').filter({hasText:'积分资源'}).click()`** |
| 7 | 确认积分 | `input[placeholder="请选择"]` 第2个（默认0） | 不需操作 | 默认 0 |
| 8 | 验重 | `checkUploadSource` API 响应 | `browser_network_request` | 查看 `isRepeat` 字段 |
| 9 | 提交 | `button.form-button` | `browser_run_code_unsafe` | `page.locator('button.form-button').last().click({force:true})` |
| 10 | 成功后验证 | `[role="dialog"][aria-label*="恭喜"]` | `browser_evaluate` | 检查"恭喜完成上传"弹窗 |

## §2 已知坑

| 坑 | 现象 | 原因/修复 |
|----|------|----------|
| ⚠️ **isRepeat=true** | 提交按钮点后无反应，页面不变 | 文件 MD5 跟已有资源重复。§0b 包装增值改变 MD5 后重试 |
| ⚠️ **发布形式自动切到 VIP** | 提交后发现资源是"VIP专享"，用户需 VIP 才能下载 | Step 6a：**每次提交前必须主动** `page.locator('label.el-radio').filter({hasText:'积分资源'}).click()` 强制选中 |
| **提交后无任何反馈** | 点了按钮，页面不变，没 toast 没弹窗 | 通常是 isRepeat 或表单验证失败。检查 network 中 `checkUploadSource` 和 `source/calculation` 的请求 |
| **成功弹窗被遮挡** | 成功后弹 dialog，可能被其他元素挡住 | 选择器：`[role="dialog"][aria-label*="恭喜"]`，包含"查看资源"和"继续上传"按钮 |
| Lv0 账号限制 | 积分资源可发，VIP/付费禁用 | 需要提升创作分 + 完成原创认证才能解锁更多发布形式 |
| 标签空格被移除 | 输入"AI Agent"变成"AIAgent" | CSDN 的 tag 组件自动去空格，标签名取文本节点的 trimmed text |
| ⚠️ **标签输入框 Playwright locator 不可达** | `page.locator('.input-new-tag input')` 超时找不到元素 | 标签输入框是 Element Plus ElAutocomplete 组件，input 在 Vue 渲染中 Playwright 无法直接定位。**必须用 `page.evaluate` 通过原生 DOM API 操作**（setter + input + compositionend + keydown/keypress/keyup Enter + change + blur 完整事件序列） |
| `input.el-upload__input` 隐藏 | 文件上传 input 是隐藏的 | `setInputFiles` 在 Playwright 中能操作隐藏元素，不需先 click 上传区域 |
| ⚠️ **文件路径必须用正斜杠** | `C:\Users\...` 格式报 ENOENT | `setInputFiles` 接受 `C:/Users/...`（正斜杠）格式的路径 |
| ⚠️ **browser_evaluate 无法传参** | `page.evaluate((val)=>{...}, tagText)` 第二参数被忽略 | 标签文本必须硬编码在 evaluate 函数的 `val` 变量中，逐个添加 |
| **GitHub 直连下载重置** | curl "Connection was reset" | 通过代理下载（自动探测 7890/1080 哪个可用） |
| **zip 命令不可用** | Git Bash 无 zip | 用 `python -c "import zipfile..."` 通过 Python 打包 |
| **子类目定位** | `[role="menuitem"]:has-text("自然语言处理")` 超时 | 改用 `.el-cascader-menu:nth-child(2) .el-cascader-node:nth-child(4)` |
| 文件重传 | 同一页面第二次上传类似文件 | 页面需要刷新（browser_navigate）否则旧文件状态残留 |
| ~~提交按钮变 disabled~~ | 成功后提交按钮变为 `disabled` | 这是正常状态，标识"已提交" |

## §3 坐标总表

| # | 元素 | 选择器 | 状态（2026-07-06） |
|---|------|--------|-------------------|
| 1 | 文件上传 input | `input.el-upload__input` | ✅ 有效 |
| 2 | 资源名称 textarea | `textarea.el-textarea__inner:nth-of-type(1)` | ✅ 有效 |
| 3 | 资源描述 textarea | `textarea.el-textarea__inner:nth-of-type(2)` | ✅ 有效 |
| 4 | 添加标签按钮 | `.new-tag-btn` | ✅ 有效（需要 evaluate 操作，见 §1 Step 4） |
| 5 | 标签输入框 | `.el-autocomplete.input-new-tag .el-input__inner` | ⚠️ Playwright locator 不可达，必须 evaluate |
| 6 | 已添加标签 | `.el-tag.el-tag--light` | ✅ 有效 |
| 7 | 分类下拉 | `input[placeholder="请选择"]` 第一个 | ✅ 有效 |
| 8 | 一级类目 | `[role="menuitem"].el-cascader-node` | ✅ 有效 |
| 9 | 子类目 | `.el-cascader-menu:nth-child(2) .el-cascader-node:nth-child(N)` | ✅ 有效（子菜单在第二个 panel 中，N 从 1 开始） |
| 10 | 积分资源 radio | `label.el-radio:has-text("积分资源")` | ✅ 有效 |
| 11 | VIP专享资源 radio | `label.el-radio:has-text("VIP专享资源")` | ⚠️ 可能自动被选中，需矫正 |
| 12 | 积分下拉 | `input[placeholder="请选择"]` 第二个 | ✅ 有效（默认值 "0"） |
| 13 | 提交按钮 | `button.form-button.el-button--primary` | ✅ 有效 |
| 14 | 成功弹窗 | `[role="dialog"][aria-label*="恭喜"]` | ✅ 提交后出现 |
| 15 | 查看资源链接 | 弹窗内 `text=查看资源` | ✅ 点击后跳转上传明细页 |

## §4 核验清单（提交前逐项检查）

- [ ] 文件已上传（页面显示文件名 + "重新上传"按钮）
- [ ] 资源名称非空（textarea 有内容）
- [ ] 资源描述非空（至少 50 字）
- [ ] 标签 ≥1 个、≤5 个
- [ ] 分类已选（input 显示 "XX / XX"）
- [ ] **发布形式 = 积分资源**（不是 VIP！主动点击 radio 确认）
- [ ] 积分已确认（默认 0）
- [ ] **isRepeat=false**（通过 browser_network_request 查看 checkUploadSource 响应）
- [ ] 文件 ≤ 1000MB
- [ ] 文件不包含侵权内容、电子书、网盘链接
- [ ] 提交后有"恭喜完成上传"弹窗

## §5 发布后

### 5.1 查看上传明细
访问 https://mp.csdn.net/mp_download/manage/download/UpDetailed 查看：
- 审核状态（待审核 / 已通过 / 未通过）
- 下载次数、积分设置
- 编辑或删除资源

### 5.2 记录到 SESSION_STATE
```markdown
## CSDN 资源上传 — {名称}
- 资源 ID：{id}
- URL：https://download.csdn.net/download/deepseek23/{id}
- 状态：已通过 / 待审核
- 积分：0（免费）
- 来源：GitHub {项目名}（MIT 许可证）
```

## §6 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| v1.3 | 2026-07-06 | 新增 §0c 代理下载/Python 打包；新增 §0d 文件路径正斜杠格式说明；修复 Step 4 标签模板：browser_evaluate 无法传参，改为硬编码 val 变量；更新 Step 5 子类目选择器（`.el-cascader-menu:nth-child(2)`）；已知坑表新增路径格式/browser_evaluate 传参/GitHub 下载等 5 项；Agent-Reach 上传成功记录 |
| v1.2 | 2026-07-05 | 修复 Step 4 标签交互：ElAutocomplete input Playwright locator 不可达，改用 `page.evaluate` 原生 DOM 事件序列（setter+input+compositionend+Enter keydown/press/up+change+blur）；更新坐标表/已知坑；新增 shell_gpt 上传成功记录 |
| v1.1 | 2026-07-04 | 完善 §0b 包装增值策略；新增 Step 6a 强制积分资源；新增提交后弹窗检测；更新坐标表和已知坑 |
| v1.0 | 2026-07-04 | 初始版：完整上传流程 + GitHub 开源项目策略 + 坐标表 |


---

## 收尾核验（强制末步）

- 回看核心规则①（`~/.claude/CLAUDE.md` 永久原则第一条）：平台技术细节（DOM/API/坐标/SOP/已知问题）只进本技能文件，不进内置记忆；本次修正与复盘已直接编入本 SKILL.md，未写多余记忆文件。
- 反馈即修技能——若本次暴露新堵塞点/选择器/绕过方案，当场写入对应章节（留版本号），不依赖记忆回看。
