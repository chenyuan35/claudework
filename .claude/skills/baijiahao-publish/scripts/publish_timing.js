// 🔴 定时发布脚本 v9.1（2026-07-26 修复：补写 sessionStorage 供 verify_submission 使用）
// 🔴 三步：点主按钮 → 点弹窗确认 → 验证跳转 → 写验收凭据
// 🔴 不操作 React DOM
// 执行方式：mcp__playwright__browser_evaluate 包进 async () => {...} 注入

(async () => {
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const $$ = (sel) => Array.from(document.querySelectorAll(sel));
  const $ = (sel) => document.querySelector(sel);

  // 0. 读取标题用于验收凭据
  const titleInput = Array.from(document.querySelectorAll('div[contenteditable="true"]'))
    .find((el) => el.getClientRects().length > 0);
  const publishedTitle = titleInput ? titleInput.textContent.trim() : '';

  function reactClick(el) {
    if (!el) return;
    el.click();
    const rect = el.getBoundingClientRect();
    const x = rect.left + rect.width / 2;
    const y = rect.top + rect.height / 2;
    const opts = { bubbles: true, cancelable: true, composed: true, clientX: x, clientY: y, pointerType: 'mouse' };
    el.dispatchEvent(new PointerEvent('pointerdown', opts));
    el.dispatchEvent(new PointerEvent('pointerup', opts));
    el.dispatchEvent(new MouseEvent('mousedown', opts));
    el.dispatchEvent(new MouseEvent('mouseup', opts));
    el.dispatchEvent(new MouseEvent('click', opts));
  }

  // 1. 点主"定时发布"按钮
  const mainBtn = $$('button').find((b) => (b.textContent || '').trim() === '定时发布');
  if (!mainBtn) throw new Error('BJH_PUBLISH_FAILED:stage=no_main_btn');
  reactClick(mainBtn);

  // 2. 等弹窗出现
  await sleep(2000);
  let waited = 0;
  while (waited < 10000 && !$('.cheetah-modal')) {
    await sleep(500);
    waited += 500;
  }
  if (!$('.cheetah-modal')) throw new Error('BJH_PUBLISH_FAILED:stage=no_dialog');

  // 3. 点弹窗内"定时发布"确认按钮
  const confirmBtn = $$('.cheetah-modal button').find((b) => (b.textContent || '').trim() === '定时发布');
  if (!confirmBtn) throw new Error('BJH_PUBLISH_FAILED:stage=no_confirm_btn');
  reactClick(confirmBtn);

  // 4. 验证跳转到投稿页
  await sleep(3000);
  let jumped = false;
  for (let i = 0; i < 16; i += 1) {
    if (/builder\/rc\/clue/.test(location.href)) { jumped = true; break; }
    await sleep(500);
  }
  if (!jumped) throw new Error('BJH_PUBLISH_FAILED:stage=no_redirect');

  // 5. 写验收凭据供 verify_submission.js 使用
  if (publishedTitle) {
    sessionStorage.setItem('bjh_published_title', publishedTitle);
    sessionStorage.setItem('bjh_published_schedule', new Date().toISOString());
  }

  return { status: 'published', url: location.href };
})();
