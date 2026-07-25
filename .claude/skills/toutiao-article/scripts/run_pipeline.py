"""
头条号自动发布 - 统一编排入口 (v8.0)
按 Phase 0→7 真实调用全部模块；SKILL.md 只调用此入口。
读取4个YAML配置，输出浏览器操作指令到 runtime/_browser_task.json。
"""
import sys, os, json, subprocess, tempfile, shutil
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lib.config_loader import get_thresholds, get_selectors, get_content_policy, get_services
from state import (
    load_state, save_state, update_state, reset_to_idle,
    load_history, append_history, load_metrics, save_metrics,
    detect_recovery, ensure_runtime_dirs, cleanup_temp,
)
from collect_metrics import build_batch_analysis
from score_topics import rank_topics
from validate_article import ArticleValidator

BASE = os.path.dirname(os.path.abspath(__file__))

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

def _generate_playwright_block(phase_name, commands_template, **kwargs):
    """
    生成可直接粘贴到 browser_run_code_unsafe 的 Playwright 代码块。
    自动注入 selectors 和 thresholds。
    """
    _dump_config()
    s = get_selectors()
    t = get_thresholds()

    # Compact selector map for browser
    sel = {
        "title": s["editor"]["title"],
        "pm": s["editor"]["prose_mirror"],
        "ad_revenue": s["switches"]["ad_revenue"],
        "toutiao_first": s["switches"]["toutiao_first"],
        "more_revenue": s["switches"]["more_revenue"],
        "personal_view": s["switches"]["personal_view"],
        "ai_reference": s["switches"]["ai_reference"],
        "edit_label": s["location"]["edit_label"],
        "pos_select": s["location"]["position_select"],
        "opt_css": s["location"]["option_css"],
        "city": s["location"]["city"],
        "single_img": s["cover"]["single_image"],
        "day_sel": s["schedule"]["day_select"],
        "hour_sel": s["schedule"]["hour_select"],
        "min_sel": s["schedule"]["minute_select"],
        "min_val": s["schedule"]["minute_value"],
        "schedule_btn": "定时发布",
        "schedule_dialog_btn": "预览并定时发布",
        "cancel_btn": "取消",
        "confirm_btn": 'button.publish-btn:has-text("定时发布")',
        "imgs_req": t["article"]["images_required"],
        "imports_required": t["article"]["images_required"],
        "hist_max": t["state"]["history_max"],
    }

    code = f"""// Phase: {phase_name} — 自动生成 · 配置已嵌入
async (page) => {{
  var s = {json.dumps(sel, ensure_ascii=False)};
  {commands_template}
}}
"""
    path = os.path.join(BASE, "runtime", f"_{phase_name}_playwright.js")
    with open(path, "w", encoding="utf-8") as f:
        f.write(code)

    # Also write readable summary
    task_path = os.path.join(BASE, "runtime", "_browser_task.json")
    with open(task_path, "w", encoding="utf-8") as f:
        json.dump({"phase": phase_name, "code_file": path, "action": f"Run browser_run_code_unsafe with code from {path}"}, f, ensure_ascii=False)

    return path

def phase0_collect(context):
    """Phase 0: 数据采集（端到端）
    接收 context['articles'] 或提示AI从页面采集"""
    if "articles" in context:
        result = build_batch_analysis(context["articles"])
        update_state(phase="0", status="phase0_done")
        return {"phase": "0", "result": "metrics_written", "detail": result}
    # 需要浏览器采集 → 写任务
    _write_browser_task("collect_metrics", "scrapeArticleList", {
        "url": get_selectors()["pages"]["content_list"],
        "count": get_thresholds()["topics"]["fetch_recent_count"],
    })
    update_state(phase="0", status="waiting_browser")
    return {"phase": "0", "action": "browser_collect"}

def phase1_score(context):
    """Phase 1: 选题评分（服务器端全量完成）"""
    metrics = load_metrics()
    last_batch = metrics.get("last_batch", {})
    high_perf = last_batch.get("high_performance", [])
    candidates = context.get("candidates", [])
    recent_titles = [a.get("title","") for a in context.get("recent_articles", [])]

    ranked = rank_topics(candidates, high_perf, recent_titles)
    selected = [c for c in ranked if c.get("score", 0) >= 70]
    update_state(phase="1", status="phase1_done")
    return {"phase": "1", "ranked": ranked, "selected": selected, "high_performance": high_perf}

def phase2_generate(context):
    """Phase 2: 内容生成 + 本地硬闸（服务器端）"""
    html = context.get("html", "")
    v = ArticleValidator(html)
    result = v.validate()
    if result["passed"]:
        update_state(phase="2", status="phase2_passed", article_hash=v.article_hash(html))
        return {"phase": "2", "passed": True, "result": result}
    return {"phase": "2", "passed": False, "result": result}

