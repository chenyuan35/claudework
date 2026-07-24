---
name: dayu-publish
description: "大鱼号图文发布 v8.11 — 分节生成+只追加不覆盖+汉字计数拆段管线"
version: 8.11
platform: 大鱼号创作者平台（mp.dayu.com）
mode: 全自动
---

**启动铁律**：`mcp__playwright__browser_*`，禁用 preview_*。

## PHASE -1：选题与数据分析

**唯一方向**：消费决策叙事型（L1个人实测 + L2对比分析 + L3根因解读）
**标题三铁律**：有"我/你" + 对比/反转 + 信息缺口。24-28字。
**排版**：生成时自然段落每段2-4句，拆段后每段≤60汉字且≤3句、全文≥50段、每章加粗小标题、章间`<hr>`。

**选题规则**：
1. 必须是"我实测X个月发现Y"类型的个人消费实验
2. 覆盖高频率、低单价、容易被忽视的日常支出
3. 以下禁词表中命中的选题一律跳过

**禁词表**（含禁词的文章整篇熔断）：
- 健康：`医` `医保` `社保` `医疗` `医院` `看病` `治病` `药品` `医生` `健康` `养生` `美容` `护肤` `防晒` `防护` `保健品` `滋补` `中医`
- 财经：`涨价` `降价` `价格走势` `市场预测` `投资` `理财` `股票` `基金` `房价` `物价` `通胀`
- 品牌：`格力美的海尔TCL` `京东淘宝天猫拼多多` `搜索XX` `下载APP` `扫码` `立即购买` `购买链接` `点击链接` `关注公众号` `搜索口令`

**参考选题源**（基于已发布的28篇成功模式）：
```
- 外卖/快递/打车会员费 | 手机/宽带/视频订阅 | 超市/便利店价格差
- 水电煤/物业费隐形支出 | 退换货/售后成本 | 二手平台买卖对比
- 信用卡/积分/返现实际收益 | 宠物/育儿日常开销 | 日用品平替测试
- 维修vs换新成本对比 | 网购vs线下价格 | 拼单vs单独购买
```

每次选题从上述列表中选取未被覆盖的细分方向，确保不与已发文章（27篇）主题重复。

```javascript
// 用搜索框精确查当前标题是否已存在，比翻页可靠
var searchBox = document.querySelector('input[placeholder*="搜索"]');
if (searchBox) {
  var setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
  setter.call(searchBox, TITLE);  // TITLE 见变量表
  searchBox.dispatchEvent(new Event('input', {bubbles: true}));
  // 触发搜索（回车或旁边搜索按钮）
  var searchBtn = searchBox.closest('[class*=search]')?.querySelector('button') || document.querySelector('[class*=search] button');
  if (searchBtn) searchBtn.click();
}
// 等搜索结果加载后检查
setTimeout(function() {
  var results = document.querySelectorAll('h3');
  var matched = Array.from(results).some(h => h.textContent.trim().includes('TITLE'));
  if (matched) throw new Error('❌ 排重熔断：已有相同文章');
}, 2000);
```

**熔断条件**：搜索结果中出现标题包含当前 TITLE 的文章。

## PHASE 1：分节生成（分节→追加→统计→回滚→拆段管线）

**总量目标**：汉字（CJK统一表意字符）≥3000，总预算 3400汉字（底限3000+400安全余量）。
**汉字计数铁律**：所有字数统计必须用 `len(re.findall(r'[一-鿿豈-﫿]', text))`，**禁止** `len(str)` 或 Token 计数。

### P1.1 分节规划

根据选题拆成 3-5 章，每章设独立汉字预算：
- 总预算 = 3400汉字
- 每章预算 = ⌈总预算/N⌉，最后一章补足余量
- 每章设定单一主题，互不重叠
- 示例：3500汉字÷5章 = 700/章，最后一章补700+余量

**输出**：输出章节规划表到 `_dayu_sections.txt`，每行格式 `章标题|目标汉字数`

### P1.2 逐节生成（循环管线）

```python
# 伪代码逻辑——执行时按此顺序逐节操作
for chapter in sections:
    # 1. 生成该章节完整内容（含加粗小标题+自然段落+<hr>结尾）
    # 2. 追加写入 _dayu_article.html（用 'a' 模式，禁止 'w'）
    # 3. 立即统计该章汉字数
    # 4. 若 < 该章预算 → 只追加补充内容到本章末尾，不覆盖
    # 5. 若 ≥ 该章预算 → 进入下一章
```

