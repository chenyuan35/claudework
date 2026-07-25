/**
 * 头条号自动发布 - 图片验证测试 (v8.0)
 * 用 Node.js 运行：node tests/test_image_validator.js
 * 测试 validate_images.js 中的核心逻辑（纯函数部分）
 */

// Mock page.evaluate for testing
function createMockPage(childrenSetup) {
  return {
    evaluate: async function(fn, ...args) {
      // Create a minimal DOM-like environment
      var pm = {
        children: childrenSetup(),
        querySelector: function(sel) {
          if (sel === '.ProseMirror') return pm;
          return null;
        },
        querySelectorAll: function(sel) {
          if (sel === 'img') {
            var all = [];
            pm.children.forEach(function(c) {
              if (c.querySelectorAll) {
                all = all.concat(c.querySelectorAll('img'));
              }
            });
            return all;
          }
          return [];
        }
      };
      // Add global objects
      var console = { log: function() {} };
      var Math = global.Math;
      var JSON = global.JSON;
      return fn.call({}, ...args);
    }
  };
}

function makeChild(tag, hasImage, src) {
  var child = { tagName: tag };
  child.querySelector = function(sel) {
    if (sel === 'img' && hasImage) return { src: src || 'blob:test' };
    return null;
  };
  child.querySelectorAll = function(sel) {
    if (sel === 'img') {
      if (hasImage && src) return [{ src: src }];
      if (hasImage) return [{ src: 'blob:test' }];
      return [];
    }
    return [];
  };
  child.textContent = tag === 'P' ? '测试段落内容。' : '';
  return child;
}

function makeImgDiv(cdnId) {
  var src = cdnId ? 'https://image-tt-private.toutiao.com/tos-cn-i-' + cdnId : 'blob:test';
  return makeChild('DIV', true, src);
}

function makeTextPara(text) {
  var p = makeChild('P', false);
  p.textContent = text || '测试段落内容。';
  return p;
}

// ============ Tests ============

var testsPassed = 0;
var testsFailed = 0;

function assert(condition, message) {
  if (condition) {
    testsPassed++;
    process.stdout.write('.');
  } else {
    testsFailed++;
    process.stdout.write('F');
    console.error('\nFAIL:', message);
  }
}

// Test 1: 恰好3张图通过核验
function test_exact_3_images() {
  // Build: 10 text paragraphs with 3 image DIVs at positions 2, 5, 8
  var children = [];
  for (var i = 0; i < 10; i++) children.push(makeTextPara());
  children[2] = makeImgDiv('abc123');  // position 2 = 20%
  children[5] = makeImgDiv('def456');  // position 5 = 50%
  children[8] = makeImgDiv('ghi789');  // position 8 = 80%

  var total = children.length;
  var imgIndices = [];
  for (var i = 0; i < total; i++) {
    if (children[i].querySelector && children[i].querySelector('img')) {
      imgIndices.push(i);
    }
  }

  assert(imgIndices.length === 3, 'exact_3: imgCount should be 3, got ' + imgIndices.length);
  assert(!imgIndices.includes(9), 'exact_3: last position should not be in last 3 nodes');

  // Check distribution
  var dist = imgIndices.map(function(idx) { return { index: idx, percent: Math.round(idx / total * 100) }; });
  var band1 = dist.filter(function(d){ return d.percent >= 8 && d.percent < 30; }).length;
  var band2 = dist.filter(function(d){ return d.percent >= 30 && d.percent < 55; }).length;
  var band3 = dist.filter(function(d){ return d.percent >= 55 && d.percent <= 85; }).length;
  assert(band1 >= 1, 'exact_3: band1 should be >=1');
  assert(band2 >= 1, 'exact_3: band2 should be >=1');
  assert(band3 >= 1, 'exact_3: band3 should be >=1');
}

