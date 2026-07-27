// 百家号首页准备模块。
// 前置：已通过 browser_navigate 打开 https://baijiahao.baidu.com。
// 执行方式：将整个文件内容传给 browser_evaluate。
// 自带 passMod 安全验证弹窗处理。
// 返回 {status, acceptance} 或 throw。

async () => {
  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
  const visible = (element) => Boolean(element && element.getClientRects().length > 0);
  const deadline = Date.now() + 30000;

  while (document.readyState !== 'complete' && Date.now() < deadline) await sleep(250);
  if (document.readyState !== 'complete') throw new Error('BJH_HOME_FAILED:stage=page_timeout');

  // 清除覆盖层（侧栏等）
  for (const selector of ['[class*="foldContent"]', '[class*="no-content"]', '[class*="-left"]']) {
    document.querySelectorAll(selector).forEach((element) => {
      if (element instanceof HTMLElement) element.style.pointerEvents = 'none';
    });
  }

  // 清除 passMod 安全验证弹窗（如果出现）
  const dismissPassMod = () => {
    const wrappers = document.querySelectorAll('.passMod_dialog-wrapper, .passMod_dialog-mask');
    wrappers.forEach((el) => {
      if (el instanceof HTMLElement) {
        el.style.display = 'none';
        el.style.pointerEvents = 'none';
      }
    });
  };
  dismissPassMod();

  let publishButton = null;
  while (Date.now() < deadline) {
    // 每次循环再扫一次弹窗
    dismissPassMod();
    publishButton = Array.from(document.querySelectorAll('button, a, div, span'))
      .find((element) => visible(element) && (element.textContent || '').trim() === '发布作品') || null;
    if (publishButton) break;
    await sleep(250);
  }
  if (!publishButton) throw new Error('BJH_HOME_FAILED:stage=no_publish_button');
  return { status: 'home_ready', acceptance: 'publish_button_visible' };
}