**具体步骤**（每节循环）：

1. **生成单节**：根据「唯一方向」风格 + 本节主题，生成一节内容（500-800汉字）
2. **追加写入**：`python -c "open('_dayu_article.html','a',encoding='utf-8').write(open('/dev/stdin').read())"` 或 Write 工具追加模式
3. **汉字统计**：`python -c "import re; t=open('_dayu_article.html',encoding='utf-8').read(); print(len(re.findall(r'[一-鿿豈-﫿]',t)))"`
4. **预算检查**：该章汉字数 ≥ 本章目标 → 继续下一章；< 目标 → 仅追加该章内容，重新统计

**写作期间段落规则**：每段 2-4 句自然段落，**禁止拆成短段**，不插入 `<br>` 强制换行。

### P1.3 追加不覆盖铁律

| 操作 | 允许 | 禁止 |
|------|------|------|
| 写入 | `Write` → 文件末尾追加，或用 Python `open(file, 'a')` | `Write` 全文覆盖（'w'模式） |
| 修改 | 精确定位某章节范围，只替换该部分 | 生成全文后一次性写入 |
| 补充 | 在指定章节末尾追加新段落 | 删掉重写整章 |

**检查**：每次写入后执行 `python -c "import re; t=open('_dayu_article.html').read(); print('lines:',t.count(chr(10)),'chars:',len(re.findall(r'[一-鿿豈-﫿]',t)))"` 确认文件未被截断。

### P1.4 版本备份与回滚

**备份规则**（按顺序，循环覆盖）：

| 阶段 | 文件名 | 保留数 |
|------|--------|--------|
| 当前草稿 | `_dayu_article.html` | 1（当前） |
| 最近可用版本 | `_dayu_article_bak.html` | 1（写入前备份） |
| 每次合格版本 | `_dayu_article_v{N}.html` | N 递增，不覆盖 |
| 拆段前版本 | `_dayu_article_presplit.html` | 1（拆段前备份） |

**备份时机**：
- 每次追加写入前：`cp _dayu_article.html _dayu_article_bak.html`
- 每次汉字统计 ≥ 目标后：`cp _dayu_article.html _dayu_article_v1.html` → 下次 v2 → v3...
- 拆段执行前：`cp _dayu_article.html _dayu_article_presplit.html`

### P1.5 回滚机制（汉字下降 → 自动恢复）

```python
# 状态变量（每次修改前保存）
prev_count = 汉字数_before
new_count  = 汉字数_after
delta      = new_count - prev_count
consecutive_drops = 连续下降次数

# 判断逻辑
if delta < 0:
    consecutive_drops += 1
    if consecutive_drops >= 2:
        # 熔断：停止修改
        # 恢复：cp _dayu_article_bak.html _dayu_article.html
        # 输出: "连续2次下降，已回滚至_bak版本。仅保留追加操作。"
        # 禁止后续任何重写操作
else:
    consecutive_drops = 0  # 上升或持平则重置计数器
```

**触发条件**：
- 连续 2 次修改后汉字数下降 → **立即停止修改**
- **仅做一次回滚**：用 `_dayu_article_bak.html` 恢复
- 恢复后**只允许追加**到汉字最少章节，不再尝试任何重写
- 回滚后再次下降 → 直接熔断，使用 `_dayu_article_v{N}.html` 中最后一个合格版本

### P1.6 统一拆段（汉字≥3000后执行一次）

**时机**：PHASE 1 全部章节写满、汉字数 ≥ 3000 后执行。**正文完成前禁止拆段**。

**拆段规则**：
1. 拆段前备份：`cp _dayu_article.html _dayu_article_presplit.html`
2. 拆段只做段落拆分，**不删改任何内容**
3. 每段 ≤ 60汉字（以 `len(re.findall(r'[一-鿿豈-﫿]', para_text))` 计数）
4. 原有加粗小标题保持不变（不拆）
5. 章间 `<hr>` 分隔符保持不变
6. 拆段后验证汉字数：拆前汉字数 === 拆后汉字数

