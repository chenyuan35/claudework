---
name: csdn-publish
description: CSDN「deepseek23」文章发布技能。主管道：选题前准备→生图(后台)→写正文→编辑注入→CDN图→封面标签→摘要→发布。v3.31 — 减法重构
---

## §0 主管道（顺序不可颠倒）

每次 `/csdn-publish` 必须按下列 5 阶段严格顺序执行。任一阶段失败且重试一次后仍失败即熔断。

| 阶段 | 步骤 | 墙钟预算 | 熔断条件 |
|------|------|---------|---------|
| **I 选题** | ①清工作区→②额度检查→③扫已有文章→④热点头条→⑤选话题去重→⑥预算配置 | ≤3min | 额度用完/无合适选题/标题重复 |
| **II 生图** | ⑦写分析文件→⑧后台启动 _csdn_gen_img.py（不阻塞） | ~0s（并行） | 双图缺失且重试仍失败→A2熔断 |
| **III 写作** | ⑨写正文 HTML（与生图并行）→⑩插入 `__BODY_IMG_PLACEHOLDER__` | 50-120s | 正文纯文本<5000→追加到字符数最低的章节，不重写全篇 |
| **IV 注入** | ⑪navigate编辑器→⑫填标题→⑬setData正文→⑭CDN上传→⑮proxy清理→⑯封面设置→⑰标签→⑱摘要 | ≤5min | §5 坐标表任一验收不通过 |
| **V 发布** | ⑲§3 红线自查→⑳dispatchEvent 发布博客 | ≤30s | §3 任一不通过 |

**发布后固定动作**：记录 PUBLISH_LOG.md → 清理临时文件 → 更新字数比率。

---

## §0a 选题准备（阶段 I）

### 步骤 ①：清工作区
```bash
python _csdn_prep.py clean
```

### 步骤 ②+③：额度检查 + 扫已有文章（同一 navigate）
```bash
# navigate → https://blog.csdn.net/deepseek23
```
```javascript
// 1. 额度检查
document.body.textContent.includes('已达发文上限')
// true → 熔断退出；false → 继续
// 2. 采集文章标题（翻页至无更多）
() => {
  const results = [];
  const links = document.querySelectorAll('a[href*="article/details"]');
  links.forEach(a => { const t = a.textContent.trim(); if (t.length > 5) results.push(t); });
  return JSON.stringify(results, null, 2);
}
```

### 步骤 ④：扫热点（Exa 搜索）
使用 Exa 搜索全球 AI/LLM/MCP 领域最新话题（替换日期为当日）：
```
"AI tools trending <month> <year>"
"LLM latest news <month> <year>"
"site:csdn.net AI 大模型 <month> <year>"
```
→ 选出 1 个话题：全球关注度高且 CSDN 不饱和（3 篇以上高阅读文章即为饱和）。执行者不犹豫超过 30 秒。

### 步骤 ⑤：去重检查
- 标题不在步骤 ③ 的文章列表中
- 与账号最近 2 篇不重复话题
- 不满足任一 → 换题

### 步骤 ⑥：字数预算
```bash
python _csdn_prep.py budget
```
→ 使用输出的校正后预算数（如 6700）作为分段目标。

---

## §0b 写作规范（写作时遵守）

### 结构轮换
**连续两篇必须使用不同结构**，记录在 PUBLISH_LOG.md：
- **A** 问题解决式：痛点→尝试→解决→感悟
- **B** 对比辩论式：立场→反方观点→数据→结论
- **C** 叙事时间线式：起因→过程→踩坑→结果
- **D** 切片拆解式：入口→逐层拆解→关键瓶颈→最佳实践
- **E** 突发场景式：偶然发现→尝鲜→深度使用→值得/不值得

### 排版铁律（段落 ≤ 180 字，超 180 字数 ≤ 3）
- 每个段落只说 1-2 个事实，超 180 字必须审视（超 180 字数 ≤ 3）
- 关键数字、日期、百分比、工具名 → `<strong>` 加粗
- 对比数据 → `<table>`（不用段落描述）
- 话题切换 → `<hr>` 分割线
- 强观点/转折 → 独立成单句段
- bullet 要点 → `<ul>` 列表（项 ≤ 20 字）
- 少用 H2，用 H3 做扁平层级（标题 H1 → H3 分段）

