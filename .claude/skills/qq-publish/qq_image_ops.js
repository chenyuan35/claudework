/**
 * qq_image_ops.js — 企鹅号 ExEditor 图片操作
 * 注入到浏览器页面 execute，用于上传、绑定、坐标优化
 *
 * 用法：
 *   // 在 browser_evaluate 中：
 *   const ops = document.createElement('script');
 *   ops.textContent = `...文件全部内容...`;
 *   document.body.appendChild(ops);
 *   // 然后调用 uploadOneBodyImage / bindBodyImageSources 等
 */

(function() {

// ============================================================
// 单张正文图上传并捕获新增 URL（DataTransfer 注入）
// ============================================================
async function uploadOneBodyImage(fileName) {
  var pm = document.querySelector('.ProseMirror');
  if (!pm) throw new Error('未找到 .ProseMirror');
  var before = new Set();
  pm.querySelectorAll('img').forEach(function(img) { before.add(img.src); });
  pm.focus();

  // 找到可见的 file input（由 Playwright 先点击「插入图片」+「本地上传」触发）
  var inputs = document.querySelectorAll('.omui-upload-image-trigger input[type=file]');
  var fileInput = null;
  for (var i = 0; i < inputs.length; i++) {
    if (inputs[i].offsetParent !== null) { fileInput = inputs[i]; break; }
  }
  if (!fileInput) throw new Error('未找到可见的正文图片 file input');

  var response = await fetch('http://127.0.0.1:8768/' + fileName);
  if (!response.ok) throw new Error(fileName + ' CORS读取失败：' + response.status);
  var file = new File([await response.blob()], fileName, { type: 'image/jpeg' });
  var dt = new DataTransfer();
  dt.items.add(file);
  Object.defineProperty(fileInput, 'files', { value: dt.files, configurable: true });
  fileInput.dispatchEvent(new Event('change', { bubbles: true }));

  // 等待新图加载（Playwright 点缩略图 + 确认后由浏览器等待）
  var deadline = Date.now() + 15000;
  while (Date.now() < deadline) {
    var added = null;
    pm.querySelectorAll('img').forEach(function(img) {
      if (!before.has(img.src) && /^https?:\/\/inews\.gtimg\.com\//.test(img.src) && img.naturalWidth > 0) {
        added = img.src;
      }
    });
    if (added) return added;
    await new Promise(function(r) { setTimeout(r, 300); });
  }
  throw new Error(fileName + ' 上传后未取得新的腾讯图床 URL');
}

// ============================================================
// 绑定图片源（替换占位符为腾讯图床 URL）
// ============================================================
function bindBodyImageSources(htmlWithPlaceholders, sources, locks) {
  locks = locks || [2, 3, 5];
  if (!Array.isArray(sources) || sources.length !== 3 || new Set(sources).size !== 3) {
    throw new Error('正文图源必须恰好3个且互不相同');
  }
  if (!sources.every(function(src) { return /^https?:\/\/inews\.gtimg\.com\//.test(src); })) {
    throw new Error('正文图源必须全部来自 inews.gtimg.com');
  }
  var doc = new DOMParser().parseFromString('<main id="article-root">' + htmlWithPlaceholders + '</main>', 'text/html');
  var root = doc.querySelector('#article-root');
  for (var id = 1; id <= 3; id++) {
    var srcMarker = '__BODY_IMG_' + id + '__';
    var imgs = root.querySelectorAll('img');
    var targetImg = null;
    for (var i = 0; i < imgs.length; i++) {
      if (imgs[i].getAttribute('src') === srcMarker) { targetImg = imgs[i]; break; }
    }
    if (!targetImg) throw new Error('缺少 IMG' + id + ' 占位符');
    targetImg.src = sources[id - 1];
    if (!targetImg.alt || targetImg.alt.indexOf('BODY_IMG_' + id) === -1) {
      targetImg.alt = 'BODY_IMG_' + id + '|img' + id;
    }

    // 确保图片被 <p> 包裹且是根级直接子节点
    if (targetImg.parentElement !== root) {
      var block = targetImg;
      while (block.parentElement && block.parentElement !== root) block = block.parentElement;
      if (block === targetImg) {
        var wrapper = doc.createElement('p');
        targetImg.replaceWith(wrapper);
        wrapper.appendChild(targetImg);
        block = wrapper;
      }
    }
    block = targetImg.parentElement;
    if (block === root) {
      var wrapper = doc.createElement('p');
      targetImg.replaceWith(wrapper);
      wrapper.appendChild(targetImg);
      block = wrapper;
    }
    block.className = 'body-image';
    block.dataset.bodyImg = String(id);
    block.dataset.lockH2 = String(locks[id - 1]);
  }
  return root.innerHTML;
}

// ============================================================
// 渲染坐标优化——隐藏副本枚举 safe 位置
// ============================================================
async function optimizeBodyImagePositions(pm, sourceHTML, options) {
  options = options || {};
  var targets = options.targets || { '1': 0.25, '2': 0.50, '3': 0.75 };
  var tolerance = options.tolerance || 0.10;
  var rounds = options.rounds || 2;

  var doc = new DOMParser().parseFromString('<main id="article-root">' + sourceHTML + '</main>', 'text/html');
  var root = doc.querySelector('#article-root');
  var imageBlocks = [];
  for (var i = 0; i < root.children.length; i++) {
    if (root.children[i].hasAttribute('data-body-img')) imageBlocks.push(root.children[i]);
  }
  imageBlocks.sort(function(a, b) { return Number(a.dataset.bodyImg) - Number(b.dataset.bodyImg); });
  if (imageBlocks.length !== 3) throw new Error('正文图必须恰好3张');

  // 创建隐藏预览
  var preview = pm.cloneNode(false);
  preview.removeAttribute('contenteditable');
  preview.style.cssText = 'position:absolute;left:-100000px;top:0;visibility:hidden;pointer-events:none;height:auto;overflow:visible;width:' + pm.getBoundingClientRect().width + 'px';
  document.body.appendChild(preview);

  function waitLayout() {
    return new Promise(function(resolve) {
      var promises = [];
      preview.querySelectorAll('img').forEach(function(img) {
        if (img.complete && img.naturalWidth > 0) return;
        promises.push(new Promise(function(res) {
          img.addEventListener('load', res, { once: true });
          img.addEventListener('error', res, { once: true });
          setTimeout(res, 5000);
        }));
      });
      Promise.all(promises).then(function() {
        requestAnimationFrame(function() { requestAnimationFrame(resolve); });
      });
    });
  }

  async function renderRatio(id) {
    preview.innerHTML = root.innerHTML;
    await waitLayout();
    var articleRect = preview.getBoundingClientRect();
    var block = preview.querySelector('[data-body-img="' + id + '"]');
    if (!block || articleRect.height <= 0) throw new Error('无法测量IMG' + id);
    var rect = block.getBoundingClientRect();
    return (rect.top + rect.height / 2 - articleRect.top) / articleRect.height;
  }

  function candidateAnchors(imageBlock) {
    var allowed = String(imageBlock.dataset.lockH2 || '').split(',').map(Number).filter(Boolean);
    if (!allowed.length) throw new Error('IMG' + imageBlock.dataset.bodyImg + ' 缺少 data-lock-h2');
    var h2Index = 0;
    var candidates = [];
    for (var i = 0; i < root.children.length; i++) {
      var el = root.children[i];
      if (el.tagName === 'H2') { h2Index++; continue; }
      if (allowed.indexOf(h2Index) === -1) continue;
      if (['P', 'UL', 'OL', 'BLOCKQUOTE'].indexOf(el.tagName) === -1 || el.hasAttribute('data-body-img') || el.querySelector('img')) continue;
      var nextText = el.nextElementSibling;
      while (nextText && nextText.hasAttribute('data-body-img')) nextText = nextText.nextElementSibling;
      if (nextText && nextText.tagName === 'H2') continue;
      candidates.push(el);
    }
    return candidates;
  }

  try {
    for (var round = 0; round < rounds; round++) {
      for (var bi = 0; bi < imageBlocks.length; bi++) {
        var ib = imageBlocks[bi];
        var id = ib.dataset.bodyImg;
        var anchors = candidateAnchors(ib);
        if (!anchors.length) throw new Error('IMG' + id + ' 的相关h2内没有安全插入点');
        var best = null;
        for (var ai = 0; ai < anchors.length; ai++) {
          anchors[ai].after(ib);
          var actual = await renderRatio(id);
          var error = Math.abs(actual - targets[id]);
          if (!best || error < best.error) best = { anchor: anchors[ai], actual: actual, error: error };
        }
        best.anchor.after(ib);
      }
    }
    preview.innerHTML = root.innerHTML;
    await waitLayout();
    var articleRect = preview.getBoundingClientRect();
    var report = imageBlocks.map(function(ib) {
      var id = ib.dataset.bodyImg;
      var mirror = preview.querySelector('[data-body-img="' + id + '"]');
      var rect = mirror.getBoundingClientRect();
      var actual = (rect.top + rect.height / 2 - articleRect.top) / articleRect.height;
      return { img: 'IMG' + id, target: targets[id], actual: actual, error: Math.abs(actual - targets[id]), pass: Math.abs(actual - targets[id]) <= tolerance };
    });
    return { html: root.innerHTML, report: report };
  } finally {
    preview.remove();
  }
}

// ============================================================
// 实际 ProseMirror 图片门（检查已插入内容）
// ============================================================
function liveImageGate(pm, tolerance) {
  tolerance = tolerance || 0.10;
  var targets = [0.25, 0.50, 0.75];
  var imgs = pm.querySelectorAll('img');
  var articleRect = pm.getBoundingClientRect();
  var srcs = [];
  var blocks = [];
  for (var i = 0; i < imgs.length; i++) {
    var img = imgs[i];
    srcs.push(img.src || '');
    var block = img;
    while (block.parentElement && block.parentElement !== pm) block = block.parentElement;
    blocks.push(block);
  }
  var report = [];
  for (var i = 0; i < blocks.length; i++) {
    var rect = blocks[i].getBoundingClientRect();
    var actual = (rect.top + rect.height / 2 - articleRect.top) / articleRect.height;
    report.push({ img: i + 1, actual: actual, target: targets[i], error: Math.abs(actual - targets[i]), loaded: imgs[i] && imgs[i].naturalWidth > 0 });
  }
  var boundaryPass = blocks.length === 3 && new Set(blocks).size === 3;
  if (boundaryPass) {
    for (var i = 0; i < blocks.length; i++) {
      var prev = blocks[i].previousElementSibling;
      var next = blocks[i].nextElementSibling;
      if (blocks[i].parentElement !== pm) { boundaryPass = false; break; }
      if (!prev || ['P', 'UL', 'OL', 'BLOCKQUOTE'].indexOf(prev.tagName) === -1) { boundaryPass = false; break; }
      if (next && next.tagName === 'H2') { boundaryPass = false; break; }
    }
  }
  var pass = imgs.length === 3 && new Set(srcs).size === 3 &&
    srcs.every(function(s) { return /^https?:\/\/inews\.gtimg\.com\//.test(s); }) &&
    boundaryPass && report.every(function(r) { return r.loaded && r.error <= tolerance; });
  return { pass: pass, report: report, srcs: srcs, boundaryPass: boundaryPass };
}

// ============================================================
// 整篇单次插入 + 两轮优化
// ============================================================
async function insertArticleWithTwoPassLimit(pm, rawHTML) {
  var html = rawHTML;

  // 第一轮插入
  for (var attempt = 1; attempt <= 2; attempt++) {
    var optResult = await optimizeBodyImagePositions(pm, html);
    html = optResult.html;

    pm.focus();
    var range = document.createRange();
    range.selectNodeContents(pm);
    var sel = window.getSelection();
    sel.removeAllRanges();
    sel.addRange(range);
    document.execCommand('delete');
    if (!document.execCommand('insertHTML', false, html)) throw new Error('整篇 insertHTML 失败');
    pm.dispatchEvent(new Event('input', { bubbles: true }));
    await new Promise(function(r) { requestAnimationFrame(function() { requestAnimationFrame(r); }); });

    var live = liveImageGate(pm);
    if (live.pass) return { pass: true, attempt: attempt, optimized: optResult.report, live: live };

    if (attempt === 2) throw new Error('实际图片门两轮仍FAIL：' + JSON.stringify(live));

    // 恢复标记后重试
    html = rehydrateImageMarkers(pm.innerHTML);
  }
}

// ============================================================
// 重水合图片标记（ProseMirror 可能剥离 data-* 属性）
// ============================================================
function rehydrateImageMarkers(editorHTML, locks) {
  locks = locks || [2, 3, 5];
  var doc = new DOMParser().parseFromString('<main id="article-root">' + editorHTML + '</main>', 'text/html');
  var root = doc.querySelector('#article-root');
  var imgs = root.querySelectorAll('img');
  if (imgs.length !== 3) throw new Error('编辑器规范化后图片数不是3：' + imgs.length);
  for (var i = 0; i < imgs.length; i++) {
    var img = imgs[i];
    var block = img;
    while (block.parentElement && block.parentElement !== root) block = block.parentElement;
    block.dataset.bodyImg = String(i + 1);
    block.dataset.lockH2 = String(locks[i]);
    block.className = 'body-image';
    img.alt = img.alt || 'BODY_IMG_' + (i + 1);
  }
  return root.innerHTML;
}

// ============================================================
// OP-2 封面图上传核心
// ============================================================
async function uploadCoverImage() {
  var inputs = document.querySelectorAll('.omui-upload-image-trigger input[type=file]');
  var fileInput = null;
  for (var i = 0; i < inputs.length; i++) {
    if (inputs[i].offsetParent !== null) { fileInput = inputs[i]; break; }
  }
  if (!fileInput) throw new Error('未找到可见的封面 file input');

  var response = await fetch('http://127.0.0.1:8768/cover.jpg');
  if (!response.ok) throw new Error('cover.jpg 读取失败');
  var file = new File([await response.blob()], 'cover.jpg', { type: 'image/jpeg' });
  var dt = new DataTransfer();
  dt.items.add(file);
  Object.defineProperty(fileInput, 'files', { value: dt.files, configurable: true });
  fileInput.dispatchEvent(new Event('change', { bubbles: true }));
  return true;
}

// Export
window.qqImageOps = {
  uploadOneBodyImage: uploadOneBodyImage,
  bindBodyImageSources: bindBodyImageSources,
  optimizeBodyImagePositions: optimizeBodyImagePositions,
  liveImageGate: liveImageGate,
  insertArticleWithTwoPassLimit: insertArticleWithTwoPassLimit,
  rehydrateImageMarkers: rehydrateImageMarkers,
  uploadCoverImage: uploadCoverImage
};

})();