**拆段方法**：
```
每段汉字数 > 60 → 找到句号/问号/感叹号/分号处拆成两个 ≤60汉字段落
拆后段落数增加，但汉字总量不变
```

**拆段后统计**：
```bash
python -c "import re; t=open('_dayu_article.html').read(); print('汉字:', len(re.findall(r'[一-鿿豈-﫿]',t)), '段落:', t.count('</p>'))"
```

### P1.7 禁止进入重写循环

以下情况视为重写循环，必须硬停止：

| 触发模式 | 熔断动作 |
|----------|----------|
| 同一章节生成 → 统计不够 → 再次生成完整章节 → 又不够 | 直接使用 `_dayu_article_bak.html` 最后一个通过版本 |
| 拆段前反复调整段落内容增加汉字数 | 退回拆段前版本（presplit），只追加不重写 |
| 全篇汉字数在 2800-3000 间徘徊超过 3 轮 | 只做最后一章的追加补充，禁止修改前面章节 |
| 回滚后再次触发回滚 | 使用 `_dayu_article_v{N}.html` 最高版本的 HTML 直接发布 |

**终极规则**：任何情况下，只要存在一个汉字数 ≥ 3000 的 `_dayu_article_v{N}.html` 版本，就使用该版本发布——不得因"不够完美"继续修改导致字数下降。

### P1.8 PHASE 1 → §1 发布流程 衔接条件

```
PHASE 1 完成标志:
  □ 汉字数 ≥ 3000（len(re.findall(r'[一-鿿豈-﫿]',text))）
  □ 已完成统一拆段，每段 ≤ 60汉字
  □ 至少有 1 个合格版本备份（_dayu_article_v{N}.html）
  □ 三大禁区已逐条扫描通过
  □ 唯一方向三层独创已覆盖
  □ 未进入熔断状态

满足以上所有条件 → 继续 §1 发布流程
任一条件不满足 → 返回对应步骤修正，禁止跳过
```

## 坐标基准（坐标速查表，1440x900，左面板display:block）

| 操作 | 选择器 | 动作 |
|------|--------|------|
| 标题输入 | `input[placeholder*="标题"]` | `evaluate: nativeInputValueSetter + input事件` |
| 发表按钮 | `button:has-text("发表")` | `browser_click` |
| 确认发表 | `button:has-text("确认发表")` | `browser_click` |
| 信息来源 | `input[value="个人观点"]` | `evaluate: radio.click()` |
| 切单封面tab | `button:has-text("单封面")` | `browser_run_code_unsafe: force:true` |
| 从正文选择封面 | `button:has-text("从正文中选择")` | `browser_run_code_unsafe: force:true` |
| overlay面板 | `.widgets-pop.w-scrollbar` | 等待可见 |
| overlay选图 | overlay内第1张img | `evaluate: imgs[0].click()` |
| overlay下一步 | `button:has-text("下一步")` | `browser_click` |
| 裁剪保存 | `button:has-text("保存") >> visible=true` | `browser_click` |

**左面板解锁**（React 页面默认收起，必须解锁才能操作）：  
`evaluate: var p=document.querySelector('.widgets-panel'); if(p) p.style.display='block';`

**封面容错**：如果React合成事件无法触发覆盖面板（widgets-pop不出现），直接跳过封面设置。系统会自动使用正文第一张图作为默认封面。不影响发布。

## 1 发布流程（唯一主管道，顺序固定）

### §1.0 变量设置（每篇仅改此处）
```
TITLE    = "外卖会员到底省不省钱？我实测了一个月，结果和你想的不一样"
ARTICLE  = "_dayu_article.html"
IMAGE1   = "_dayu_body1.png"
IMAGE2   = "_dayu_body2.png"
URL1     = "https://mp.dayu.com/dayu/image?t=..."  /* §1.3 返回后填入 */
URL2     = "https://mp.dayu.com/dayu/image?t=..."  /* §1.3 返回后填入 */
CHECK    = "外卖会员"
```

### §1.1 页面准备
**工具**：`browser_evaluate`  
```javascript
/* 解锁左面板 && 设标题，一条evaluate完成 */
var p = document.querySelector('.widgets-panel');
if (p) p.style.display = 'block';
var input = document.querySelector('input[placeholder*="标题"]');
var setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
setter.call(input, TITLE);  /* 见 §0 变量表 */
input.dispatchEvent(new Event('input', {bubbles: true}));
input.value;
```
**验证**：返回标题字符串

