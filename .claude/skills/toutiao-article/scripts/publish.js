/**
 * 头条号自动发布 - 发布设置脚本 (v8.0)
 * 开关、位置、封面、定时发布。所有确保函数核验操作结果。
 * config 来自 runtime/_config.json，不硬编码。
 *
 * 通过 browser_run_code_unsafe 调用：
 *   const cfg = JSON.parse(require('fs').readFileSync('./runtime/_config.json'));
 *   const { setSwitches, setPosition, setCover, schedulePublish, ensureSwitchWithVerify } = require('./scripts/publish.js');
 *   await setSwitches(page, cfg);
 */

async function ensureSwitchWithVerify(page, label, cfg) {
  var slc = cfg.selectors;
  var sw = slc.switches;

  // Read current state
  var before = await page.evaluate(function(targetLabel) {
    var checks = document.querySelectorAll('input[type="checkbox"], input[type="radio"]');
    for (var i = 0; i < checks.length; i++) {
      var p = checks[i].parentElement;
      for (var j = 0; j < 5; j++) {
        if (!p) break;
        if (p.textContent && p.textContent.includes(targetLabel)) {
          return { found: true, checked: checks[i].checked };
        }
        p = p.parentElement;
      }
    }
    return { found: false };
  }, label);

  if (!before.found) {
    throw new Error('SWITCH_NOT_FOUND: ' + label);
  }

  if (before.checked) {
    console.log(label + ': 已勾 ✓');
    return;
  }

  // Click
  await page.evaluate(function(targetLabel) {
    var checks = document.querySelectorAll('input[type="checkbox"], input[type="radio"]');
    for (var i = 0; i < checks.length; i++) {
      var p = checks[i].parentElement;
      for (var j = 0; j < 5; j++) {
        if (!p) break;
        if (p.textContent && p.textContent.includes(targetLabel)) {
          checks[i].click();
          return;
        }
        p = p.parentElement;
      }
    }
  }, label);

  await page.waitForTimeout(300);

  // Verify after click
  var after = await page.evaluate(function(targetLabel) {
    var checks = document.querySelectorAll('input[type="checkbox"], input[type="radio"]');
    for (var i = 0; i < checks.length; i++) {
      var p = checks[i].parentElement;
      for (var j = 0; j < 5; j++) {
        if (!p) break;
        if (p.textContent && p.textContent.includes(targetLabel)) {
          return { found: true, checked: checks[i].checked };
        }
        p = p.parentElement;
      }
    }
    return { found: false };
  }, label);

  if (!after.checked) {
    throw new Error('SWITCH_SET_FAILED: ' + label + ' still unchecked after click');
  }
  console.log(label + ': ✅ 已勾选确认');
}

async function setSwitches(page, cfg) {
  var sw = cfg.selectors.switches;
  await ensureSwitchWithVerify(page, sw.ad_revenue, cfg);
  await page.waitForTimeout(300);
  await ensureSwitchWithVerify(page, sw.toutiao_first, cfg);
  await page.waitForTimeout(300);
  await ensureSwitchWithVerify(page, sw.more_revenue, cfg);
  await page.waitForTimeout(300);
  await ensureSwitchWithVerify(page, sw.personal_view, cfg);
  await page.waitForTimeout(300);

  // Uncheck "引用AI" if checked
  var aiChecked = await page.evaluate(function(targetLabel) {
    var checks = document.querySelectorAll('input[type="checkbox"]');
    for (var i = 0; i < checks.length; i++) {
      var p = checks[i].parentElement;
      for (var j = 0; j < 5; j++) {
        if (!p) break;
        if (p.textContent && p.textContent.includes(targetLabel)) { return checks[i].checked; }
        p = p.parentElement;
      }
    }
    return false;
  }, cfg.selectors.switches.ai_reference);

  if (aiChecked) {
    await page.evaluate(function(targetLabel) {
      var checks = document.querySelectorAll('input[type="checkbox"]');
      for (var i = 0; i < checks.length; i++) {
        var p = checks[i].parentElement;
        for (var j = 0; j < 5; j++) {
          if (!p) break;
          if (p.textContent && p.textContent.includes(targetLabel)) {
            checks[i].click();
            return;
          }
          p = p.parentElement;
        }
      }
    }, cfg.selectors.switches.ai_reference);
    await page.waitForTimeout(300);
    // Verify unchecked
    var aiAfter = await page.evaluate(function(targetLabel) {
      var checks = document.querySelectorAll('input[type="checkbox"]');
      for (var i = 0; i < checks.length; i++) {
        var p = checks[i].parentElement;
        for (var j = 0; j < 5; j++) {
          if (!p) break;
          if (p.textContent && p.textContent.includes(targetLabel)) { return checks[i].checked; }
          p = p.parentElement;
        }
      }
      return false;
    }, cfg.selectors.switches.ai_reference);
    if (aiAfter) throw new Error('AI_REFERENCE_STILL_CHECKED');
    console.log('引用AI: 已取消 ✅');
  } else {
    console.log('引用AI: 已未勾选 ✓');
  }
}

