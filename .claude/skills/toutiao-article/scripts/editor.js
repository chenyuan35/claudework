/**
 * 头条号自动发布 - 编辑器操作脚本 (v8.0)
 * 正文写入、清空、二次核验。
 * config 来自 runtime/_config.json，不硬编码。
 *
 * 通过 browser_run_code_unsafe 调用：
 *   const cfg = JSON.parse(require('fs').readFileSync('./runtime/_config.json'));
 *   const { writeBody, clearEditor, verifyBody, getTitleText } = require('./scripts/editor.js');
 *   await writeBody(page, html, cfg);
 */

async function writeBody(page, html, cfg) {
  var sel = cfg.selectors.editor.prose_mirror;
  return await page.evaluate(function(innerHTML, selector) {
    var pm = document.querySelector(selector);
    if (!pm) return { error: 'ProseMirror not found' };
    pm.innerHTML = innerHTML;
    pm.dispatchEvent(new Event('input', {bubbles: true}));
    return { written: true, length: innerHTML.length };
  }, html, sel);
}

async function clearEditor(page, cfg) {
  var sel = cfg.selectors.editor.prose_mirror;
  return await page.evaluate(function(selector) {
    var pm = document.querySelector(selector);
    if (!pm) return { error: 'ProseMirror not found' };
    pm.innerHTML = '';
    pm.dispatchEvent(new Event('input', {bubbles: true}));
    return { cleared: true };
  }, sel);
}

async function clearTitle(page, cfg) {
  var sel = cfg.selectors.editor.title;
  return await page.evaluate(function(selector) {
    var tb = document.querySelector(selector);
    if (!tb) return { error: 'title textarea not found' };
    tb.value = '';
    tb.dispatchEvent(new Event('input', {bubbles: true}));
    return { cleared: true };
  }, sel);
}

async function verifyBody(page, cfg) {
  var sel = cfg.selectors.editor.prose_mirror;
  return await page.evaluate(function(selector) {
    var pm = document.querySelector(selector);
    if (!pm) return { error: 'ProseMirror not found', empty: true };
    var html = pm.innerHTML;
    var text = pm.innerText || '';
    var isEmpty = !text.trim() || text.trim() === '' || html === '<p><br></p>' || html === '';
    return {
      html_length: html.length,
      text_length: text.length,
      empty: isEmpty,
    };
  }, sel);
}

async function getTitleText(page, cfg) {
  var sel = cfg.selectors.editor.title;
  return await page.evaluate(function(selector) {
    var tb = document.querySelector(selector);
    return tb ? tb.value : null;
  }, sel);
}

module.exports = { writeBody, clearEditor, clearTitle, verifyBody, getTitleText };