### 禁止
- ❌ 教科书定义开头（"什么是 XXX？"）
- ❌ "第一、第二、第三"大纲式列表
- ❌ "简单说""总的来说""显而易见"等 AI 过渡词
- ❌ "总结"/"结语"章节
- ❌ "欢迎关注"等模板结尾
- ❌ 完美段落过渡（段间留一点断裂感）

### 标题规则
标题必须包含态度词（"最狠""必学""封神"等）。

### 代码块
每篇至少 1 个可运行的代码块，放在概念解释段落之后。

### 图像布局
- 先写完整正文 HTML，不含任何 `<img>` 标签
- 在图片应放置处插入文本标记 `__BODY_IMG_PLACEHOLDER__`
- 该标记必须落在文章纯文字长度的 **35%-60% 区间**
- 成文后执行：`python -c "import re;html=open('article_csdn.html',encoding='utf-8').read();pos=html.index('__BODY_IMG_PLACEHOLDER__');r=pos/len(html);assert 0.35<=r<=0.6,f'{r*100:.0f}%'"`

---

## §1 图像生成（阶段 II）

### 分析文件
写 `_csdn_prompt_analysis.json`，包含 cover（核心主题/隐喻/色调/风格/色板/构图/情绪）和 body（段落上下文/概念类型/构图/风格/色板/情绪）。封面与正文在 style/palette/composition/mood 四个维度全部不同，且与上篇至少 2 维度不同（通过 `_csdn_last_style.txt` 检查）。

风格/色板/构图/情绪从轮盘选（轮盘列于文件末尾附录），每次选不同组合。

### 启动生图（后台不阻塞）
分析文件写完**立即**执行，不做任何审查：
```bash
# Bash run_in_background: true
python _csdn_gen_img.py --analysis _csdn_prompt_analysis.json
```

### 双图验证锁（生图结束后执行）
```bash
ls -la _csdn_cover.jpg _csdn_body.jpg
# 缺图 → 单独重跑；再次失败 → A2 熔断（本轮不发）
```

### 图片压缩 + HTTP 服务
```bash
python _csdn_prep.py compress
python img_server.py &
curl -s -o /dev/null -w "%{http_code}" http://localhost:18991/_csdn_cover_small.jpg  # 必须 200
```

---

## §1a 写作正文（阶段 III，与生图并行）

1. 确认选题（§0a 步骤 ⑤）和字数预算（§0a 步骤 ⑥）
2. 按 §0b 规范写 HTML 正文，逐段校验字数：
   - 破题段 400-600 字 → 主体每节 600-1200 字 → 结尾 300-500 字
   - 写完每节立即 `python -c "import re;t=re.sub(r'<[^>]+>','',open('article_csdn.html',encoding='utf-8').read());t=re.sub(r'\s+','',t);print(len(t))"`，不足则本节内补
3. 插入 `__BODY_IMG_PLACEHOLDER__` 并执行 35%-60% 位置检测
4. 终验：纯文本 ≥ 目标字数（取自步骤⑥预算）。不够→只向字符数最低的章节追加内容，禁止重写已有正文
5. **编辑审稿门（字数达标后执行）**：通读全文检查逻辑通顺性和段落衔接。检查重点：段间过渡自然度、观点连贯性、表述清晰度、有无逻辑断裂。发现问题→只修改对应章节内容，禁止整篇重写。编辑期间总字数允许在目标值 ±10% 范围内浮动。修改完成后进入 §1b。

---

## §1b 图片错误熔断

| 错误 | 处理 |
|------|------|
| `503 system_memory_overloaded` | 等 10s 重试 1 次，仍失败 → A2 熔断 |
| `503 model_not_found` | 改模型 `agnes-image-2.1`（去 `-flash`）重试，仍失败 → A2 熔断 |
| **A2 熔断** | 本轮不发，不复用旧图、不网络找图、不用 data URL |

---

## §2 编辑器操作（阶段 IV）