async function setPosition(page, cfg) {
  var slc = cfg.selectors;
  var city = slc.location.city;

  // Step 1: Click edit-label to activate position
  await page.evaluate(function(sel) {
    var cell = document.querySelector(sel);
    if (cell) cell.click();
  }, slc.location.edit_label);
  await page.waitForTimeout(1000);

  // Step 2: Click .position-select to open dropdown
  await page.evaluate(function(sel) {
    var posSelect = document.querySelector(sel);
    if (posSelect) posSelect.click();
  }, slc.location.position_select);
  await page.waitForTimeout(1500);

  // Step 3: Select city
  var selected = await page.evaluate(function(cityName, optSel) {
    var opts = document.querySelectorAll(optSel);
    for (var i = 0; i < opts.length; i++) {
      if (opts[i].textContent.trim() === cityName) { opts[i].click(); return true; }
    }
    return false;
  }, city, slc.location.option_css);
  await page.waitForTimeout(500);
  if (!selected) throw new Error('POSITION_CITY_NOT_FOUND: ' + city);

  var posDisplay = await page.evaluate(function(sel) {
    var pos = document.querySelector(sel);
    return pos ? pos.textContent.trim() : '';
  }, slc.location.position_select);
  console.log('📍 位置已设置: ' + posDisplay);
  if (!posDisplay.includes(city)) throw new Error('POSITION_SET_FAILED: 位置未设置为' + city);
}

async function setCover(page, cfg) {
  var slc = cfg.selectors;
  var coverSet = await page.evaluate(function(singleText, wrapperClass) {
    var all = document.querySelectorAll('label, span, div, .byte-radio-wrapper');
    for (var i = 0; i < all.length; i++) {
      if (all[i].textContent.trim() === singleText) {
        var wrapper = all[i].closest(wrapperClass) || all[i];
        if (wrapper.classList.contains('byte-radio-wrapper-checked')) {
          return '已选中';
        }
        wrapper.querySelector('input')?.click();
        if (!wrapper.querySelector('input')) wrapper.click();
        return '已点击设';
      }
    }
    return '未找到单图选项';
  }, slc.cover.single_image, slc.cover.wrapper);
  console.log('🖼️ 封面设置:', coverSet);
  if (coverSet === '未找到单图选项') throw new Error('COVER_OPTION_NOT_FOUND');
  await page.waitForTimeout(500);

  var coverPreviewOk = await page.evaluate(function() {
    var imgs = document.querySelectorAll('.cover-upload-area img, [class*="cover"] img');
    for (var i = 0; i < imgs.length; i++) {
      if (imgs[i].src && !imgs[i].src.startsWith('blob:')) return true;
    }
    return false;
  });
  if (!coverPreviewOk) console.log('⚠️ 封面预览可能为空');
}