### §1.2 文字注入
**工具**：`python` + `browser_run_code_unsafe`  
```bash
python -c "
import base64, pathlib
b64 = base64.b64encode(pathlib.Path('_dayu_article.html').read_bytes()).decode()
js = 'async (page) => {' + chr(10)
js += '  var b = \"' + b64 + '\";' + chr(10)
js += '  var r = await page.evaluate(function(b) {' + chr(10)
js += '    var bin = atob(b), b2 = new Uint8Array(bin.length);' + chr(10)
js += '    for (var i=0;i<bin.length;i++) b2[i]=bin.charCodeAt(i);' + chr(10)
js += '    var h = new TextDecoder(\"utf-8\").decode(b2);' + chr(10)
js += '    UE.instants[\"ueditorInstant0\"].setContent(h);' + chr(10)
js += '    var t = UE.instants[\"ueditorInstant0\"].getPlainTxt();' + chr(10)
js += '    var m = /ä½|æ²¡|æ¯|è¿Ù|ç§/.test(t);' + chr(10)
js += '    return \"chars:\"+t.length+\" moji:\"+m;' + chr(10)
js += '  }, b); return r;' + chr(10)
js += '}'
pathlib.Path('_dayu_set_content.js').write_text(js, encoding='utf-8')
print('OK')
"
```
**执行**：`browser_run_code_unsafe({filename: '_dayu_set_content.js'})`  
**验证**：返回 `chars>=3000 moji:false`

### §1.3 Agens 配图生图
**工具**：`bash`（Agens API → PIL裁切 → 生成三张图）

**先删旧图**（防 Agens 失败后误用上篇旧图）：
```bash
rm -f _dayu_body1.png _dayu_body2.png _dayu_cover.png _dayu_prompts.txt
```
若 Agens 后续失败 → 文件不存在 → §1.4上传直接报错 → 熔断，不会错传旧图。

**提取prompt**（自动从正文各章节提取素材，非硬编码）：
```bash
python -c "
import re
t = open('_dayu_article.html', encoding='utf-8').read()
chs = t.split('<hr>')
for i,ch in enumerate(chs):
    hz = re.findall(r'[一-鿿豈-﫿，。！？、：；]', ch)
    snippet = ''.join(hz)[:100]
    if len(snippet) > 20: print(f'prompt{i+1}|{snippet}')
" | tee _dayu_prompts.txt
```
提取逻辑：每章取前100汉字作为 prompt 素材，`prompt1`=封面(第一章)、`prompt2`=正文图1(第二章数据)、`prompt3`=正文图2(第三章)

**Agens生图**（~40s/张，可并行）：
```bash
# 正文图1(第2章数据)
python .claude/skills/agnes-image/scripts/generate.py \
  --prompt "实拍风格，明亮温暖，$(sed -n '2p' _dayu_prompts.txt | cut -d'|' -f2)" \
  --out _dayu_body1.png --size 1200x675
# 正文图2(第3章)  
python .claude/skills/agnes-image/scripts/generate.py \
  --prompt "实拍风格，明亮温暖，$(sed -n '3p' _dayu_prompts.txt | cut -d'|' -f2)" \
  --out _dayu_body2.png --size 1200x675
# 封面图(第1章)
python .claude/skills/agnes-image/scripts/generate.py \
  --prompt "实拍风格，明亮温暖，$(sed -n '1p' _dayu_prompts.txt | cut -d'|' -f2)" \
  --out _dayu_cover.png --size 1200x675
```

**PIL裁切验证**：
```bash
python -c "
from PIL import Image
for f in ['_dayu_body1.png','_dayu_body2.png','_dayu_cover.png']:
    try:
        img = Image.open(f)
        if img.size != (1200,675): img = img.crop((0,0,1200,675)).resize((1200,675)); img.save(f,quality=70)
        print(f'{f}: {img.size} OK')
    except Exception as e: print(f'{f}: ERROR {e}')
"
```

