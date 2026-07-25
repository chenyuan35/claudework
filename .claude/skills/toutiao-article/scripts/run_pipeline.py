"""
头条号自动发布 - 统一编排入口 (v8.0)
按 Phase 0→7 真实调用全部模块；SKILL.md 只调用此入口。
读取4个YAML配置，输出浏览器操作指令到 runtime/_browser_task.json。
"""
import sys, os, json, subprocess, tempfile, shutil
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.lib.config_loader import get_thresholds, get_selectors, get_content_policy, get_services
from scripts.state import (
    load_state, save_state, update_state, reset_to_idle, article_hash,
    load_history, append_history, load_metrics, save_metrics,
    detect_recovery, ensure_runtime_dirs, cleanup_temp,
)
from scripts.collect_metrics import build_batch_analysis
from scripts.score_topics import rank_topics
from scripts.validate_article import ArticleValidator
from scripts.generate_images import generate_prompts, article_dir, generate_one_image
from scripts.image_browser_task import build_phase4_browser_task

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARTICLE_CONTEXT_FILE = os.path.join(BASE, "runtime", "_article_context.json")


def _write_browser_task(phase: str, action: str, payload: dict):
    """写入统一浏览器任务文件。"""
    path = os.path.join(BASE, "runtime", "_browser_task.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"phase": phase, "action": action, "payload": payload},
                  f, ensure_ascii=False, indent=2)
    return path


def _save_article_context(context: dict, replace=False):
    """跨 Phase 保存当前文章正文与元数据；state.json 只保存轻量状态。"""
    current = {}
    if not replace and os.path.exists(ARTICLE_CONTEXT_FILE):
        with open(ARTICLE_CONTEXT_FILE, "r", encoding="utf-8") as f:
            current = json.load(f)
    current.update({k: v for k, v in context.items() if v is not None})
    os.makedirs(os.path.dirname(ARTICLE_CONTEXT_FILE), exist_ok=True)
    with open(ARTICLE_CONTEXT_FILE, "w", encoding="utf-8") as f:
        json.dump(current, f, ensure_ascii=False, indent=2)
    return current


def _load_article_context(context=None):
    saved = {}
    if os.path.exists(ARTICLE_CONTEXT_FILE):
        with open(ARTICLE_CONTEXT_FILE, "r", encoding="utf-8") as f:
            saved = json.load(f)
    saved.update(context or {})
    return saved


