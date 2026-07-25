/**
 * 头条号自动发布 - 发布后列表核验 (v8.0)
 * config 来自 runtime/_config.json，不硬编码。
 */

async function verifyPublished(page, expectedTitle, cfg) {
  var slc = cfg.selectors;

  var currentUrl = page.url();
  if (!currentUrl.includes('/graphic/articles')) {
    return { verified: false, reason: 'URL_NOT_LIST_PAGE: ' + currentUrl };
  }

  var found = await page.evaluate(function(title) {
    var links = document.querySelectorAll('article-item-title a, .article-title a, [class*="title"] a, .title-row a, a.title-link');
    for (var i = 0; i < links.length; i++) {
      if (links[i].textContent.trim() === title) return { found: true, text: links[i].textContent.trim() };
    }
    var body = document.body.innerText;
    if (body.includes(title)) {
      var indicators = ['定时发布', '定时', '已发布', '审核中'];
      var status = 'unknown';
      for (var si = 0; si < indicators.length; si++) {
        if (body.includes(indicators[si])) { status = indicators[si]; break; }
      }
      return { found: true, text: title, status: status, method: 'text_search' };
    }
    return { found: false };
  }, expectedTitle);

  if (found.found) {
    console.log('✅ 列表中找到文章:', found.text, found.status || '');
    return { verified: true, title: expectedTitle, details: found };
  }

  // Retry once
  await page.waitForTimeout(3000);
  await page.evaluate(function() { window.location.reload(); });
  await page.waitForTimeout(5000);

  var foundAfterReload = await page.evaluate(function(title) {
    var body = document.body.innerText;
    if (body.includes(title)) {
      var indicators = ['定时发布', '定时', '已发布', '审核中'];
      var status = 'unknown';
      for (var si = 0; si < indicators.length; si++) {
        if (body.includes(indicators[si])) { status = indicators[si]; break; }
      }
      return { found: true, text: title, status: status };
    }
    return { found: false };
  }, expectedTitle);

  if (foundAfterReload.found) {
    console.log('✅ 刷新后找到文章:', foundAfterReload.text, foundAfterReload.status || '');
    return { verified: true, title: expectedTitle, details: foundAfterReload };
  }

  return { verified: false, reason: 'NOT_FOUND_IN_LIST after refresh' };
}

async function navigateToList(page) {
  await page.goto('https://mp.toutiao.com/profile_v4/manage/content/all');
  await page.waitForTimeout(3000);
  return page.url().includes('/manage/content/all');
}

module.exports = { verifyPublished, navigateToList };
