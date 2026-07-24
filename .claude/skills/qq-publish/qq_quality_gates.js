/**
 * qq_quality_gates.js — 企鹅号 ExEditor 质量门
 * 注入到浏览器页面 execute，用于 DOM 级质量检查
 *
 * 用法：
 *   // 在 browser_evaluate 中：
 *   const gates = document.createElement('script');
 *   gates.textContent = `...文件全部内容...`;
 *   document.body.appendChild(gates);
 *   // 然后调用 qualityGateHTML / mobileRenderGate 等
 */

(function() {

// ============================================================
// 汉字计数（Unicode Script=Han 属性）
// ============================================================
function hanCount(s) {
  return (String(s).match(/\p{Script=Han}/gu) || []).length;
}

// ============================================================
// 句界拆段（只在完整句号边界拆分）
// ============================================================
function splitPlainParagraphAtSentenceBoundaries(text, softMax, hardMax) {
  softMax = softMax || 9999; // 不再按长度合并，一句一段
  hardMax = hardMax || 150;
  var sentences = String(text).trim().match(/[^。！？!?；;…]+(?:……|[。！？!?；;…]+|$)/g) || [];
  var groups = [];
  for (var i = 0; i < sentences.length; i++) {
    var sentence = sentences[i];
    if (hanCount(sentence) > hardMax) {
      throw new Error('单句超过' + hardMax + '汉字，必须重写，禁止从中切断：' + sentence.slice(0, 40) + '...');
    }
    // 一句一段，不再合并
    groups.push(sentence.trim());
  }
  return groups.filter(function(g) { return g.length > 0; });
}

// ============================================================
// 手机端段落归一化（按句界拆长段）
// ============================================================
function normalizeMobileParagraphs(html) {
  var doc = new DOMParser().parseFromString('<main id="article-root">' + html + '</main>', 'text/html');
  var root = doc.querySelector('#article-root');
  var ps = root.querySelectorAll('p');
  for (var i = 0; i < ps.length; i++) {
    var p = ps[i];
    if (p.hasAttribute('data-body-img') || p.querySelector('img')) continue;
    // 全部段落都拆，不跳过短段
    if (p.children.length) {
      throw new Error('含行内富文本的超长段落禁止自动拆分，需人工按完整句界重写');
    }
    var parts = splitPlainParagraphAtSentenceBoundaries(p.textContent);
    var fragment = doc.createDocumentFragment();
    for (var j = 0; j < parts.length; j++) {
      var np = doc.createElement('p');
      np.textContent = parts[j];
      fragment.appendChild(np);
    }
    p.replaceWith(fragment);
    // re-query because DOM changed
    ps = root.querySelectorAll('p');
  }
  return root.innerHTML;
}

// ============================================================
// DOM 质量门
// ============================================================
function qualityGateHTML(html, opts) {
  opts = opts || {};
  var requireImages = opts.requireImages || false;
  var doc = new DOMParser().parseFromString('<main id="article-root">' + html + '</main>', 'text/html');
  var root = doc.querySelector('#article-root');
  var direct = root.children;
  var paragraphs = root.querySelectorAll('p');
  var textParas = [];
  for (var i = 0; i < paragraphs.length; i++) {
    var p = paragraphs[i];
    if (!p.hasAttribute('data-body-img') && !p.querySelector('img')) {
      textParas.push(p);
    }
  }
  var lengths = textParas.map(function(p) { return hanCount(p.textContent); });
  var sorted = lengths.slice().sort(function(a, b) { return a - b; });
  var median = sorted.length ? (sorted.length % 2 ? sorted[(sorted.length - 1) / 2] : (sorted[sorted.length / 2 - 1] + sorted[sorted.length / 2]) / 2) : 0;
  var totalHan = hanCount(root.textContent);
  var h2s = [];
  for (var i = 0; i < direct.length; i++) {
    if (direct[i].tagName === 'H2') h2s.push(direct[i]);
  }
  var requiredH2 = totalHan < 3600 ? 6 : Math.max(6, Math.ceil(totalHan / 600));
  var imageBlocks = [];
  for (var i = 0; i < direct.length; i++) {
    if (direct[i].hasAttribute('data-body-img')) imageBlocks.push(direct[i]);
  }
  var imgs = imageBlocks.map(function(block) { return block.querySelector('img'); }).filter(Boolean);
  var srcs = imgs.map(function(img) { return img.getAttribute('src') || ''; });
  var ids = imageBlocks.map(function(block) { return block.dataset.bodyImg; }).sort().join(',');

  // 图片边界检查
  var imageBoundaryPass = true;
  for (var i = 0; i < imageBlocks.length; i++) {
    var block = imageBlocks[i];
    var prev = block.previousElementSibling;
    var next = block.nextElementSibling;
    if (block.parentElement !== root) { imageBoundaryPass = false; break; }
    if (!prev || ['P', 'UL', 'OL', 'BLOCKQUOTE'].indexOf(prev.tagName) === -1) { imageBoundaryPass = false; break; }
    if (next && next.tagName === 'H2') { imageBoundaryPass = false; break; }
  }

  // 区块段落检查
  var sectionParas = [];
  var section = null;
  for (var i = 0; i < direct.length; i++) {
    if (direct[i].tagName === 'H2') {
      section = { title: direct[i].textContent.trim(), paras: [] };
      sectionParas.push(section);
    } else if (section && direct[i].tagName === 'P' && !direct[i].hasAttribute('data-body-img') && !direct[i].querySelector('img')) {
      section.paras.push(hanCount(direct[i].textContent));
    }
  }

  // 相邻两段同时 >100
  var adjacentLong = false;
  for (var i = 0; i < lengths.length - 1; i++) {
    if (lengths[i] > 100 && lengths[i + 1] > 100) { adjacentLong = true; break; }
  }

  var checks = [
    ['totalHan>=3000', totalHan >= 3000, totalHan],
    ['h2 count', h2s.length >= requiredH2, h2s.length + '/' + requiredH2],
    ['max para <=150', Math.max(0, lengths) <= 150, Math.max(0, lengths)],
    ['median <=90', median <= 90, median],
    ['>120 ratio <=10%', lengths.filter(function(n) { return n > 120; }).length / lengths.length <= 0.10, lengths.filter(function(n) { return n > 120; }).length + '/' + lengths.length],
    ['no adjacent >100', !adjacentLong, adjacentLong ? 'FAIL' : 'PASS'],
    ['h2 block 4-8 paras + <=50', sectionParas.length >= requiredH2 && sectionParas.every(function(s) { return s.paras.length >= 4 && s.paras.length <= 8 && s.paras.some(function(n) { return n <= 50; }); }),
      sectionParas.map(function(s, i) { return 'h2#' + (i + 1) + ':' + s.paras.join(','); }).join(' | ')],
    ['exactly 3 body images', imageBlocks.length === 3 && imgs.length === 3 && ids === '1,2,3', 'blocks=' + imageBlocks.length + ',img=' + imgs.length + ',ids=' + ids],
    ['image boundary', imageBoundaryPass, imageBoundaryPass ? 'OK' : 'FAIL'],
  ];

  if (requireImages) {
    var allDifferent = new Set(srcs).size === 3;
    var allCDN = srcs.every(function(src) { return /^https?:\/\/inews\.gtimg\.com\//.test(src); });
    var noPlaceholders = html.indexOf('__BODY_IMG_') === -1;
    checks.push(['all CDN + no placeholders', allDifferent && allCDN && noPlaceholders, srcs.join(' | ')]);
  }

  var failed = checks.filter(function(c) { return !c[1]; });
  return {
    pass: failed.length === 0,
    totalHan: totalHan,
    h2: h2s.length,
    paragraphs: lengths.length,
    median: median,
    checks: checks,
    failed: failed
  };
}

// ============================================================
// 390px 手机端渲染门
// ============================================================
function mobileRenderGate(html) {
  return new Promise(function(resolve) {
    var box = document.createElement('main');
    box.style.cssText = 'position:absolute;left:-100000px;top:0;visibility:hidden;width:358px;box-sizing:border-box;font-size:17px;line-height:1.75;word-break:break-word';
    var computedFont = getComputedStyle(document.body).fontFamily;
    box.style.fontFamily = computedFont;
    box.innerHTML = html;
    var allP = box.querySelectorAll('p');
    for (var i = 0; i < allP.length; i++) {
      allP[i].style.margin = '0 0 1em';
    }
    var allImg = box.querySelectorAll('img');
    for (var i = 0; i < allImg.length; i++) {
      allImg[i].style.width = '100%';
      allImg[i].style.height = 'auto';
    }
    document.body.appendChild(box);
    requestAnimationFrame(function() {
      requestAnimationFrame(function() {
        var rows = [];
        var textPs = box.querySelectorAll('p');
        for (var i = 0; i < textPs.length; i++) {
          var p = textPs[i];
          if (p.hasAttribute('data-body-img') || p.querySelector('img')) continue;
          var lh = parseFloat(getComputedStyle(p).lineHeight);
          var h = p.getBoundingClientRect().height;
          rows.push({ index: i + 1, lines: Math.max(1, Math.round(h / lh)), text: p.textContent.trim().slice(0, 30) });
        }
        var over8 = rows.filter(function(r) { return r.lines > 8; });
        var adjacentOver5 = false;
        for (var i = 0; i < rows.length - 1; i++) {
          if (rows[i].lines > 5 && rows[i + 1].lines > 5) { adjacentOver5 = true; break; }
        }
        box.remove();
        resolve({ pass: over8.length === 0 && !adjacentOver5, over8: over8, adjacentOver5: adjacentOver5, rows: rows });
      });
    });
  });
}

// ============================================================
// 语义卡点检查（辅助用，非自动）
// ============================================================
function semanticCheckPrompt(title, hook, imagePlans, infoIncrements) {
  return {
    title: title,
    hook: hook,
    images: imagePlans,
    infoIncrements: infoIncrements,
    consistencyCheck: 'Title-core-hook must be consistent. Verify each image is placed near its related h2.'
  };
}

// Export
window.qqGates = {
  hanCount: hanCount,
  splitPlainParagraphAtSentenceBoundaries: splitPlainParagraphAtSentenceBoundaries,
  normalizeMobileParagraphs: normalizeMobileParagraphs,
  qualityGateHTML: qualityGateHTML,
  mobileRenderGate: mobileRenderGate,
  semanticCheckPrompt: semanticCheckPrompt
};

})();