def _dump_config():
    """将4个YAML配置写入 runtime/_config.json 供JS读取"""
    cfg = {
        "thresholds": get_thresholds(),
        "selectors": get_selectors(),
        "content_policy": get_content_policy(),
        "services": get_services(),
    }
    path = os.path.join(BASE, "runtime", "_config.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    return path

def _page_signature_guard():
    """返回页面签名核验代码块（嵌入生成的browser code中）"""
    s = get_selectors()
    texts = s["editor"]["page_texts_check"]
    texts_json = json.dumps(texts, ensure_ascii=False)
    btns_json = json.dumps(s["editor"]["button_order"], ensure_ascii=False)
    return (
        f"  var guard = await page.evaluate(function(a) {{\n"
        f"    if(!location.href.includes('/graphic/publish')) return {{passed:false,error:'URL_MISMATCH',actual:location.href}};\n"
        f"    var pm = document.querySelector(a.pm);\n"
        f"    if(!pm) return {{passed:false,error:'NO_PM'}};\n"
        f"    var texts = a.texts;\n"
        f"    var missing = [];\n"
        f"    for(var i=0;i<texts.length;i++){{if(!document.body.innerText.includes(texts[i])) missing.push(texts[i]);}}\n"
        f"    if(missing.length>0) return {{passed:false,error:'TEXT_MISSING',missing:missing}};\n"
        f"    var btns = document.querySelectorAll('button');\n"
        f"    var order = [];\n"
        f"    btns.forEach(function(b){{var t=b.textContent.trim();if(a.btns.includes(t))order.push(t);}});\n"
        f"    for(var i=0;i<a.btns.length;i++){{if(order[i]!==a.btns[i])return{{passed:false,error:'BTN_ORDER',expected:a.btns,actual:order}};}}\n"
        f"    return {{passed:true}};\n"
        f"  }}, {{pm: '{s['editor']['prose_mirror']}', texts: {texts_json}, btns: {btns_json}}});\n"
        f"  console.log('Page guard:',JSON.stringify(guard));\n"
        f"  if(!guard.passed) throw new Error('PAGE_SIGNATURE_FAILED:'+guard.error);\n"
    )

def phase0_collect(context):
    """Phase 0: 数据采集并初始化当日运行。"""
    today = datetime.now().strftime("%Y-%m-%d")
    state = load_state()
    if state.get("run_date") != today:
        reset_to_idle()
        update_state(run_date=today,
                     run_id=datetime.now().strftime("%Y%m%d-%H%M%S"))
    if "articles" in context:
        result = build_batch_analysis(context["articles"])
        update_state(phase="1", status="phase0_done")
        return {"phase": "0", "result": "metrics_written", "next": "1", "detail": result}
    task_path = _write_browser_task("0", "collect_metrics", {
        "url": get_selectors()["pages"]["content_list"],
        "count": get_thresholds()["topics"]["fetch_recent_count"],
    })
    update_state(phase="0", status="waiting_browser")
    return {"phase": "0", "action": "browser_collect", "task_file": task_path}

def phase1_score(context):
    """Phase 1: 选题评分（服务器端全量完成）"""
    metrics = load_metrics()
    last_batch = metrics.get("last_batch", {})
    high_perf = last_batch.get("high_performance", [])
    candidates = context.get("candidates", [])
    recent_titles = [a.get("title", "") for a in context.get("recent_articles", [])]

    # 连续两篇不得使用同一开头钩子。
    history = load_history()
    last_hook_id = history[-1].get("hook_id") if history else None
    eligible = [c for c in candidates if last_hook_id is None or str(c.get("hook_id")) != str(last_hook_id)]
    ranked = rank_topics(eligible, high_perf, recent_titles)
    score_min = get_thresholds()["topics"]["score_min"]
    selected = [c for c in ranked if c.get("score", 0) >= score_min]

    selected_topic = selected[0] if selected else None
    if not selected_topic:
        update_state(phase="1", status="no_qualified_topic")
        return {"phase": "1", "ranked": ranked, "selected": [],
                "error": "no_qualified_topic", "high_performance": high_perf,
                "excluded_hook_id": last_hook_id}
    _save_article_context(selected_topic, replace=True)
    update_state(phase="2", status="phase1_done")
    return {"phase": "1", "ranked": ranked, "selected": selected,
            "next": "2", "high_performance": high_perf,
            "excluded_hook_id": last_hook_id}


def phase2_generate(context):
    """Phase 2: 内容生成 + 本地硬闸（服务器端）"""
    article = _load_article_context(context)
    html = article.get("html", "")
    title = article.get("title", "")
    if not title or not html:
        update_state(phase="2", status="missing_article_content")
        return {"phase": "2", "passed": False, "error": "missing_article_content",
                "message": "Phase 2 输入必须包含非空 title 和 html"}
    v = ArticleValidator(html)
    result = v.validate()
    if result["passed"]:
        article["article_hash"] = article_hash(html)
        _save_article_context(article)
        update_state(phase="3", status="phase2_passed", title=title,
                     article_hash=article["article_hash"])
        return {"phase": "2", "passed": True, "next": "3", "result": result,
                "title": title, "article_hash": article["article_hash"]}
    return {"phase": "2", "passed": False, "result": result}

def _generate_phase3_code(html: str, title: str = ""):
    """生成 Phase 3（写入编辑器）的 Playwright 代码块，嵌入真实 HTML 和标题"""
    _dump_config()
    sel = get_selectors()
    t = get_thresholds()["article"]
    selector_map = {
        "title": sel["editor"]["title"],
        "pm": sel["editor"]["prose_mirror"],
    }
    import json as _j
    s = _j.dumps(selector_map, ensure_ascii=False)
    html_json = _j.dumps(html, ensure_ascii=False)
    title_json = _j.dumps(title, ensure_ascii=False)
    chinese_min = t["chinese_min"]
    local_chinese = len(ArticleValidator.CJK_RE.findall(ArticleValidator(html).plain_text))
    editor_diff_pct = t["chinese_editor_diff_pct"]

    code = (
        f"async (page) => {{\n"
        f"  var s = {s};\n"
        f"  var html = {html_json};\n"
        f"  var titleStr = {title_json};\n"
        f"  var chineseMin = {chinese_min};\n"
        f"  var localChinese = {local_chinese};\n"
        f"  var editorDiffPct = {editor_diff_pct};\n"
        f"{_page_signature_guard()}"
        f"  // 写入正文\n"
        f"  var w = await page.evaluate(function(a) {{\n"
        f"    var pm = document.querySelector(a.sel);\n"
        f"    if(!pm) return {{error:'no pm'}};\n"
        f"    pm.innerHTML = a.html + '<p><br></p>';\n"
        f"    pm.dispatchEvent(new Event('input',{{bubbles:true}}));\n"
        f"    return {{ok:true}};\n"
        f"  }}, {{sel: s.pm, html: html}});\n"
        f"  console.log('Write body:', JSON.stringify(w));\n"
        f"  await page.waitForTimeout(500);\n"
        f"  // 核验正文\n"
        f"  var v = await page.evaluate(function(a) {{\n"
        f"    var pm = document.querySelector(a.sel);\n"
        f"    if(!pm) return {{empty:true}};\n"
        f"    var t = pm.innerText||'';\n"
        f"    var cc = (t.match(/[\\u4e00-\\u9fff\\u3400-\\u4dbf\\uf900-\\ufaff]/g)||[]).length;\n"
        f"    return {{len: t.length, chinese: cc, empty: t.trim()===''}};\n"
        f"  }}, {{sel: s.pm}});\n"
        f"  console.log('Verify body:', JSON.stringify(v));\n"
        f"  if(v.empty || v.chinese < chineseMin) throw new Error('Body verification failed: chinese='+v.chinese+' < '+chineseMin);\n"
        f"  var diffPct = localChinese ? Math.abs(v.chinese-localChinese)*100/localChinese : 100;\n"
        f"  if(diffPct>editorDiffPct) throw new Error('EDITOR_LOCAL_DIFF:'+diffPct.toFixed(2)+'% > '+editorDiffPct+'%');\n"
        f"  if(!titleStr) throw new Error('TITLE_EMPTY');\n"
        f"  var ti = page.locator(s.title);\n"
        f"  await ti.fill(titleStr);\n"
        f"  await page.waitForTimeout(300);\n"
        f"  var actualTitle = await ti.inputValue();\n"
        f"  if(actualTitle!==titleStr||actualTitle.length<{t['title_len_min']}||actualTitle.length>{t['title_len_max']})throw new Error('TITLE_VERIFY_FAILED:'+actualTitle);\n"
        f"  return {{written: w, verified: v, titleWritten: true, title:actualTitle}};\n"
        f"}}"
    )
    path = os.path.join(BASE, "runtime", "_phase3_code.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(code)
    return path

def _generate_phase5_code(day_str, hour_str, expected_title):
    """生成 Phase 5（硬闸/开关/位置/封面/定时确认）的 Playwright 代码块"""
    _dump_config()
    sel = get_selectors()
    thresholds = get_thresholds()["article"]
    sw = sel["switches"]
    loc = sel["location"]
    cov = sel["cover"]
    sched = sel["schedule"]
    buttons = sel["buttons"]

    s = {
        "ad_revenue": sw["ad_revenue"],
        "toutiao_first": sw["toutiao_first"],
        "more_revenue": sw["more_revenue"],
        "personal_view": sw["personal_view"],
        "ai_reference": sw["ai_reference"],
        "edit_label": loc["edit_label"],
        "pos_select": loc["position_select"],
        "opt_css": loc["option_css"],
        "city": loc["city"],
        "single_img": cov["single_image"],
        "day_sel": sched["day_select"],
        "hour_sel": sched["hour_select"],
        "min_sel": sched["minute_select"],
        "min_val": sched["minute_value"],
        "schedule_btn": buttons["schedule"],
        "schedule_dialog_btn": buttons["schedule_in_dialog"],
        "confirm_btn": buttons["confirm"],
        "expected_title": expected_title,
        "chinese_min": thresholds["chinese_min"],
        "images_required": thresholds["images_required"],
    }
    import json as _j
    ss = _j.dumps(s, ensure_ascii=False)

    code = (
        f"async (page) => {{\n"
        f"  var s = {ss};\n"
        f"{_page_signature_guard()}"
        f"  // 发布前硬闸\n"
        f"  var preflight = await page.evaluate(function(a){{\n"
        f"    var title=document.querySelector(a.title)?.value||''; var pm=document.querySelector(a.pm);\n"
        f"    var text=pm?.innerText||''; var chinese=(text.match(/[\\u4e00-\\u9fff\\u3400-\\u4dbf\\uf900-\\ufaff]/g)||[]).length;\n"
        f"    var blocks=pm?Array.from(pm.children).filter(function(n){{return n.tagName==='DIV'&&n.querySelector('img');}}):[];\n"
        f"    var canonical=blocks.map(function(b){{return b.querySelector('.pgc-img img')||b.querySelector('img');}}).filter(Boolean);\n"
        f"    var uniqueCdn=new Set(canonical.filter(function(i){{return i.src&&!i.src.startsWith('blob:')&&/^https?:/.test(i.src);}}).map(function(i){{return i.src.split('~')[0].split('?')[0];}})).size;\n"
        f"    return{{title:title,chinese:chinese,imageBlocks:blocks.length,uniqueCdn:uniqueCdn,blob:canonical.filter(function(i){{return i.src.startsWith('blob:')}}).length}};\n"
        f"  }},{{title:'{sel['editor']['title']}',pm:'{sel['editor']['prose_mirror']}'}});\n"
        f"  console.log('Preflight:',JSON.stringify(preflight));\n"
        f"  if(preflight.title!==s.expected_title)throw new Error('TITLE_MISMATCH');\n"
        f"  if(preflight.chinese<s.chinese_min)throw new Error('BODY_CHINESE_TOO_SHORT:'+preflight.chinese);\n"
        f"  if(preflight.imageBlocks!==s.images_required||preflight.uniqueCdn!==s.images_required||preflight.blob!==0)throw new Error('IMAGE_PREFLIGHT_FAILED:'+JSON.stringify(preflight));\n"
        f"  // 广告收益 — radio 按钮\n"
        f"  var adRevenueLabel = s.ad_revenue;\n"
        f"  var adRadio=await page.evaluate(function(a){{var labels=document.querySelectorAll('label.byte-radio');for(var i=0;i<labels.length;i++){{if((labels[i].textContent||'').trim()===a.t){{var checked=!!labels[i].querySelector('.byte-radio-inner.checked');return{{found:true,checked:checked}};}}}}return{{found:false}};}},{{t:adRevenueLabel}});\n"
        f"  if(!adRadio.found)throw new Error('AD_RADIO_NOT_FOUND:'+adRevenueLabel);\n"
        f"  if(!adRadio.checked){{"
        f"    await page.evaluate(function(a){{var labels=document.querySelectorAll('label.byte-radio');for(var i=0;i<labels.length;i++){{if((labels[i].textContent||'').trim()===a.t){{var input=labels[i].querySelector('input[type=radio]');if(input)input.click();return;}}}}}},{{t:adRevenueLabel}});\n"
        f"    await page.waitForTimeout(300);\n"
        f"  }}\n"
        f"  console.log(adRevenueLabel+':',adRadio.checked?'already':'set OK');\n"
        f"  // 其余底部开关 — checkbox\n"
        f"  var switches = [s.toutiao_first, s.more_revenue, s.personal_view];\n"
        f"  for(var i=0;i<switches.length;i++){{\n"
        f"    var label=switches[i];\n"
        f"    var swResult=await page.evaluate(function(a){{var boxes=document.querySelectorAll('.byte-checkbox');for(var b=0;b<boxes.length;b++){{var cb=boxes[b];if(cb.textContent.includes(a.l)){{var checked=cb.classList.contains('byte-checkbox-checked');return{{found:true,checked:checked}};}}}}return{{found:false}};}},{{l:label}});\n"
        f"    if(!swResult.found)throw new Error('SWITCH_NOT_FOUND:'+label);\n"
        f"    if(!swResult.checked){{"
        f"      await page.evaluate(function(a){{var boxes=document.querySelectorAll('.byte-checkbox');for(var b=0;b<boxes.length;b++){{var cb=boxes[b];if(cb.textContent.includes(a.l)){{var wrapper=cb.querySelector('.byte-checkbox-wrapper')||cb;wrapper.click();return;}}}}}},{{l:label}});\n"
        f"      await page.waitForTimeout(300);\n"
        f"      var swAfter=await page.evaluate(function(a){{var boxes=document.querySelectorAll('.byte-checkbox');for(var b=0;b<boxes.length;b++){{var cb=boxes[b];if(cb.textContent.includes(a.l))return{{checked:cb.classList.contains('byte-checkbox-checked')}};}}return{{checked:false}}}},{{l:label}});\n"
        f"      if(!swAfter.checked)throw new Error('SWITCH_SET_FAILED:'+label);\n"
        f"    }}\n"
        f"    console.log(label+':',swResult.checked?'already':'set OK');\n"
        f"  }}\n"
        f"  // 引用AI反勾选\n"
        f"  var aiChk=await page.evaluate(function(a){{var boxes=document.querySelectorAll('.byte-checkbox');for(var b=0;b<boxes.length;b++){{var cb=boxes[b];if(cb.textContent.includes(a.l))return{{found:true,checked:cb.classList.contains('byte-checkbox-checked')}};}}return{{found:false}};}},{{l:s.ai_reference}});\n"
        f"  if(aiChk.found&&aiChk.checked){{"
        f"    await page.evaluate(function(a){{var boxes=document.querySelectorAll('.byte-checkbox');for(var b=0;b<boxes.length;b++){{var cb=boxes[b];if(cb.textContent.includes(a.l)){{var wrapper=cb.querySelector('.byte-checkbox-wrapper')||cb;wrapper.click();return;}}}}}},{{l:s.ai_reference}});\n"
        f"    await page.waitForTimeout(300);\n"
        f"    var aiAfter=await page.evaluate(function(a){{var boxes=document.querySelectorAll('.byte-checkbox');for(var b=0;b<boxes.length;b++){{var cb=boxes[b];if(cb.textContent.includes(a.l))return{{found:true,checked:cb.classList.contains('byte-checkbox-checked')}};}}return{{found:false,checked:false}};}},{{l:s.ai_reference}});\n"
        f"    if(!aiAfter.found||aiAfter.checked)throw new Error('AI_REFERENCE_UNCHECK_FAILED');\n"
        f"  }}\n"
        f"  console.log('Switches done');\n"
        f"  // 位置 — 上海\n"
        f"  await page.evaluate(function(a){{var c=document.querySelector(a.s);if(c)c.click();}},{{s:s.edit_label}});\n"
        f"  await page.waitForTimeout(1000);\n"
        f"  await page.evaluate(function(a){{var c=document.querySelector(a.s);if(c)c.click();}},{{s:s.pos_select}});\n"
        f"  await page.waitForTimeout(1500);\n"
        f"  var citySet=await page.evaluate(function(a){{var o=document.querySelectorAll(a.opt);for(var i=0;i<o.length;i++){{if(o[i].textContent.trim()===a.city){{o[i].click();return true;}}}}return false;}},{{opt:s.opt_css,city:s.city}});\n"
        f"  if(!citySet)throw new Error('POSITION_CITY_NOT_FOUND:'+s.city);\n"
        f"  await page.waitForTimeout(500);\n"
        f"  var positionText=await page.evaluate(function(a){{return document.querySelector(a.s)?.textContent.trim()||'';}},{{s:s.pos_select}});\n"
        f"  if(!positionText.includes(s.city))throw new Error('POSITION_VERIFY_FAILED:'+positionText);\n"
        f"  console.log('Position set to:',positionText);\n"
        f"  // 封面 — 单图\n"
        f"  var cover=await page.evaluate(function(a){{var all=document.querySelectorAll('label,span,.byte-radio-wrapper');for(var i=0;i<all.length;i++){{if(all[i].textContent.trim()===a.txt){{var w=all[i].closest('.byte-radio-wrapper')||all[i];if(w.classList.contains('byte-radio-wrapper-checked'))return'checked';w.querySelector('input')?.click();if(!w.querySelector('input'))w.click();return'set';}}}}return'not_found';}},{{txt:s.single_img}});\n"
        f"  if(cover==='not_found')throw new Error('COVER_NOT_FOUND');\n"
        f"  console.log('Cover:',cover);\n"
        f"  await page.waitForTimeout(500);\n"
        f"  var coverOk=await page.evaluate(function(){{var imgs=document.querySelectorAll('.cover-upload-area img,[class*=\\\"cover\\\"] img');for(var i=0;i<imgs.length;i++){{if(imgs[i].src&&!imgs[i].src.startsWith('blob:'))return true;}}return false;}});\n"
        f"  if(!coverOk)throw new Error('COVER_PREVIEW_EMPTY');\n"
        f"  // 定时发布\n"
        f"  await page.locator(s.schedule_btn).click();\n"
        f"  await page.waitForTimeout(2000);\n"
        f"  // 日期\n"
        f"  await page.evaluate(function(a){{var d=document.querySelector(a.s);if(d)d.click();}},{{s:s.day_sel}});\n"
        f"  await page.waitForTimeout(1000);\n"
        f"  var dayOk=await page.evaluate(function(a){{var o=document.querySelectorAll(a.opt);for(var i=0;i<o.length;i++){{if(o[i].textContent.trim()===a.val){{o[i].click();return true;}}}}return false;}},{{opt:s.opt_css,val:'{day_str}'}});\n"
        f"  if(!dayOk)throw new Error('DATE_OPTION_NOT_FOUND:{day_str}');\n"
        f"  await page.waitForTimeout(800);\n"
        f"  // 小时\n"
        f"  await page.evaluate(function(a){{var d=document.querySelector(a.s);if(d)d.click();}},{{s:s.hour_sel}});\n"
        f"  await page.waitForTimeout(1000);\n"
        f"  var hourOk=await page.evaluate(function(a){{var o=document.querySelectorAll(a.opt);for(var i=0;i<o.length;i++){{if(o[i].textContent.trim()===a.val){{o[i].click();return true;}}}}return false;}},{{opt:s.opt_css,val:'{hour_str}'}});\n"
        f"  if(!hourOk)throw new Error('HOUR_OPTION_NOT_FOUND:{hour_str}');\n"
        f"  await page.waitForTimeout(800);\n"
        f"  // 分钟\n"
        f"  await page.evaluate(function(a){{var d=document.querySelector(a.s);if(d)d.click();}},{{s:s.min_sel}});\n"
        f"  await page.waitForTimeout(1000);\n"
        f"  var minOk=await page.evaluate(function(a){{var o=document.querySelectorAll(a.opt);for(var i=0;i<o.length;i++){{if(o[i].textContent.trim()===a.val){{o[i].click();return true;}}}}return false;}},{{opt:s.opt_css,val:s.min_val}});\n"
        f"  if(!minOk)throw new Error('MINUTE_OPTION_NOT_FOUND');\n"
        f"  await page.waitForTimeout(800);\n"
        f"  // 核验时间\n"
        f"  var t=await page.evaluate(function(a){{return{{day:document.querySelector(a.d)?.textContent.trim()||'',hour:document.querySelector(a.h)?.textContent.trim()||'',min:document.querySelector(a.m)?.textContent.trim()||''}};}},{{d:s.day_sel,h:s.hour_sel,m:s.min_sel}});\n"
        f"  console.log('Time check:',JSON.stringify(t));\n"
        f"  if(!t.day.includes('{day_str}')||t.hour!=='{hour_str}'||t.min!==s.min_val)throw new Error('Time mismatch');\n"
        f"  // 预览并定时发布 → 最终确认\n"
        f"  await page.locator(s.schedule_dialog_btn).click();\n"
        f"  await page.waitForTimeout(1500);\n"
        f"  await page.locator(s.confirm_btn).waitFor({{state:'visible',timeout:10000}});\n"
        f"  await page.locator(s.confirm_btn).click();\n"
        f"  await page.waitForURL(function(u){{return u.pathname.includes('/graphic/articles');}},{{timeout:15000}});\n"
        f"  console.log('Phase 5 done - scheduled');\n"
        f"  return{{publishClicked:true,switchesDone:true,position:positionText,cover:cover,coverOk:coverOk,time:t,url:page.url()}};\n"
        f"}}"
    )
    path = os.path.join(BASE, "runtime", "_phase5_code.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(code)
    return path

def phase3_writer(context=None):
    """Phase 3: 写入编辑器 — 生成 Playwright 代码块，嵌入真实HTML/标题"""
    article = _load_article_context(context)
    html = article.get("html", "")
    title = article.get("title", "")
    if not html:
        return {"phase": "3", "error": "no_html", "message": "Phase 3 需要已通过验证的 html"}

    path = _generate_phase3_code(html, title)
    ah = article_hash(html)
    article["article_hash"] = ah
    _save_article_context(article)
    update_state(phase="3", status="waiting_browser", title=title, article_hash=ah)
    _write_browser_task("3", "browser_write", {"code_file": path, "title": title})
    return {"phase": "3", "action": "browser_write", "code_file": path,
            "title": title, "article_hash": ah}


def phase4_images(context=None):
    """Phase 4: 配图生成/上传 — server端调用API生图 + 生成browser relocate+validate代码"""
    article = _load_article_context(context)
    title = article.get("title", "")
    html = article.get("html", "")

    if not title or not html:
        return {"phase": "4", "error": "no_article_data",
                "message": "Phase 4 需要 title 和 html（从 context 或 state）"}

    # === Server端：自动生成图片 ===
    prompts = generate_prompts(title, html)
    img_dir = article_dir(title)

    import sys as _sys
    results = []
    for i, prompt in enumerate(prompts):
        idx = i + 1
        print(f"Phase 4: generating img{idx}/{len(prompts)}...", file=_sys.stderr)
        r = generate_one_image(prompt, img_dir, idx)
        results.append(r)
        print(f"  img{idx}: {'OK' if r.get('ok') else 'FAIL'}", file=_sys.stderr)

    successes = [r for r in results if r.get("ok")]
    all_ok = len(successes) == len(prompts)
    image_dir_rel = os.path.relpath(img_dir, BASE)

    if not all_ok:
        # 不发布，清空状态
        update_state(phase="4", status="image_failed")
        return {"phase": "4", "error": "image_generation_failed",
                "all_ok": False, "results": results,
                "message": "图片生成失败，不进入浏览器流程"}

    # === 生成单文件browser任务：上传三图 → 自动定位 → 段落完整性核验 ===
    s = get_selectors()
    t = get_thresholds()["article"]
    browser_task = build_phase4_browser_task(
        title=title,
        html=html,
        article_hash=state.get("article_hash", "") if (state := load_state()) else "",
        image_paths=[r["path"] for r in results],
        editor_selector=s["editor"]["prose_mirror"],
        article_cfg=t,
    )
    update_state(phase="4", status="waiting_browser", last_image_dir=image_dir_rel)
    _write_browser_task("4", "browser_images", browser_task)
    return {"phase": "4", "action": "browser_images",
            "code_file": browser_task["code_file"],
            "execution": browser_task["execution"],
            "all_ok": True, "image_dir": image_dir_rel,
            "results": results, "prompts": prompts}

def _allocate_schedule():
    """从明天开始逐日扫描，返回第一个未被 history/state 占用的配置时段。"""
    now = datetime.now()
    cfg = get_thresholds()["publish"]
    slots = cfg["scheduled_times"]
    occupied = {
        entry.get("scheduled_time", "")
        for entry in load_history()
        if entry.get("scheduled_time")
    }
    state_time = load_state().get("scheduled_time")
    if state_time:
        occupied.add(state_time)

    for day_offset in range(1, cfg["schedule_search_days"] + 1):
        target_day = now + timedelta(days=day_offset)
        iso_date = target_day.strftime("%Y-%m-%d")
        for slot in slots:
            slot_time = f"{iso_date} {slot}"
            if slot_time not in occupied:
                hour, _ = slot.split(":")
                return target_day.strftime("%m月%d日"), str(int(hour)), iso_date
    raise RuntimeError("NO_SCHEDULE_SLOT_AVAILABLE")


def phase5_publish(context=None):
    """Phase 5: 定时发布 — 时段分配器"""
    article = _load_article_context(context)
    title = article.get("title") or load_state().get("title") or ""
    if not title:
        return {"phase": "5", "error": "no_title", "message": "Phase 5 需要已验证标题"}
    state = load_state()
    existing_time = state.get("scheduled_time") if str(state.get("phase")) == "5" else None
    if existing_time:
        scheduled_dt = datetime.strptime(existing_time, "%Y-%m-%d %H:%M")
        day_str = scheduled_dt.strftime("%m月%d日")
        hour_str = str(scheduled_dt.hour)
        iso_date = scheduled_dt.strftime("%Y-%m-%d")
    else:
        day_str, hour_str, iso_date = _allocate_schedule()

    # 记录占用时段到state（供下一篇分配器读取）
    h_int = int(hour_str)
    slot_time = f"{iso_date} {h_int:02d}:00"
    update_state(phase="5", status="waiting_browser", scheduled_time=slot_time)

    path = _generate_phase5_code(day_str, hour_str, title)
    _write_browser_task("5", "browser_publish", {
        "code_file": path, "scheduled_time": slot_time,
    })
    return {"phase": "5", "action": "browser_publish", "code_file": path,
            "date": day_str, "hour": hour_str, "scheduled_time": slot_time}

def phase6_verify(context=None):
    """Phase 6: 发布后列表核验 — 生成 Playwright 代码块，嵌入标题"""
    article = _load_article_context(context)
    title = article.get("title") or load_state().get("title") or ""
    if not title:
        return {"phase": "6", "error": "no_title",
                "message": "Phase 6 需要 title（从 context 或 state）"}

    s = get_selectors()
    title_json = json.dumps(title, ensure_ascii=False)
    scheduled_time = load_state().get("scheduled_time") or article.get("scheduled_time") or ""
    scheduled_json = json.dumps(scheduled_time, ensure_ascii=False)
    statuses_json = json.dumps(s["verify"]["status_scheduled"], ensure_ascii=False)
    max_checks = get_thresholds()["state"]["uncertain_max_checks"]
    code_path = os.path.join(BASE, "runtime", "_phase6_code.txt")
    code = (
        f"async (page) => {{\n"
        f"  var title = {title_json};\n"
        f"  var scheduledTime = {scheduled_json};\n"
        f"  var statuses = {statuses_json};\n"
        f"  var expectedUrl = '{s['verify']['entry_url_pattern']}';\n"
        f"  if(!page.url().includes(expectedUrl)) return {{verified:false, reason:'not_on_list_page:'+page.url()}};\n"
        f"  for(var attempt=1;attempt<={max_checks};attempt++){{\n"
        f"    var found = await page.evaluate(function(a) {{\n"
        f"      var links = document.querySelectorAll(a.selector);\n"
        f"      for(var i=0;i<links.length;i++){{\n"
        f"        if(links[i].textContent.trim()!==a.title)continue;\n"
        f"        var row=links[i]; for(var up=0;up<6&&row.parentElement;up++)row=row.parentElement;\n"
        f"        var text=row.textContent||'';\n"
        f"        var status=a.statuses.find(function(x){{return text.includes(x)}})||'';\n"
        f"        var parts=a.time.split(/[- :]/);\n"
        f"        var timeOk=!a.time||(parts.length>=5&&text.includes(parts[1]+'-'+parts[2])&&text.includes(parts[3]+':'+parts[4]));\n"
        f"        return{{found:true,status:status,statusOk:!!status,timeOk:timeOk,rowText:text.substring(0,300)}};\n"
        f"      }}\n"
        f"      return{{found:false,statusOk:false,timeOk:false}};\n"
        f"    }},{{title:title,time:scheduledTime,statuses:statuses,selector:{json.dumps(s['verify']['title_cell_css'])}}});\n"
        f"    console.log('Verify attempt '+attempt+':',JSON.stringify(found));\n"
        f"    if(found.found&&found.statusOk&&found.timeOk)return{{verified:true,attempt:attempt,details:found}};\n"
        f"    if(attempt<{max_checks}){{await page.waitForTimeout(3000);await page.reload();await page.waitForTimeout(3000);}}\n"
        f"  }}\n"
        f"  return{{verified:false,reason:'NOT_CONFIRMED_AFTER_{max_checks}_CHECKS'}};\n"
        f"}}"
    )
    with open(code_path, "w", encoding="utf-8") as f:
        f.write(code)
    _write_browser_task("6", "browser_verify", {
        "code_file": code_path, "title": title,
        "scheduled_time": load_state().get("scheduled_time"),
    })
    return {"phase": "6", "action": "browser_verify", "code_file": code_path,
            "title": title}

def phase7_cleanup(context):
    """Phase 7: 用 history 作为提交记录，对 state/metrics 做崩溃后幂等对账。"""
    article = _load_article_context(context)
    state = load_state()
    if not state.get("publish_verified"):
        return {"phase": "7", "error": "publish_not_verified",
                "message": "Phase 6 未确认发布，不允许落盘或递增 article_index"}

    title = article.get("title") or state.get("title") or ""
    scheduled_time = article.get("scheduled_time") or state.get("scheduled_time") or ""
    ah = article.get("article_hash") or state.get("article_hash") or ""
    operation_key = ah or article_hash(f"{title}|{scheduled_time}")
    history = load_history()
    existing = next((
        entry for entry in history
        if entry.get("operation_key") == operation_key
        or (ah and entry.get("article_hash") == ah)
        or (title and scheduled_time and entry.get("title") == title
            and entry.get("scheduled_time") == scheduled_time)
    ), None)

    if existing:
        committed_index = existing.get("article_index_after") or max(
            state.get("article_index", 0), 1
        )
        action = "already_recorded"
    else:
        committed_index = state.get("article_index", 0) + 1
        entry = {
            "title": title,
            "topic": article.get("topic", ""),
            "direction": article.get("direction", ""),
            "series_id": article.get("series_id", ""),
            "framework": article.get("framework", ""),
            "hook_id": article.get("hook_id"),
            "scheduled_time": scheduled_time,
            "publish_status": "scheduled",
            "article_hash": ah,
            "operation_key": operation_key,
            "article_index_after": committed_index,
        }
        append_history(entry)
        action = "daily_done" if committed_index >= get_thresholds()["publish"]["articles_per_day"] else "next_article"

    if state.get("article_index", 0) != committed_index:
        update_state(article_index=committed_index)

    m = load_metrics()
    counted = m.get("published_operation_keys", [])
    if operation_key not in counted:
        m["articles_total"] = m.get("articles_total", 0) + 1
        counted.append(operation_key)
        m["published_operation_keys"] = counted[-get_thresholds()["state"]["history_max"]:]
        save_metrics(m)

    cleanup_temp(keep_images=False)
    if os.path.exists(ARTICLE_CONTEXT_FILE):
        os.remove(ARTICLE_CONTEXT_FILE)

    if committed_index >= get_thresholds()["publish"]["articles_per_day"]:
        reset_to_idle()
        return {"phase": "7", "action": "daily_done", "article_index": committed_index}

    update_state(phase="idle", status="ready_next_article", publish_clicked=False,
                 publish_verified=False, title=None, article_hash=None,
                 scheduled_time=None)
    return {"phase": "7", "action": action, "article_index": committed_index}


def main():
    ensure_runtime_dirs()
    _dump_config()

    import argparse
    parser = argparse.ArgumentParser(description="头条号自动发布编排入口")
    parser.add_argument("--prepare", type=int, choices=range(0, 8), help="准备Phase的浏览器代码")
    parser.add_argument("--complete", type=int, choices=range(0, 8), help="Phase完成后提交结果")
    parser.add_argument("--phase", type=int, choices=range(0, 8), help=argparse.SUPPRESS)
    parser.add_argument("--input", help="输入JSON文件路径")
    parser.add_argument("--status", action="store_true", help="打印当前状态并退出")
    parser.add_argument("--recovery", action="store_true", help="检测恢复状态并输出")
    args = parser.parse_args()

    if args.status:
        state = load_state()
        print(json.dumps(state, ensure_ascii=False, indent=2))
        sys.exit(0)

    if args.recovery:
        action, detail = detect_recovery()
        print(json.dumps({"action": action, "detail": detail, "state": load_state()},
                         ensure_ascii=False, indent=2))
        sys.exit(0)

    # Load input context
    context = {}
    if args.input:
        with open(args.input, "r", encoding="utf-8") as f:
            context = json.load(f)
    elif not sys.stdin.isatty():
        context = json.loads(sys.stdin.read())

    # Determine phase (--prepare > --phase > current state)
    phase = args.prepare if args.prepare is not None else args.phase
    is_complete = args.complete is not None
    if is_complete:
        phase = args.complete
    elif phase is None:
        state_phase = str(load_state().get("phase", "idle")).lower()
        phase_map = {"idle": 0, "done": 0, "0": 0, "1": 1, "2": 2,
                     "3": 3, "4": 4, "5": 5, "6": 6, "7": 7}
        phase = phase_map.get(state_phase, 0)

    # Execute phase
    phases = [
        phase0_collect,
        phase1_score,
        phase2_generate,
        phase3_writer,
        phase4_images,
        phase5_publish,
        phase6_verify,
        phase7_cleanup,
    ]

    if phase < 0 or phase >= len(phases):
        print(json.dumps({"error": f"Invalid phase: {phase}"}))
        sys.exit(1)

    if is_complete:
        if phase in (1, 2, 7):
            print(json.dumps({"error": "server_phase_cannot_complete",
                              "message": f"Phase {phase} 直接执行；不得使用 --complete"},
                             ensure_ascii=False, indent=2))
            sys.exit(1)
        current_phase = str(load_state().get("phase", "idle"))
        if current_phase != str(phase):
            print(json.dumps({"error": "phase_order_mismatch",
                              "expected": current_phase, "received": str(phase)},
                             ensure_ascii=False, indent=2))
            sys.exit(1)
        if phase == 0:
            articles = context.get("articles", [])
            if not articles:
                print(json.dumps({"error": "phase0_missing_articles", "result": context},
                                 ensure_ascii=False, indent=2))
                sys.exit(1)
            build_batch_analysis(articles)
        if phase == 3:
            written = context.get("written", {})
            verified = context.get("verified", {})
            if not written.get("ok") or not context.get("titleWritten") or verified.get("chinese", 0) < get_thresholds()["article"]["chinese_min"]:
                print(json.dumps({"error": "phase3_verification_failed", "result": context},
                                 ensure_ascii=False, indent=2))
                sys.exit(1)
        if phase == 4:
            validated = context.get("validated", {})
            if (not context.get("uploaded") or not context.get("relocated")
                    or not validated.get("passed")
                    or not validated.get("paragraphIntegrityOk")):
                print(json.dumps({"error": "phase4_validation_failed", "result": context},
                                 ensure_ascii=False, indent=2))
                sys.exit(1)
        if phase == 5 and (
            not context.get("publishClicked")
            or not context.get("switchesDone")
            or not context.get("coverOk")
            or get_selectors()["location"]["city"] not in str(context.get("position", ""))
        ):
            print(json.dumps({"error": "phase5_not_confirmed", "result": context},
                             ensure_ascii=False, indent=2))
            sys.exit(1)
        if phase == 6 and not context.get("verified"):
            update_state(phase="6", status="publish_uncertain", publish_verified=False)
            print(json.dumps({"error": "publish_uncertain", "result": context},
                             ensure_ascii=False, indent=2))
            sys.exit(1)

        phase_names = ["phase0_done", "phase1_done", "phase2_done", "phase3_done",
                       "phase4_done", "phase5_done", "phase6_done", "phase7_done"]
        next_phase = phase + 1
        updates = {
            "phase": str(next_phase) if next_phase < 8 else "idle",
            "status": phase_names[phase],
        }
        if phase == 5:
            updates["publish_clicked"] = True
        if phase == 6:
            updates["publish_verified"] = True
        update_state(**updates)
        print(json.dumps({"phase": str(phase), "action": "completed",
                          "next": str(next_phase) if next_phase < 8 else "idle",
                          "result": context}, ensure_ascii=False, indent=2))
        sys.exit(0)

    result = phases[phase](context)
    result["config_path"] = _dump_config()
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if result.get("action") in ("browser_collect", "browser_write", "browser_images", "browser_publish", "browser_verify"):
        print(f"\n→ Claude 模式: 读取 runtime/_browser_task.json → 执行 browser_run_code_unsafe → 把结果传给 --complete --phase {phase} --input result.json",
              file=sys.stderr)

if __name__ == "__main__":
    main()