navigate → `https://mp.csdn.net/mp_blog/creation/editor`（不等就绪，CKEditor 检测在正文注入前执行）。然后按 [§5 坐标表](#5-坐标表playwright-mcp-精确指令) 逐条执行（#0→#1→#2→#2b→#2c→#2d→#3→#4→#10→#11），无分支。

编号映射（§5 → §0 主管道）：#0=预检 / #1=⑫填标题 / #2=⑬setData / #2b=⑭CDN上传 / #2c=⑮proxy清理 / #2d=验收 / #3=⑯封面 / #4=⑰标签 / #10=⑱摘要 / #11=⑳发布。

---

## §3 红线自查（阶段 V 发布前，任一不通过禁止点击）

- [ ] 封面预览图 src 以 https 开头（`.container-coverimage-box .preview`）
- [ ] 至少 1 个标签已设（`input[name="tags"]` 不为空）
- [ ] 正文含 CDN 图片（`i-blog.csdnimg.cn/direct/`），且 `<img` 计数 === 1
- [ ] `<img` 在 35%-60% 位置（纯文字计，非前 30% 非后 30%）
- [ ] 封面/正文的 style/palette/composition/mood 4 维度全部不同
- [ ] 本次组合与上篇至少 2 维度不同
- [ ] 摘要长度 ≥ 200
- [ ] 正文纯文本 ≥ 5000 字符
- [ ] 无段落超 180 字（超的数量 ≤ 3）

---

## §4 已知坑表（复用时参考，不新增分支）

| # | 现象 | 当前方案 | 日期 |
|---|------|---------|------|
| 1 | 正文图重复（IMG 超出 1 个）| strip 所有 `<img>` 后再替换 `__BODY_IMG_PLACEHOLDER__` | 7.13 |
| 2 | CKEditor 出现 img-home proxy 占位图 | 通用正则 `<img[^>]*src="https://img-home\.csdnimg\.cn/...` → remove | 7.14 |
| 3 | 封面裁剪确认卡死 | evaluate `.vicp-operate-btn.click()` 绕过 overlay，不用 Playwright click | 7.17 |
| 4 | 标签面板不可见 | nativeInputValueSetter 直接赋值隐藏 input，不走面板交互 | 7.21 |
| 5 | 原图 >1MB 上传超慢 | PIL resize + q=60 压缩到 <100KB 再上传 | 7.08 |
| 6 | 编辑器 SPA 崩溃（操作超 30 次）| 操作计数上限 30 次；页面死亡则放弃 | 7.17 |
| 7 | 发布按钮 Vue 不响应 | `removeAttribute('aria-disabled')` + `dispatchEvent(MouseEvent('click'))`，不用 browser_click | 7.24 |
| 8 | CDN 上传弹窗按钮为"选择图片"而非"从本地上传" | Click "选择图片" → browser_file_upload → 确认裁剪(.vicp-operate-btn) → 从 getData 取 CDN URL → strip img 后替换占位符 | 7.24 |
| 9 | AI 提取摘要返回"无法回答" | 取消弹窗后用 browser_fill_form 手动写入摘要，目标 textarea[placeholder*="摘要"] | 7.24 |
| 10 | 摘要过长会覆盖标题框 | 设摘要后必须验证标题框 #txtTitle 的 value 正确 | 7.24 |

### 已合并/过期（被稳定方案替代不再单独记录）
- ~CDN 上传被安全策略拦截~ → #8 浏览器文件选择器方案替代
- ~封面 input 选择器二义性~ → §5 #3 img-selection-item 方案稳定

---

## §5 坐标表（Playwright MCP 精确指令）

每行包含精确的 evaluate 代码，按 # 顺序执行，无分支。

| # | 步骤 | evaluate 代码 | 验收条件 |
|---|------|-------------|---------|
| 0 | 预检（额度+CKEditor就绪） | `async () => { if(document.body.textContent.includes('已达发文上限')) throw new Error('已达发文上限'); for(let i=0;i<40;i++){ if(typeof CKEDITOR!=='undefined' && CKEDITOR.instances && CKEDITOR.instances.editor) return true; await new Promise(r => setTimeout(r, 500)); } throw new Error('CKEditor 加载超时'); }` | CKEDITOR.instances.editor 存在 |
| 1 | 填标题 #txtTitle | `() => { const t=document.querySelector('#txtTitle'); t.value='标题'; t.dispatchEvent(new Event('input',{bubbles:true})); }` | value === 标题 |
| 2 | setData 正文（从 HTTP 服务 fetch） | `async () => { const r=await fetch('http://localhost:18991/article_csdn.html'); const h=await r.text(); CKEDITOR.instances.editor.setData(h); CKEDITOR.instances.editor.fire('change'); return CKEDITOR.instances.editor.getData().length; }` | getData().length > 0 |
| 2b | CDN 上传（→§2b 详细步骤） | 见下方 §2b 多步序列 | `<img` 计数 === 1 |
| 2c | 清除 proxy 图 | `() => { let h=CKEDITOR.instances.editor.getData(); h=h.replace(/<img[^>]*src="https:\/\/img-home\.csdnimg\.cn\/images\/[^"]+\?origin_url=[^">]*"[^>]*\/?>/gi,''); CKEDITOR.instances.editor.setData(h); CKEDITOR.instances.editor.fire('change'); }` | getData() 无 img-home URL |
| 2d | 验证图片状态 | `() => { const h=CKEDITOR.instances.editor.getData(); return { proxy:/img-home\.csdnimg\.cn/.test(h), cdn: (h.match(/i-blog\.csdnimg\.cn\/direct\/[^"']+/)?.[0]||'') }; }` | proxy=false 且 cdn 非空 |
| 3 | 设置封面 | `() => { const i=document.querySelector('.img-selection-item img[src*=\"csdnimg.cn/direct\"]'); if(!i) return 'no_img'; i.closest('.img-selection-item')?.click(); return 'clicked'; }` → wait 3s → `() => { const c=document.querySelector('.vicp-operate-btn'); if(c){c.click();return 'crop';} return 'no_crop'; }` → 若 crop 仍在：`() => { const d=document.querySelector('.vicp-close'); if(d)d.click(); }` | `.container-coverimage-box .preview` 的 src 以 http 开头且 >50 字符 |
| 4 | 设标签 | `() => { const s=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set; s.call(document.querySelector('input[name=\"tags\"]'),'标签1,标签2'); document.querySelector('input[name=\"tags\"]').dispatchEvent(new Event('input',{bubbles:true})); }` | `input[name="tags"]` 不为空 |
| 10 | 提取摘要（AI 固定流程） | `() => { const btn=Array.from(document.querySelectorAll('button')).find(x=>x.textContent.trim()==='AI提取摘要'); if(btn){btn.click();return 'clicked';} return 'not_found'; }` → wait 5s → 验证 textarea.value.length。若 < 200 则 `() => { const btn=document.querySelector('.cke_dialog .el-dialog .ai-extract-btn, button:contains(\"AI提取摘要\")'); if(btn)btn.click(); }` 重试 1 次 → 仍 < 200 则熔断（本轮摘要为空放弃发布） | 摘要 textarea.value.length ≥ 200 |
| 10b | 验证标题未被覆盖 | `() => { const t=document.querySelector('#txtTitle'); return t?.value?.length > 0 && t.value.length <= 100; }` | title 长度在 5-100 范围 |
| 11 | **发布博客** | `() => { const b=Array.from(document.querySelectorAll('button')).find(x=>x.textContent.trim()==='发布博客'); if(!b) return 'not_found'; b.removeAttribute('aria-disabled'); b.dispatchEvent(new MouseEvent('click',{bubbles:true,cancelable:true})); return 'ok'; }` | URL 含 /creation/success/ |

### §2b — CDN 上传详细步骤（2026-07-24 验证）

| 序号 | 操作 | 工具 | 命令 |
|------|------|------|------|
| ① | execImageUpload 打开弹窗 | browser_evaluate | `function: "() => { CKEDITOR.instances.editor.execCommand('execImageUpload'); }"` |
| ② | 点"选择图片"打开文件选择器 | browser_click | `target: "text=选择图片"` |
| ③ | 选择压缩图（弹窗变为 file chooser） | browser_file_upload | `paths: ["_csdn_body_small.jpg"]` |
| ④ | 等裁剪界面出现 | browser_wait_for | `time: 3` |
| ⑤ | 确认裁剪上传 | browser_evaluate | `function: "() => { const b=document.querySelector('.vicp-operate-btn'); if(b) b.click(); }"` |
| ⑥ | 等 CDN 上传完成 | browser_wait_for | `time: 10` |
| ⑦ | 获取 CDN URL + 关窗 | browser_evaluate | `function: "() => { document.querySelectorAll('.cke_dialog,.el-overlay,.vicp-close').forEach(el=>el.remove()); const h=CKEDITOR.instances.editor.getData(); const m=h.match(/i-blog\\.csdnimg\\.cn\\/direct\\/[^\"']+/); return m ? 'https://'+m[0] : null; }"` |
| ⑧ | 重新注入完整正文 + 替换占位符 | browser_evaluate | `function: async () => { const resp=await fetch('http://localhost:18991/article_csdn.html'); const full=await resp.text(); const cdn='CDN_URL'; let h=full.replace(/<img[^>]*src="[^"]*"[^>]*\/?>/gi,''); h=h.replace('__BODY_IMG_PLACEHOLDER__','<img src=\"'+cdn+'\" style=\"width:100%;max-width:800px;border:1px solid #e0e0e0;border-radius:8px;\" />'); CKEDITOR.instances.editor.setData(h); CKEDITOR.instances.editor.fire('change'); return (CKEDITOR.instances.editor.getData().match(/<img/gi)||[]).length===1; }"` |
| ⑨ | 验证图片 | browser_evaluate | `function: "() => { const h=CKEDITOR.instances.editor.getData(); return { imgCount:(h.match(/<img/gi)||[]).length, cdn:(h.match(/i-blog\.csdnimg\.cn\/direct\/[^"']+/)?.[0]||'none') } }"` |

### §2c — 封面设置详细步骤

| 序号 | 操作 | 工具 | 命令 |
|------|------|------|------|
| ① | 点 CDN 图设为封面 | browser_evaluate | `function: "() => { const i=document.querySelector('.img-selection-item img[src*=\"csdnimg.cn/direct\"]'); if(!i) return 'no_cdn'; i.closest('.img-selection-item')?.click(); return 'ok'; }"` |
|   | ⏳ 等裁剪界面 | browser_wait_for | `time: 3` |
| ② | 点击"确认上传" | browser_evaluate | `function: "() => { const b=document.querySelector('.vicp-operate-btn'); if(b) { b.click(); return 'cropped'; } return 'no_crop'; }"` |
| ③ | 若未关闭则点 x | browser_evaluate | `function: "() => { const c=document.querySelector('.vicp-close'); if(c) c.click(); }"` |
|   | 验收 | browser_evaluate | `function: "() => { const p=document.querySelector('.container-coverimage-box .preview'); return !!(p?.src?.startsWith('http') && p.src.length > 50); }"` |

---

## §6 发布后

### 6.1 记录
追加到 [PUBLISH_LOG.md](PUBLISH_LOG.md)。

### 6.2 更新字数比率（必须先于清理执行）
```python
python -c "import re,os;html=open('article_csdn.html',encoding='utf-8').read();text=re.sub(r'<[^>]+>','',html);text=re.sub(r'\s+','',text);actual=len(text);budget=7000;new=actual/budget;f='_csdn_budget_ratio.txt';p=float(open(f).read().strip())if os.path.isfile(f)else new;s=p*0.7+new*0.3;open(f,'w').write(f'{s:.4f}');print(f'ratio:{new:.4f} factor:{1/max(s,0.1):.2f}')"
```

### 6.3 清理
```bash
python _csdn_prep.py clean
```
保留 `_csdn_last_style.txt` / `_csdn_gen_img.py` / `_csdn_prep.py` / `_csdn_budget_ratio.txt`。

### 6.4 复盘
按 CLAUDE.md 技能修复标准流程执行。复盘唯一产出是 diff，不产复盘章节。

---

## 附录 A：风格轮盘

| 维度 | 选项 |
|------|------|
| **风格** | 产品渲染 / 概念艺术 / 概念图解 / 水彩手绘 / 赛博 / 中国水墨 / 浮世绘 / 3D卡通 / 极简线稿 / 拼贴风 / 几何抽象 / 玻璃质感 / 科幻杂志 / 像素风 / 复古海报 |
| **色板** | 蓝橙互补 / 紫金奢华 / 绿黑白冷淡 / 红蓝赛博 / 莫兰迪低饱和 / 黑白单色 / 粉蓝渐变 / 暖黄棕复古 / 霓虹紫绿 / 大地色系 |
| **构图** | 中心主体 / 左文右图 / 对角线分割 / 俯瞰俯视 / 第一人称 / 微距特写 / S型引导线 / 框架构图 / 对称分割 / 留白极简 |
| **情绪** | 兴奋惊喜 / 冷静专业 / 危机警示 / 温暖接地气 / 未来感 / 怀旧 / 混乱复杂 / 通透清晰 |

## 附录 B：OP-0b — _csdn_gen_img.py（代码见技能目录同名文件）