### §1.4 图片上传
**工具**：`python` + `browser_run_code_unsafe`  
每张图执行一次，文件名逐一替换  
```bash
python -c "
import base64, pathlib
f = IMAGE1  /* 见 §0 变量表 */
b64 = base64.b64encode(pathlib.Path(f).read_bytes()).decode()
js = 'async (page) => {' + chr(10)
js += '  var b = \"' + b64 + '\";' + chr(10)
js += '  var r = await page.evaluate(function(b) {' + chr(10)
js += '    var d = Uint8Array.from(atob(b),c=>c.charCodeAt(0));' + chr(10)
js += '    var bl = new Blob([d], {type:\"image/png\"});' + chr(10)
js += '    return new Promise(function(r) {' + chr(10)
js += '      var f = new FormData(); f.append(\"upfile\",bl,\"image.png\");' + chr(10)
js += '      var x = new XMLHttpRequest();' + chr(10)
js += '      x.open(\"POST\",\"/ueditor/controller?action=uploadimage\");' + chr(10)
js += '      x.setRequestHeader(\"X-Requested-With\",\"XMLHttpRequest\");' + chr(10)
js += '      x.onload=function(){r(JSON.parse(x.responseText).url)};' + chr(10)
js += '      x.onerror=function(){r(\"ERR:\"+x.statusText)};' + chr(10)
js += '      x.send(f);' + chr(10)
js += '    });' + chr(10)
js += '  },b); return r;' + chr(10)
js += '}'
pathlib.Path('_dayu_upload.js').write_text(js, encoding='utf-8')
print('OK')
"
```
**执行**：`browser_run_code_unsafe({filename: '_dayu_upload.js'})`  
**返回**：图片URL（改 `IMAGE1` → `IMAGE2` 再执行一次）
**注意**：返回的URL替换到 §1.4 的 `URL1`/`URL2`

### §1.5 DOM插入正文
**工具**：`browser_evaluate`  
```javascript
var body = document.querySelector('#ueditor_0').contentDocument.body;
var ps = Array.from(body.querySelectorAll('p'));
var p1 = document.createElement('p'); p1.style.textAlign = 'center';
p1.innerHTML = '<img src="' + URL1 + '" width="600"/>';
ps[Math.floor(ps.length*0.4)].after(p1);
ps = Array.from(body.querySelectorAll('p'));
var p2 = document.createElement('p'); p2.style.textAlign = 'center';
p2.innerHTML = '<img src="URL2" width="600"/>';
ps[Math.floor(ps.length*0.65)].after(p2);
/* 结构验证 */
var imgs = body.querySelectorAll('img'), errs = [];
imgs.forEach(function(img) {
  if (!img.closest('p')) errs.push('img not in p');
  else if ((img.closest('p').textContent||'').replace(img.alt||'','').replace(/\\s/g,'').length > 10) errs.push('text+img mixed');
});
if (body.firstElementChild.querySelector('img')) errs.push('first is img');
errs.length ? 'FAIL: '+JSON.stringify(errs) : 'OK imgs:'+imgs.length;
```

### §1.6 封面设置
**工具**：`browser_evaluate`（React不响应browser_click，必须用PointerEvent）  
```javascript
/* step 1: 切单封面tab */
var btns = document.querySelectorAll('button');
for (var b of btns) { if (b.textContent.trim() === '单封面') {
  b.dispatchEvent(new PointerEvent('pointerdown', {bubbles:true, cancelable:true}));
  b.dispatchEvent(new PointerEvent('pointerup', {bubbles:true, cancelable:true}));
  b.dispatchEvent(new MouseEvent('click', {bubbles:true, cancelable:true, view:window})); break;
}}
/* step 2: 从正文中选择 */
for (var b of document.querySelectorAll('button.w-btn.w-btn_primary')) { if (b.textContent.trim() === '从正文中选择') {
  b.dispatchEvent(new PointerEvent('pointerdown', {bubbles:true, cancelable:true}));
  b.dispatchEvent(new PointerEvent('pointerup', {bubbles:true, cancelable:true}));
  b.dispatchEvent(new MouseEvent('click', {bubbles:true, cancelable:true, view:window})); break;
}}
/* 等待弹出框 */
new Promise(r => setTimeout(() => {
  /* step 3: 选第一张图 */
  var popup = document.querySelector('.widgets-pop');
  if (!popup) return r('no popup');
  var imgs = popup.querySelectorAll('img');
  if (!imgs.length) return r('no imgs');
  imgs[0].dispatchEvent(new PointerEvent('pointerdown', {bubbles:true, cancelable:true}));
  imgs[0].dispatchEvent(new PointerEvent('pointerup', {bubbles:true, cancelable:true}));
  imgs[0].dispatchEvent(new MouseEvent('click', {bubbles:true, cancelable:true, view:window}));
  /* step 4: 下一步 */
  Array.from(popup.querySelectorAll('button')).filter(b => b.textContent.trim() === '下一步')[0]?.dispatchEvent(new MouseEvent('click', {bubbles:true, cancelable:true, view:window}));
  /* step 5: 保存 */
  Array.from(popup.querySelectorAll('button')).filter(b => b.textContent.trim() === '保存')[0]?.dispatchEvent(new MouseEvent('click', {bubbles:true, cancelable:true, view:window}));
  r('cover done');
}, 1000));
```
**验证**：`evaluate: document.querySelectorAll('[class*=cover] img[src*="dayu"]').length >= 1`

