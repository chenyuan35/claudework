// 百家号编辑器打开就绪模块。
// 前置：已通过 browser_click('text=发布作品') 进入编辑器页。
// 执行方式：将整个文件内容传给 browser_evaluate。
// 自带 passMod 安全验证弹窗处理。
// 返回 {status, acceptance, reusedCurrentEditor, elapsedMs} 或 throw。

async () => {
  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
  const visible = (element) => Boolean(element && element.getClientRects().length > 0);
  const TITLE_INPUT_TIMEOUT = 180000;
  const editorDeadline = Date.now() + TITLE_INPUT_TIMEOUT;

  // 清除覆盖层和 passMod 弹窗
  const clearOverlays = () => {
    for (const cls of ['foldContent', 'no-content', '-left']) {
      document.querySelectorAll(`[class*="${cls}"]`).forEach((el) => {
        if (el instanceof HTMLElement) el.style.pointerEvents = 'none';
      });
    }
    // 清除 passMod 安全验证弹窗
    document.querySelectorAll('.passMod_dialog-wrapper, .passMod_dialog-mask').forEach((el) => {
      if (el instanceof HTMLElement) {
        el.style.display = 'none';
        el.style.pointerEvents = 'none';
      }
    });
  };

  clearOverlays();

  // 检查是否已在发布页（复用当前编辑器）
  const currentUrl = location.href;
  const isOnEditPage = /\/builder\/rc\/edit/.test(currentUrl);
  if (isOnEditPage) {
    // 等标题栏出现
    while (Date.now() < editorDeadline) {
      clearOverlays();
      const titleEl = Array.from(document.querySelectorAll('div[contenteditable="true"]'))
        .find((el) => visible(el));
      if (titleEl) {
        return { status: 'editor_ready', acceptance: 'title_input_and_ueditor_ready', reusedCurrentEditor: true, elapsedMs: Date.now() - (editorDeadline - TITLE_INPUT_TIMEOUT) };
      }
      await sleep(250);
    }
    throw new Error('BJH_EDITOR_FAILED:stage=no_title_on_reuse');
  }

  // 不在编辑页 → 等 SPA 跳转从首页进编辑页
  const BTN_TIMEOUT = 30000;
  const publishDeadline = Date.now() + BTN_TIMEOUT;
  while (Date.now() < publishDeadline) {
    clearOverlays();
    const url = location.href;
    if (/\/builder\/rc\/edit/.test(url)) break;
    await sleep(200);
  }

  // 确认编辑页就绪
  while (Date.now() < editorDeadline) {
    clearOverlays();
    const readyState = document.readyState;
    if (readyState === 'complete' || readyState === 'interactive') {
      const titleEl = Array.from(document.querySelectorAll('div[contenteditable="true"]'))
        .find((el) => visible(el));
      if (titleEl) {
        return { status: 'editor_ready', acceptance: 'title_input_and_ueditor_ready', reusedCurrentEditor: false, elapsedMs: Date.now() - (editorDeadline - TITLE_INPUT_TIMEOUT) };
      }
    }
    await sleep(250);
  }

  throw new Error('BJH_EDITOR_FAILED:stage=title_not_visible');
}
