/**
 * 头条号自动发布 - 图片核验 (v8.0)
 * 在编辑器内核验图片数量、CDN上传、分布、blob残留。
 * config 来自 runtime/_config.json，不硬编码。
 */

async function validateImages(page, cfg) {
  var t = cfg.thresholds.article;
  return await page.evaluate(function(imgsRequired, b1Min, b1Max, b2Min, b2Max, b3Min, b3Max, gapMin, lastExcl, lastNoImg) {
    var pm = document.querySelector('.ProseMirror');
    if (!pm) return { passed: false, error: 'ProseMirror not found', checks: {} };

    var imgDivs = [];
    for (var i = 0; i < pm.children.length; i++) {
      if (pm.children[i].tagName === 'DIV' && pm.children[i].querySelector('img')) {
        imgDivs.push(pm.children[i]);
      }
    }
    var checks = {};

    checks.imageDivCount = imgDivs.length;
    checks.imageDivCountOk = imgDivs.length === imgsRequired;

    var blobCount = 0;
    for (var i = 0; i < pm.children.length; i++) {
      var imgs = pm.children[i].querySelectorAll ? pm.children[i].querySelectorAll('img') : [];
      for (var j = 0; j < imgs.length; j++) {
        if (imgs[j].src && imgs[j].src.startsWith('blob:')) blobCount++;
      }
    }
    checks.blobCount = blobCount;
    checks.blobCountOk = blobCount === 0;

    var cdnSeen = {};
    for (var i = 0; i < pm.children.length; i++) {
      var imgs = pm.children[i].querySelectorAll ? pm.children[i].querySelectorAll('img') : [];
      for (var j = 0; j < imgs.length; j++) {
        var m = imgs[j].src && imgs[j].src.match(/tos-cn-i-[^/]+\/([^~?]+)/);
        if (m) cdnSeen[m[1]] = true;
      }
    }
    checks.cdnImageDivCount = Object.keys(cdnSeen).length;
    checks.cdnImageDivCountOk = Object.keys(cdnSeen).length === imgsRequired;

    var totalNodes = pm.children.length;
    var imgIndices = [];
    for (var i = 0; i < totalNodes; i++) {
      if (pm.children[i].querySelector && pm.children[i].querySelector('img')) imgIndices.push(i);
    }
    var distribution = imgIndices.map(function(idx) {
      return { index: idx, percent: Math.round(idx / totalNodes * 100) };
    });

    var band1 = distribution.filter(function(d){ return d.percent >= b1Min && d.percent < b1Max; }).length;
    var band2 = distribution.filter(function(d){ return d.percent >= b2Min && d.percent < b2Max; }).length;
    var band3 = distribution.filter(function(d){ return d.percent >= b3Min && d.percent <= b3Max; }).length;
    var inLast10 = distribution.filter(function(d){ return d.percent > lastExcl; }).length;

    var gapsOk = true;
    var gapInfo = [];
    for (var g = 1; g < distribution.length; g++) {
      var gap = distribution[g].percent - distribution[g-1].percent;
      gapInfo.push({ from: distribution[g-1].percent, to: distribution[g].percent, gap: gap });
      if (gap < gapMin) gapsOk = false;
    }
    checks.distributionBand1 = band1;
    checks.distributionBand2 = band2;
    checks.distributionBand3 = band3;
    checks.distributionInLast10 = inLast10;
    checks.gapsOk = gapsOk;
    checks.distributionOk = (band1 >= 1 && band2 >= 1 && band3 >= 1 && gapsOk && inLast10 === 0);

    var last3HasImage = false;
    for (var i = Math.max(0, totalNodes - lastNoImg); i < totalNodes; i++) {
      if (pm.children[i].querySelector && pm.children[i].querySelector('img')) last3HasImage = true;
    }
    checks.lastThreeTextParasNoImage = !last3HasImage;

    var sentenceEndRegex = /[。？！.!?]$/;
    var prevParaSentenceOk = true;
    var prevParaFailures = [];
    for (var i = 0; i < totalNodes; i++) {
      if (pm.children[i].querySelector && pm.children[i].querySelector('img')) {
        if (i > 0 && pm.children[i-1].tagName === 'P') {
          var prevText = pm.children[i-1].textContent || '';
          if (!sentenceEndRegex.test(prevText.trim())) {
            prevParaSentenceOk = false;
            prevParaFailures.push('img at index ' + i + ': prev P does not end with sentence end');
          }
        }
      }
    }
    checks.previousParagraphEndsSentence = prevParaSentenceOk;
    checks.previousParagraphFailures = prevParaFailures;

    var passed = checks.imageDivCountOk && checks.blobCountOk && checks.cdnImageDivCountOk &&
                 checks.distributionOk && checks.lastThreeTextParasNoImage && prevParaSentenceOk;

    var failures = [];
    if (!checks.imageDivCountOk) failures.push('imageDivCount=' + checks.imageDivCount);
    if (!checks.blobCountOk) failures.push('blobCount=' + checks.blobCount);
    if (!checks.cdnImageDivCountOk) failures.push('cdnImageDivCount=' + checks.cdnImageDivCount);
    if (!checks.distributionOk) failures.push('distribution fail');
    if (!checks.lastThreeTextParasNoImage) failures.push('last3HasImage');
    if (!prevParaSentenceOk) failures.push('prevParaNotSentence');

    return { passed: passed, checks: checks, distribution: distribution, failures: failures };
  }, t.images_required, t.image_distribution_bands.band1_min, t.image_distribution_bands.band1_max,
     t.image_distribution_bands.band2_min, t.image_distribution_bands.band2_max,
     t.image_distribution_bands.band3_min, t.image_distribution_bands.band3_max,
     t.image_gap_min_pct, t.image_last_exclusion_pct, t.last_paras_no_image);
}

