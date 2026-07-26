// 百家号投稿列表验收模块。
// 前置：publish_timing.js 已返回 scheduled。
// 执行方式：将整个文件内容传给 browser_evaluate。

async () => {
  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
  const title = sessionStorage.getItem('bjh_published_title') || '';
  const scheduledTime = sessionStorage.getItem('bjh_published_schedule') || '';
  if (!title || !scheduledTime) throw new Error('BJH_VERIFY_FAILED:stage=receipt_missing');

  const deadline = Date.now() + 15000;
  let bodyText = '';
  while (Date.now() < deadline) {
    bodyText = (document.body.textContent || '').replace(/\s+/g, ' ');
    if (bodyText.includes(title) && /审核中|正在审核|已发布|待发布|定时发布/.test(bodyText)) break;
    await sleep(250);
  }
  if (!bodyText.includes(title)) throw new Error('BJH_VERIFY_FAILED:stage=title_missing');
  const status = (bodyText.match(/审核中|正在审核|已发布|待发布|定时发布/) || [])[0];
  if (!status) throw new Error('BJH_VERIFY_FAILED:stage=status_missing');
  return {
    status: 'submission_verified',
    title,
    scheduledTime,
    platformStatus: status,
    url: location.href,
  };
}
