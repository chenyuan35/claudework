/**
 * semantic_image_pipeline.js — 语义图片管线硬门（v1.0）
 *
 * 注入后调用 window.semanticImagePipeline(pm, cdnUrls, options)
 * 返回 {pass, report, html}，pass=false 则 throw，后续函数不得调用。
 *
 * 流程：离线构建 HTML → 单次 insertHTML → 真实 PM 测量 → 迭代调整（≤3轮）
 * 验收：3图、3个不同CDN、全部naturalWidth>0、三个ratio误差≤0.05
 */

(function() {

const DEFAULT_OPTIONS = {
  targets: { '1': 0.25, '2': 0.50, '3': 0.75 },
  tolerance: 0.05,
  maxRounds: 3,
  lockH2: { '1': 2, '2': 4, '3': 6 }
};

async function semanticImagePipeline(pm, cdnUrls, options) {
  options = Object.assign({}, DEFAULT_OPTIONS, options || {});

  if (!pm) throw new Error('semanticImagePipeline: ProseMirror null');
  if (!Array.isArray(cdnUrls) || cdnUrls.length !== 3) throw new Error('semanticImagePipeline: 需要恰好3个CDN URL');
  if (new Set(cdnUrls).size !== 3) throw new Error('semanticImagePipeline: 3个CDN URL必须互不相同');
  if (!cdnUrls.every(function(u) { return /inews\.gtimg\.com/.test(u); })) throw new Error('semanticImagePipeline: CDN URL必须全部来自 inews.gtimg.com');

  // Step 1: Extract body text from PM
  var text = pm.textContent;

  // Step 2: Build the 6 h2 titles (must match article)
  var h2Titles = findH2Titles(text);
  if (h2Titles.length < 6) throw new Error('semanticImagePipeline: 不足6个h2, 需要先完成正文');

  // Step 3: Build clean HTML with __BODY_IMG markers at initial positions
  // Initial position: after paragraph 2 of h2#2, h2#4, h2#6
  var initialHtml = buildArticleHtml(text, h2Titles, cdnUrls, options.lockH2);

  // Step 4: Iterative optimization loop (≤3 rounds)
  var bestHtml = initialHtml;
  var bestReport = null;
  var bestMaxError = Infinity;

  for (var round = 1; round <= options.maxRounds; round++) {
    // Insert HTML into PM (single shot)
    pm.focus();
    var r = document.createRange(); r.selectNodeContents(pm);
    var sel = window.getSelection(); sel.removeAllRanges(); sel.addRange(r);
    document.execCommand('delete');
    document.execCommand('insertHTML', false, bestHtml);
    pm.dispatchEvent(new Event('input', { bubbles: true }));

    // Wait for layout
    await new Promise(function(resolve) { requestAnimationFrame(function() { requestAnimationFrame(resolve); }); });

    // Measure actual positions in REAL PM
    var measurement = measureImagePositions(pm, options.targets);

    if (!measurement) {
      // PM DOM changed drastically - rebuild from text
      bestHtml = buildArticleHtml(text, h2Titles, cdnUrls, options.lockH2);
      continue;
    }

    var maxError = Math.max.apply(null, measurement.report.map(function(r) { return r.error; }));

    if (maxError < bestMaxError) {
      bestMaxError = maxError;
      bestHtml = pm.innerHTML;
      bestReport = measurement;
    }

    if (maxError <= options.tolerance) {
      // PASS - all images within tolerance
      break;
    }

    // Adjust positions: move images that are off-target
    // Rebuild HTML with adjusted lockH2 targets
    var adjustedLocks = adjustLockH2(measurement.report, h2Titles, options);
    bestHtml = buildArticleHtml(text, h2Titles, cdnUrls, adjustedLocks);
  }

  // If after all rounds no good result, do one final insert with best known HTML
  if (bestReport === null || bestMaxError > options.tolerance) {
    // Final attempt: insert best HTML
    pm.focus();
    var r2 = document.createRange(); r2.selectNodeContents(pm);
    var sel2 = window.getSelection(); sel2.removeAllRanges(); sel2.addRange(r2);
    document.execCommand('delete');
    document.execCommand('insertHTML', false, bestHtml);
    pm.dispatchEvent(new Event('input', { bubbles: true }));
    await new Promise(function(resolve) { requestAnimationFrame(function() { requestAnimationFrame(resolve); }); });
    bestReport = measureImagePositions(pm, options.targets);
  }

  // Build final evidence
  var imgs = pm.querySelectorAll('img');
  var srcs = [];
  var loaded = [];
  imgs.forEach(function(img) {
    if (img.src && img.src.indexOf('inews.gtimg.com') >= 0) {
      srcs.push(img.src);
      loaded.push(img.naturalWidth > 0);
    }
  });

  // Get context (anchor text before and after each image)
  var context = [];
  var imageBlocks = [];
  for (var i = 0; i < pm.children.length; i++) {
    if (pm.children[i].querySelector('img')) imageBlocks.push(pm.children[i]);
  }
  imageBlocks.forEach(function(block) {
    var prev = block.previousElementSibling;
    var next = block.nextElementSibling;
    context.push({
      prevText: prev ? prev.textContent.trim().slice(0, 50) : 'none',
      nextText: next ? next.textContent.trim().slice(0, 50) : 'none',
      prevTag: prev ? prev.tagName : 'none',
      nextTag: next ? next.tagName : 'none'
    });
  });

  var report = {
    pass: bestMaxError <= options.tolerance,
    round: 'done',
    maxError: bestMaxError,
    cdnSrcs: srcs,
    uniqueSrcs: new Set(srcs).size,
    naturalWidths: loaded,
    allLoaded: loaded.every(Boolean),
    positions: bestReport ? bestReport.report : [],
    context: context,
    imageCount: imgs.length
  };

  // Hard gate: fail if any condition not met
  if (srcs.length !== 3) throw new Error('semanticImagePipeline FAIL: 图片数=' + srcs.length + '（需3）');
  if (new Set(srcs).size !== 3) throw new Error('semanticImagePipeline FAIL: CDN src 重复');
  if (!loaded.every(Boolean)) throw new Error('semanticImagePipeline FAIL: 存在未加载图片');
  if (report.maxError > options.tolerance) throw new Error('semanticImagePipeline FAIL: 最大误差=' + report.maxError.toFixed(3) + '（需≤' + options.tolerance + '）');

  return report;
}

// ============================================================
// Internal helpers
// ============================================================

function han(s) {
  return (String(s).match(/[一-鿿豈-﫿]/g) || []).length;
}

function findH2Titles(text) {
  var candidates = [
    '你有多久', '那些陪你', '开黑，从', '有些朋友', '当好友', '游戏里的关系'
  ];
  var fullTitles = [
    '你有多久没跟游戏里的朋友聊天了？',
    '那些陪你刷副本到天亮的人',
    '开黑，从路人变兄弟最快的方式',
    '有些朋友，只在游戏里认识',
    '当好友列表慢慢变灰',
    '游戏里的关系为什么比现实真'
  ];
  var found = [];
  for (var i = 0; i < candidates.length; i++) {
    if (text.indexOf(candidates[i]) >= 0) {
      found.push(fullTitles[i]);
    }
  }
  return found;
}

function buildArticleHtml(text, h2Titles, cdnUrls, lockH2) {
  var html = [];
  for (var i = 0; i < h2Titles.length; i++) {
    html.push('<h2>' + h2Titles[i] + '</h2>');
    var s = text.indexOf(h2Titles[i].slice(0, 5));
    if (s < 0) s = text.indexOf(h2Titles[i]);
    if (s < 0) continue;
    var e = (i + 1 < h2Titles.length) ? text.indexOf(h2Titles[i + 1].slice(0, 5), s + 5) : text.length;
    if (e <= s) e = text.length;
    var sec = text.slice(s + h2Titles[i].length, e).trim();
    var sents = sec.match(/[^。！？]+[。！？]/g) || [sec];
    var cur = '';
    var paraCount = 0;
    for (var j = 0; j < sents.length; j++) {
      var t = cur + sents[j];
      if (t.length > 140 && han(cur) > 20) {
        paraCount++;
        html.push('<p>' + cur.trim() + '</p>');
        cur = sents[j];
      } else { cur = t; }
    }
    if (cur.trim()) { paraCount++; html.push('<p>' + cur.trim() + '</p>'); }

    // Insert CDN image at correct position based on lockH2
    for (var imgId = 1; imgId <= 3; imgId++) {
      if (lockH2[String(imgId)] === i + 1) {
        html.push('<p data-body-img="' + imgId + '" data-lock-h2="' + (i + 1) + '"><img src="' + cdnUrls[imgId - 1] + '"></p>');
      }
    }
  }
  return html.join('\n');
}

function measureImagePositions(pm, targets) {
  var imgs = pm.querySelectorAll('img');
  var cdnImgs = [];
  imgs.forEach(function(img) {
    if (img.src && img.src.indexOf('inews.gtimg.com') >= 0) cdnImgs.push(img);
  });
  if (cdnImgs.length !== 3) return null;

  var pmRect = pm.getBoundingClientRect();
  if (pmRect.height <= 0) return null;

  var report = [];
  cdnImgs.forEach(function(img, idx) {
    var block = img;
    while (block.parentElement && block.parentElement !== pm) block = block.parentElement;
    var rect = block.getBoundingClientRect();
    var actual = (rect.top + rect.height / 2 - pmRect.top) / pmRect.height;
    var targetKey = String(idx + 1);
    var target = targets[targetKey] || (0.25 + idx * 0.25);
    report.push({
      img: 'IMG' + (idx + 1),
      target: target,
      actual: actual,
      error: Math.abs(actual - target),
      loaded: img.naturalWidth > 0,
      src: img.src.slice(0, 60)
    });
  });

  return { report: report };
}

function adjustLockH2(report, h2Titles, options) {
  var locks = {};
  report.forEach(function(r) {
    var id = r.img.replace('IMG', '');
    var targetPct = r.target;
    var actualPct = r.actual;
    var diff = actualPct - targetPct;

    // Current lock h2
    var currentLock = options.lockH2[id] || parseInt(id) + 1;

    if (diff > 0.10) {
      // Image is too far down - move to earlier h2
      locks[id] = Math.max(1, currentLock - 1);
    } else if (diff < -0.10) {
      // Image is too far up - move to later h2
      locks[id] = Math.min(h2Titles.length, currentLock + 1);
    } else {
      locks[id] = currentLock;
    }
  });
  return locks;
}

// Export
window.semanticImagePipeline = semanticImagePipeline;

})();