async function relocateImages(page) {
  return await page.evaluate(function() {
    var pm = document.querySelector('.ProseMirror');
    if (!pm) return { error: 'no pm' };
    var imgDivs = [];
    for (var i = 0; i < pm.children.length; i++) {
      if (pm.children[i].tagName === 'DIV' && pm.children[i].querySelector('img')) imgDivs.push(pm.children[i]);
    }
    if (imgDivs.length !== 3) return { error: 'imgDivs=' + imgDivs.length };
    var textParas = [];
    for (var i = 0; i < pm.children.length; i++) {
      if (pm.children[i].tagName === 'P' && !pm.children[i].querySelector('img')) textParas.push(pm.children[i]);
    }
    if (textParas.length < 10) return { error: 'paras=' + textParas.length };
    var n = textParas.length;
    var targets = [Math.floor(n*0.25)-1, Math.floor(n*0.50)-1, Math.floor(n*0.75)-1];
    for (var t = 1; t < targets.length; t++) {
      if (targets[t] <= targets[t-1]) targets[t] = targets[t-1] + 2;
    }
    if (targets[2] >= n) targets[2] = n - 1;
    for (var k = imgDivs.length - 1; k >= 0; k--) {
      var tp = textParas[targets[k]];
      if (tp) tp.insertAdjacentElement('afterend', imgDivs[k]);
    }
    pm.dispatchEvent(new Event('input', {bubbles: true}));
    return { targets: targets, textParaCount: n, ok: true };
  });
}

async function clearImageDivs(page) {
  return await page.evaluate(function() {
    var pm = document.querySelector('.ProseMirror');
    if (!pm) return { cleared: 0 };
    var removed = 0;
    for (var i = pm.children.length - 1; i >= 0; i--) {
      if (pm.children[i].tagName === 'DIV' && pm.children[i].querySelector('img')) {
        pm.children[i].remove(); removed++;
      }
    }
    pm.dispatchEvent(new Event('input', {bubbles: true}));
    return { cleared: removed };
  });
}

module.exports = { validateImages, relocateImages, clearImageDivs };