### §1.7 版面验证（发布前必检）
**工具**：`browser_evaluate` → `browser_take_screenshot`

```javascript
/* 数字检验：段落≥50、图片≥2、首非图、无混排、图片分散 */
var body = document.querySelector('#ueditor_0').contentDocument.body;
var ps = body.querySelectorAll('p'), imgs = body.querySelectorAll('img');
var pass1 = ps.length >= 50, pass2 = imgs.length >= 2;
var pass3 = !body.firstElementChild?.querySelector('img');
var pass4 = true;
imgs.forEach(function(i) { var p=i.closest('p'); if(p&&(p.textContent||'').replace(i.alt||'','').replace(/\\s/g,'').length>10) pass4=false; });
var fp = Array.from(ps).indexOf(imgs[0]?.closest('p'));
var lp = Array.from(ps).indexOf(imgs[1]?.closest('p'));
var pass5 = fp < ps.length/2 && lp > ps.length/3;
return {段落:pass1, 图片数:pass2, 首非图:pass3, 无混排:pass4, 分散:pass5};
```
**截图存档**：`browser_take_screenshot` → 目视检验排版  
**卡关**：任一检验不通过 → 熔断不发布

### §1.8 发布
**工具**：`browser_evaluate`（选信息来源）→ `browser_click`（React听原生click）  
```javascript
/* 选"个人观点" */
window.scrollTo(0, document.body.scrollHeight);
var radios = document.querySelectorAll('input[value="个人观点"]');
if (radios.length) radios[radios.length-1].click();
```
**点击"发表"**：`browser_click button.w-btn.w-btn_primary:has-text("发表")`  
**等待 3秒**  
**点击"确认发表"**：`browser_click button:has-text("确认发表")`  
**等待 5秒** → URL 自动跳转 `/dashboard/contents`

### §1.9 结果验证
**工具**：`browser_evaluate`  
```javascript
var h3s = Array.from(document.querySelectorAll('h3')).map(h => h.textContent.trim());
h3s.some(t => t.includes(CHECK));  /* CHECK 见 §0 变量表 */
```
**验证**：返回 `true`

### 清理（可选，节省磁盘空间）
```bash
rm -f _dayu_body1.png _dayu_body2.png _dayu_cover.png _dayu_prompts.txt _dayu_upload_*.js _dayu_set_content.js
```
保护机制已在 §1.3 开头：生图前先删旧文件，失败即报错，不会把旧图传上去。

## 2 质量门
**内容**：汉字≥3000（len(re.findall(r'[一-鿿豈-﫿]')) / 段落≥50 / 每段≤60汉字且≤3句 / 每章加粗小标题 / 章间`<hr>` / 无乱码
**标题**：5-50字 / 含"我/你"+对比/反转+信息缺口 / 无夸张/强迫/很多人不知道类
**禁区**：逐条扫描三大禁词表 / 无品牌名平台名推广语
**独创**：L1+L2全文覆盖 / L3至少1处
**配图**：正文>=2张 / 封面已设（`[class*=cover] img[src*="dayu"]` 确认实际图非图标） / 结构验证全部通过 / 无图片切断段落
**信用分**：80生死线，有任何违规风险 -> 不发布

**发布门**：所有质量门验证通过后才发布，任一不满足熔断。