async function schedulePublish(page, dayStr, hourStr, cfg) {
  var slc = cfg.selectors;
  var btn = slc.buttons;

  // Click timer button
  await page.locator('button:has-text("' + btn.schedule.replace('button:has-text("', '').replace('")', '') + '")').click();
  await page.waitForTimeout(2000);

  // Verify dialog appeared
  var hasDialog = await page.evaluate(function(cancelText, previewText) {
    var btns = document.querySelectorAll('button');
    var c = false, p = false;
    for (var i = 0; i < btns.length; i++) {
      var t = btns[i].textContent;
      if (t.includes(cancelText)) c = true;
      if (t.includes(previewText)) p = true;
    }
    return c && p;
  }, btn.cancel.replace('button:has-text("', '').replace('")', ''), btn.schedule_in_dialog.replace('button:has-text("', '').replace('")', ''));

  if (!hasDialog) {
    await page.waitForTimeout(3000);
    await page.evaluate(function(btnText) {
      var btns = document.querySelectorAll('button');
      for (var i = 0; i < btns.length; i++) {
        if (btns[i].textContent.trim() === btnText) { btns[i].click(); break; }
      }
    }, btn.schedule.replace('button:has-text("', '').replace('")', ''));
    await page.waitForTimeout(2000);
    hasDialog = await page.evaluate(function(cancelText, previewText) {
      var btns = document.querySelectorAll('button');
      var c = false, p = false;
      for (var i = 0; i < btns.length; i++) {
        var t = btns[i].textContent;
        if (t.includes(cancelText)) c = true;
        if (t.includes(previewText)) p = true;
      }
      return c && p;
    }, btn.cancel.replace('button:has-text("', '').replace('")', ''), btn.schedule_in_dialog.replace('button:has-text("', '').replace('")', ''));
    if (!hasDialog) throw new Error('TIMER_DIALOG_FAILED');
  }

  // Select date
  await page.evaluate(function(sel) { var ds = document.querySelector(sel); if (ds) ds.click(); }, slc.schedule.day_select);
  await page.waitForTimeout(1000);
  var daySelected = await page.evaluate(function(dateStr, optSel) {
    var opts = document.querySelectorAll(optSel);
    for (var i = 0; i < opts.length; i++) { if (opts[i].textContent.trim() === dateStr) { opts[i].click(); return true; } }
    return false;
  }, dayStr, slc.location.option_css);
  if (!daySelected) throw new Error('DATE_OPTION_NOT_FOUND: ' + dayStr);
  await page.waitForTimeout(800);

  // Select hour
  await page.evaluate(function(sel) { var hs = document.querySelector(sel); if (hs) hs.click(); }, slc.schedule.hour_select);
  await page.waitForTimeout(1000);
  var hourSelected = await page.evaluate(function(hourStr, optSel) {
    var opts = document.querySelectorAll(optSel);
    for (var i = 0; i < opts.length; i++) { if (opts[i].textContent.trim() === hourStr) { opts[i].click(); return true; } }
    return false;
  }, hourStr, slc.location.option_css);
  if (!hourSelected) throw new Error('HOUR_OPTION_NOT_FOUND: ' + hourStr);
  await page.waitForTimeout(800);

  // Select minute (always 0)
  await page.evaluate(function(sel) { var ms = document.querySelector(sel); if (ms) ms.click(); }, slc.schedule.minute_select);
  await page.waitForTimeout(1000);
  var minSelected = await page.evaluate(function(optSel, minVal) {
    var opts = document.querySelectorAll(optSel);
    for (var i = 0; i < opts.length; i++) { if (opts[i].textContent.trim() === minVal) { opts[i].click(); return true; } }
    return false;
  }, slc.location.option_css, slc.schedule.minute_value);
  if (!minSelected) throw new Error('MINUTE_OPTION_0_NOT_FOUND');
  await page.waitForTimeout(800);

  // Verify time
  var timerVerify = await page.evaluate(function(dSel, hSel, mSel) {
    return {
      day: document.querySelector(dSel) ? document.querySelector(dSel).textContent.trim() : 'not found',
      hour: document.querySelector(hSel) ? document.querySelector(hSel).textContent.trim() : 'not found',
      min: document.querySelector(mSel) ? document.querySelector(mSel).textContent.trim() : 'not found',
    };
  }, slc.schedule.day_select, slc.schedule.hour_select, slc.schedule.minute_select);
  console.log('⏰ 定时时间核验:', JSON.stringify(timerVerify));
  if (!timerVerify.day.includes(dayStr) || timerVerify.hour !== hourStr || timerVerify.min !== '0') {
    throw new Error('❌ 定时时间设置失败：期望 ' + dayStr + ' ' + hourStr + ':00，实际=' + timerVerify.day + ' ' + timerVerify.hour + ':' + timerVerify.min);
  }

  // Click preview and schedule
  await page.evaluate(function(btnText) {
    var buttons = document.querySelectorAll('[role="dialog"] button');
    for (var i = 0; i < buttons.length; i++) {
      if (buttons[i].textContent.includes(btnText)) {
        ['mousedown', 'mouseup', 'click'].forEach(function(type) {
          buttons[i].dispatchEvent(new MouseEvent(type, {bubbles: true, cancelable: true, view: window}));
        });
        break;
      }
    }
  }, cfg.selectors.buttons.schedule_in_dialog.replace('button:has-text("', '').replace('")', ''));
  await page.waitForTimeout(2000);

  // Final confirm
  await page.locator(cfg.selectors.buttons.confirm).waitFor({timeout: 10000});
  await page.waitForTimeout(1000);
  await page.locator(cfg.selectors.buttons.confirm).click();
  await page.waitForTimeout(3000);
  console.log('✅ 定时发布已确认');
}

module.exports = { ensureSwitchWithVerify, setSwitches, setPosition, setCover, schedulePublish };