def _generate_phase3_code():
    """生成 Phase 3（写入编辑器）的 Playwright 代码块"""
    _dump_config()
    sel = get_selectors()
    selector_map = {
        "title": sel["editor"]["title"],
        "pm": sel["editor"]["prose_mirror"],
    }
    import json as _j
    s = _j.dumps(selector_map, ensure_ascii=False)
    code = (
        f"async (page) => {{\n"
        f"  var s = {s};\n"
        f"  // 正文HTML在此替换\n"
        f"  var html = '<p>替换为正文HTML</p>';\n"
        f"  var w = await page.evaluate(function(a) {{\n"
        f"    var pm = document.querySelector(a.sel);\n"
        f"    if(!pm) return {{error:'no pm'}};\n"
        f"    pm.innerHTML = a.html;\n"
        f"    pm.dispatchEvent(new Event('input',{{bubbles:true}}));\n"
        f"    return {{ok:true}};\n"
        f"  }}, {{sel: s.pm, html: html}});\n"
        f"  console.log('Write:', JSON.stringify(w));\n"
        f"  await page.waitForTimeout(500);\n"
        f"  var v = await page.evaluate(function(a) {{\n"
        f"    var pm = document.querySelector(a.sel);\n"
        f"    if(!pm) return {{empty:true}};\n"
        f"    var t = pm.innerText||'';\n"
        f"    return {{len: t.length, text: t.substring(0,100), empty: t.trim()===''}};\n"
        f"  }}, {{sel: s.pm}});\n"
        f"  console.log('Verify:', JSON.stringify(v));\n"
        f"  if(v.empty || v.len < 1500) throw new Error('Body verification failed: '+v.len);\n"
        f"  return {{written: w, verified: v}};\n"
        f"}}"
    )
    path = os.path.join(BASE, "runtime", "_phase3_code.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(code)
    return path

def _generate_phase5_code(day_str, hour_str):
    """生成 Phase 5（设置开关/位置/封面/定时）的 Playwright 代码块"""
    _dump_config()
    sel = get_selectors()
    sw = sel["switches"]
    loc = sel["location"]
    cov = sel["cover"]
    sched = sel["schedule"]

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
    }
    import json as _j
    ss = _j.dumps(s, ensure_ascii=False)

    code = (
        f"async (page) => {{\n"
        f"  var s = {ss};\n"
        f"  // 确保标题已写入\n"
        f"  var titleVal = await page.evaluate(function(a){{return document.querySelector(a.sel)?.value||'';}}, {{sel: 'textarea[placeholder*=\\'请输入文章标题\\']'}});\n"
        f"  console.log('Title:', titleVal.substring(0,30));\n"
        f"  // 开关 — 找文本 → click → 核验checked\n"
        f"  var switches = [s.ad_revenue, s.toutiao_first, s.more_revenue, s.personal_view];\n"
        f"  for(var i=0;i<switches.length;i++){{\n"
        f"    var label=switches[i];\n"
        f"    var before=await page.evaluate(function(a){{var c=document.querySelectorAll('input[type=checkbox],input[type=radio]');for(var i=0;i<c.length;i++){{var p=c[i].parentElement;for(var j=0;j<5;j++){{if(!p)break;if(p.textContent&&p.textContent.includes(a.l))return{{found:true,checked:c[i].checked}};p=p.parentElement;}}}}return{{found:false}};}},{{l:label}});\n"
        f"    if(!before.found)throw new Error('SWITCH_NOT_FOUND:'+label);\n"
        f"    if(!before.checked){{"
        f"      await page.evaluate(function(a){{var c=document.querySelectorAll('input[type=checkbox],input[type=radio]');for(var i=0;i<c.length;i++){{var p=c[i].parentElement;for(var j=0;j<5;j++){{if(!p)break;if(p.textContent&&p.textContent.includes(a.l)){{c[i].click();return;}}p=p.parentElement;}}}}}},{{l:label}});\n"
        f"      await page.waitForTimeout(300);\n"
        f"      var after=await page.evaluate(function(a){{var c=document.querySelectorAll('input[type=checkbox],input[type=radio]');for(var i=0;i<c.length;i++){{var p=c[i].parentElement;for(var j=0;j<5;j++){{if(!p)break;if(p.textContent&&p.textContent.includes(a.l))return{{checked:c[i].checked}};p=p.parentElement;}}}}return{{checked:false}};}},{{l:label}});\n"
        f"      if(!after.checked)throw new Error('SWITCH_SET_FAILED:'+label);\n"
        f"    }}\n"
        f"    console.log(label+':',before.checked?'already':'set OK');\n"
        f"  }}\n"
        f"  // 引用AI反勾选\n"
        f"  var aiChk=await page.evaluate(function(a){{var c=document.querySelectorAll('input[type=checkbox]');for(var i=0;i<c.length;i++){{var p=c[i].parentElement;for(var j=0;j<5;j++){{if(!p)break;if(p.textContent&&p.textContent.includes(a.l))return{{found:true,checked:c[i].checked}};p=p.parentElement;}}}}return{{found:false}};}},{{l:s.ai_reference}});\n"
        f"  if(aiChk.found&&aiChk.checked){{"
        f"    await page.evaluate(function(a){{var c=document.querySelectorAll('input[type=checkbox]');for(var i=0;i<c.length;i++){{var p=c[i].parentElement;for(var j=0;j<5;j++){{if(!p)break;if(p.textContent&&p.textContent.includes(a.l)){{c[i].click();return;}}p=p.parentElement;}}}}}},{{l:s.ai_reference}});\n"
        f"    await page.waitForTimeout(300);\n"
        f"    var aiAfter=await page.evaluate(function(a){{var c=document.querySelectorAll('input[type=checkbox]');for(var i=0;i<c.length;i++){{var p=c[i].parentElement;for(var j=0;j<5;j++){{if(!p)break;if(p.textContent&&p.textContent.includes(a.l))return{{found:true,checked:c[i].checked}};p=p.parentElement;}}}}return{{found:false}};}},{{l:s.ai_reference}});\n"
        f"    if(aiAfter.found&&aiAfter.checked)throw new Error('AI_REFERENCE_STILL_CHECKED');\n"
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
        f"  console.log('Position set to:',s.city);\n"
        f"  // 封面 — 单图\n"
        f"  var cover=await page.evaluate(function(a){{var all=document.querySelectorAll('label,span,.byte-radio-wrapper');for(var i=0;i<all.length;i++){{if(all[i].textContent.trim()===a.txt){{var w=all[i].closest('.byte-radio-wrapper')||all[i];if(w.classList.contains('byte-radio-wrapper-checked'))return'checked';w.querySelector('input')?.click();if(!w.querySelector('input'))w.click();return'set';}}}}return'not_found';}},{{txt:s.single_img}});\n"
        f"  if(cover==='not_found')throw new Error('COVER_NOT_FOUND');\n"
        f"  console.log('Cover:',cover);\n"
        f"  await page.waitForTimeout(500);\n"
        f"  // 定时发布\n"
        f"  await page.locator('button:has-text(\\\"定时发布\\\")').click();\n"
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
        f"  if(!t.day.includes('{day_str}')||t.hour!=='{hour_str}'||t.min!=='0')throw new Error('Time mismatch');\n"
        f"  console.log('Phase 5 done - ready for final confirm');\n"
        f"  return{{switchesDone:true,position:s.city,cover:cover,time:t}};\n"
        f"}}"
    )
    path = os.path.join(BASE, "runtime", "_phase5_code.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(code)
    return path

def phase3_writer(context=None):
    """Phase 3: 写入编辑器 — 生成 Playwright 代码块"""
    path = _generate_phase3_code()
    update_state(phase="3", status="waiting_browser")
    return {"phase": "3", "action": "browser_write", "code_file": path,
            "message": f"browser_run_code_unsafe 执行 {path} 中的代码。替换html为正文后执行。"}

def phase4_images(context=None):
    """Phase 4: 配图上传 — 生成 Playwright 代码块"""
    s = get_selectors()
    code_path = os.path.join(BASE, "runtime", "_phase4_code.txt")
    code = (
        f"async (page) => {{\n"
        f"  // 已上传3张图到 {os.path.join(BASE, 'runtime', 'images')}\n"
        f"  // 依次 browser_drop 到 .ProseMirror\n"
        f"  var sel = {{pm: '{s['editor']['prose_mirror']}'}};\n"
        f"  // 拖完后 relocate\n"
        f"  var r = await page.evaluate(function(a) {{\n"
        f"    var pm = document.querySelector(a.sel);\n"
        f"    if(!pm) return {{error:'no pm'}};\n"
        f"    var divs=[]; for(var i=0;i<pm.children.length;i++){{if(pm.children[i].tagName==='DIV'&&pm.children[i].querySelector('img'))divs.push(pm.children[i]);}}\n"
        f"    if(divs.length!==3) return {{error:'imgDivs='+divs.length}};\n"
        f"    var paras=[]; for(var i=0;i<pm.children.length;i++){{if(pm.children[i].tagName==='P'&&!pm.children[i].querySelector('img'))paras.push(pm.children[i]);}}\n"
        f"    if(paras.length<10) return {{error:'paras='+paras.length}};\n"
        f"    var n=paras.length, t=[Math.floor(n*0.25)-1,Math.floor(n*0.50)-1,Math.floor(n*0.75)-1];\n"
        f"    for(var k=1;k<t.length;k++){{if(t[k]<=t[k-1])t[k]=t[k-1]+2;}}\n"
        f"    if(t[2]>=n)t[2]=n-1;\n"
        f"    for(var k=divs.length-1;k>=0;k--){{var tp=paras[t[k]];if(tp)tp.insertAdjacentElement('afterend',divs[k]);}}\n"
        f"    pm.dispatchEvent(new Event('input',{{bubbles:true}}));\n"
        f"    return{{ok:true,targets:t,paras:n}};\n"
        f"  }}, {{sel: sel.pm}});\n"
        f"  console.log('Relocate:',JSON.stringify(r));\n"
        f"  return r;\n"
        f"}}"
    )
    with open(code_path, "w", encoding="utf-8") as f:
        f.write(code)
    update_state(phase="4", status="waiting_browser")
    return {"phase": "4", "action": "browser_images", "code_file": code_path}

def phase5_publish(context=None):
    """Phase 5: 定时发布 — 生成 Playwright 代码块"""
    from datetime import datetime, timedelta
    tomorrow = datetime.now() + timedelta(days=1)
    day_str = tomorrow.strftime("%m月%d日")
    hour_str = "6"  # Default: 06:00
    path = _generate_phase5_code(day_str, hour_str)
    update_state(phase="5", status="waiting_browser")
    return {"phase": "5", "action": "browser_publish", "code_file": path,
            "date": day_str, "hour": hour_str}

def phase6_verify(context=None):
    """Phase 6: 发布后列表核验 — 生成 Playwright 代码块"""
    s = get_selectors()
    code_path = os.path.join(BASE, "runtime", "_phase6_code.txt")
    code = (
        f"async (page) => {{\n"
        f"  var title = '替换为实际标题';\n"
        f"  var expectedUrl = '{s['verify']['entry_url_pattern']}';\n"
        f"  var currentUrl = page.url();\n"
        f"  if(!currentUrl.includes(expectedUrl)) return {{verified:false, reason:'not_on_list_page:'+currentUrl}};\n"
        f"  var found = await page.evaluate(function(a) {{\n"
        f"    var links = document.querySelectorAll('article-item-title a, .article-title a, [class*=\"title\"] a');\n"
        f"    for(var i=0;i<links.length;i++){{if(links[i].textContent.trim()===a.title)return{{found:true,text:links[i].textContent.trim()}};}}\n"
        f"    return{{found:false}};\n"
        f"  }}, {{title:title}});\n"
        f"  console.log('Verify:',JSON.stringify(found));\n"
        f"  return found;\n"
        f"}}"
    )
    with open(code_path, "w", encoding="utf-8") as f:
        f.write(code)
    return {"phase": "6", "action": "browser_verify", "code_file": code_path,
            "message": "browser_run_code_unsafe 执行后，替换title为实际标题"}

def phase7_cleanup(context):
    """Phase 7: 落盘 + 清理（服务器端）"""
    title = context.get("title", "")

    # state.py 已内置历史上限（从thresholds.yaml读取）
    entry = {
        "title": title,
        "direction": context.get("direction", ""),
        "series_id": context.get("series_id", ""),
        "framework": context.get("framework", ""),
        "scheduled_time": context.get("scheduled_time", ""),
        "publish_status": "scheduled",
    }
    append_history(entry)

    # 指标计数
    m = load_metrics()
    m["articles_total"] = m.get("articles_total", 0) + 1
    save_metrics(m)

    # 清临时图片
    cleanup_temp(keep_images=False)

    # 检查是否两篇都完成了
    state = load_state()
    if state.get("article_index", 0) >= get_thresholds()["publish"]["articles_per_day"]:
        reset_to_idle()
        return {"phase": "7", "action": "daily_done", "article_index": state["article_index"]}

    update_state(phase="7", status="phase7_done")
    return {"phase": "7", "action": "next_article", "article_index": state.get("article_index", 0)}


def main():
    ensure_runtime_dirs()
    _dump_config()

    import argparse
    parser = argparse.ArgumentParser(description="头条号自动发布编排入口")
    parser.add_argument("--phase", type=int, choices=range(0, 8), help="指定Phase")
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

    # Determine phase
    if args.phase is not None:
        phase = args.phase
    else:
        # Auto-detect from state
        state = load_state()
        p = state.get("phase", "idle")
        # Map phase value to numeric - phase field stores string
        phase_map = {"idle": 0, "0": 0, "1": 1, "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7}
        phase = phase_map.get(str(p).lower(), 0)

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

    result = phases[phase](context)
    result["config_path"] = _dump_config()
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if result.get("action") in ("browser_collect", "browser_write", "browser_images", "browser_publish", "browser_verify"):
        print(f"\n→ 浏览器操作已写入 runtime/_browser_task.json。SKILL.md 执行对应操作后，再次调用 run_pipeline.py。",
              file=sys.stderr)

if __name__ == "__main__":
    main()