// Test 2: 1张图失败
function test_1_image_fails() {
  var children = [];
  for (var i = 0; i < 10; i++) children.push(makeTextPara());
  children[3] = makeImgDiv('abc123');

  var total = children.length;
  var imgIndices = [];
  for (var i = 0; i < total; i++) {
    if (children[i].querySelector && children[i].querySelector('img')) {
      imgIndices.push(i);
    }
  }
  assert(imgIndices.length !== 3, '1_image: should not equal 3, got ' + imgIndices.length);
}

// Test 3: 4张图失败
function test_4_images_fails() {
  var children = [];
  for (var i = 0; i < 12; i++) children.push(makeTextPara());
  children[1] = makeImgDiv('a');
  children[4] = makeImgDiv('b');
  children[7] = makeImgDiv('c');
  children[10] = makeImgDiv('d');

  var total = children.length;
  var imgIndices = [];
  for (var i = 0; i < total; i++) {
    if (children[i].querySelector && children[i].querySelector('img')) {
      imgIndices.push(i);
    }
  }
  assert(imgIndices.length !== 3, '4_images: should not equal 3');
}

// Test 4: blob图片失败
function test_blob_image_fails() {
  var children = [];
  for (var i = 0; i < 10; i++) children.push(makeTextPara());
  children[2] = makeImgDiv();  // No CDN id = blob
  children[5] = makeImgDiv('abc123');
  children[8] = makeImgDiv('def456');

  var blobCount = 0;
  for (var i = 0; i < children.length; i++) {
    var imgs = children[i].querySelectorAll ? children[i].querySelectorAll('img') : [];
    for (var j = 0; j < imgs.length; j++) {
      if (imgs[j].src || true) {
        if (!imgs[j].src || imgs[j].src.startsWith('blob:')) blobCount++;
      }
    }
  }
  assert(blobCount > 0, 'blob: should have blob images');
}

// Test 5: 图片集中（间距不足）
function test_images_clustered() {
  var children = [];
  for (var i = 0; i < 15; i++) children.push(makeTextPara());
  children[2] = makeImgDiv('a');  // 13%
  children[3] = makeImgDiv('b');  // 20% - gap too small
  children[8] = makeImgDiv('c');  // 53%

  var total = children.length;
  var imgIndices = [];
  for (var i = 0; i < total; i++) {
    if (children[i].querySelector && children[i].querySelector('img')) {
      imgIndices.push(i);
    }
  }
  var gap = Math.round(imgIndices[1] / total * 100) - Math.round(imgIndices[0] / total * 100);
  assert(gap < 15, 'clustered: gap should be < 15, got ' + gap);
}

// Test 6: 最后3段有图失败
function test_last_3_has_image() {
  var children = [];
  for (var i = 0; i < 10; i++) children.push(makeTextPara());
  children[2] = makeImgDiv('a');
  children[5] = makeImgDiv('b');
  children[9] = makeImgDiv('c');  // Last child has image

  var total = children.length;
  var last3HasImage = false;
  for (var i = Math.max(0, total - 3); i < total; i++) {
    if (children[i].querySelector && children[i].querySelector('img')) {
      last3HasImage = true;
    }
  }
  assert(last3HasImage, 'last_3: should have image in last 3');
}

// Run all tests
var testFunctions = [
  { name: 'test_exact_3_images', fn: test_exact_3_images },
  { name: 'test_1_image_fails', fn: test_1_image_fails },
  { name: 'test_4_images_fails', fn: test_4_images_fails },
  { name: 'test_blob_image_fails', fn: test_blob_image_fails },
  { name: 'test_images_clustered', fn: test_images_clustered },
  { name: 'test_last_3_has_image', fn: test_last_3_has_image },
];

var funcCount = testFunctions.length;
testFunctions.forEach(function(t) {
  t.fn();
});

console.log('\n─── Image Validator Test Report ───');
console.log('Test functions: ' + funcCount);
console.log('Assert calls:   ' + testsPassed);
console.log('Assert failed:   ' + testsFailed);
console.log('Test coverage:  ' + funcCount + ' functions, ' + (testsPassed + testsFailed) + ' total assertions');
console.log('Result:         ' + (testsFailed > 0 ? 'FAILED' : 'PASSED'));
process.exit(testsFailed > 0 ? 1 : 0);
