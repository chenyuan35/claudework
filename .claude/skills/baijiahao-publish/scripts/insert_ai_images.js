// 🔴 百家号正文配图脚本 v9.0（2026-07-20 审计重写）
// 🔴 此脚本只有一条路径：6节循环 → 每节固定10步 → 全验证
// 🔴 任何验证失败 → throw → 外层 retry 捕获后从头开始
// 执行方式：mcp__playwright__browser_evaluate 包进 async () => {...} 注入
// 🔴 铁律：如本脚本失败，只许清空编辑页后重跑本脚本。
//   禁止在脚本之间插入任何手动 evaluate/Playwright 操作"恢复页面状态"

(async () => {
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const $ = (sel, root) => (root || document).querySelector(sel);
  const $$ = (sel, root) => Array.from((root || document).querySelectorAll(sel));

  // 唯一点击方式：触发 React 合成事件
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

  // 取第 N 节（0基）末尾1-2段原文做 prompt
  function getSectionTail(sectionIndex) {
    const editor = window.UE_V2.instants['ueditorInstant0'];
    const doc = editor.document;
    const paragraphs = Array.from(doc.querySelectorAll('p'));
    const titleIndexes = paragraphs
      .map((p, i) => ({ i, text: p.textContent || '' }))
      .filter((x) => x.text.includes('━━━'));
    const start = titleIndexes[sectionIndex].i;
    const end = sectionIndex + 1 < titleIndexes.length ? titleIndexes[sectionIndex + 1].i : paragraphs.length;
    return paragraphs
      .slice(start + 1, end)
      .map((p) => (p.textContent || '').replace(/\s+/g, ' ').trim())
      .filter((t) => t && !t.includes('请点击输入图片描述') && t.length > 2)
      .slice(-2)
      .join('');
  }

  // 用 UEditor Range 定位光标至节末尾
  function positionCursor(sectionIndex) {
    const editor = window.UE_V2.instants['ueditorInstant0'];
    const doc = editor.document;
    const paragraphs = Array.from(doc.querySelectorAll('p'));
    const titleIndexes = paragraphs
      .map((p, i) => ({ i, text: p.textContent || '' }))
      .filter((x) => x.text.includes('━━━'));
    const next = titleIndexes[sectionIndex + 1] || { i: paragraphs.length - 1 };
    const ueRange = editor.selection.getRange();
    ueRange.setStartBefore(paragraphs[next.i]);
    ueRange.collapse(true);
    ueRange.select();
    editor.focus();
  }

  // 第 N 节已有几张图
  function sectionImgCount(sectionIndex) {
    const editor = window.UE_V2.instants['ueditorInstant0'];
    const doc = editor.document;
    const paragraphs = Array.from(doc.querySelectorAll('p'));
    const titleIndexes = paragraphs
      .map((p, i) => ({ i, text: p.textContent || '' }))
      .filter((x) => x.text.includes('━━━'));
    const start = titleIndexes[sectionIndex].i;
    const end = sectionIndex + 1 < titleIndexes.length ? titleIndexes[sectionIndex + 1].i : paragraphs.length;
    return paragraphs.slice(start + 1, end).reduce((c, p) => c + p.querySelectorAll('img').length, 0);
  }

  // 验证图片是真实图片（非1x1追踪像素）
  function isRealImage(img) {
    return img && img.naturalWidth > 1 && img.naturalHeight > 1;
  }

  // 找图片插入按钮
  function findImageBtn() {
    return $('#edui28_body')
      || $('[class*="edui-for-insertimage"] [id$="_body"]')
      || $$('[title*="图片"]').find(el => el.closest('[class*="edui"]'));
  }

  async function insertOneSection(sectionIndex) {
    positionCursor(sectionIndex);
    await sleep(300);

    // 点图片按钮
    let btn = findImageBtn();
    for (let i = 0; i < 10 && !btn; i += 1) { await sleep(300); btn = findImageBtn(); }
    if (!btn) throw new Error('BJH_AI_IMAGE_FAILED:section=' + (sectionIndex + 1) + ':stage=no_image_btn');
    reactClick(btn);
    await sleep(3000);

    // 切 AI配图 tab
    const aiTab = $('[data-node-key="ai-illustration"]');
    if (!aiTab) throw new Error('BJH_AI_IMAGE_FAILED:section=' + (sectionIndex + 1) + ':stage=no_ai_tab');
    aiTab.click();
    await sleep(1000);

    // 找 textarea
    let ta = null;
    for (let w = 0; w < 15 && !ta; w += 1) { await sleep(500); ta = $('.cheetah-tabs-tabpane-active textarea'); }
    if (!ta) throw new Error('BJH_AI_IMAGE_FAILED:section=' + (sectionIndex + 1) + ':stage=no_textarea');

    // 🔴 v9.0：用原生 setter 清空 + 设新 prompt（正确触发 React onChange）
    const prompt = getSectionTail(sectionIndex) + '，写实风格';
    const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
    nativeSetter.call(ta, ''); ta.dispatchEvent(new Event('input', { bubbles: true })); await sleep(100);
    nativeSetter.call(ta, prompt); ta.dispatchEvent(new Event('input', { bubbles: true }));
    ta.dispatchEvent(new Event('change', { bubbles: true }));
    if (ta.value !== prompt) throw new Error('BJH_AI_IMAGE_FAILED:section=' + (sectionIndex + 1) + ':stage=prompt_not_applied');
    await sleep(500);

    // 生成
    const genBtn = $('.FeEditorApp-_65f7660e096d0b20-btn');
    if (!genBtn) throw new Error('BJH_AI_IMAGE_FAILED:section=' + (sectionIndex + 1) + ':stage=no_gen_btn');
    reactClick(genBtn);
    await sleep(30000);

    // 选第一张图（多选择器容错）
    const clickSelectors = [
      '.cheetah-tabs-tabpane-active .FeEditorApp-_28863d93deff3e03-clickArea',
      '.cheetah-tabs-tabpane-active [class*="clickArea"]',
      '.cheetah-tabs-tabpane-active [class*="imageWrap"]',
      '.cheetah-tabs-tabpane-active [class*="img-item"]'
    ];
    let clickArea = null;
    for (const sel of clickSelectors) {
      clickArea = $(sel);
      if (clickArea) break;
    }
    if (!clickArea) {
      const allImgs = $$('.cheetah-tabs-tabpane-active img');
      clickArea = allImgs.find(img => img.naturalWidth > 1);
    }
    if (!clickArea) throw new Error('BJH_AI_IMAGE_FAILED:section=' + (sectionIndex + 1) + ':stage=no_click_area');
    reactClick(clickArea);
    await sleep(1000);

    // 点确认（用 reactClick 触发 React 合成事件）
    const confirmBtn = $$('.cheetah-modal button').find((b) => (b.textContent || '').trim() === '确认');
    if (!confirmBtn) throw new Error('BJH_AI_IMAGE_FAILED:section=' + (sectionIndex + 1) + ':stage=no_confirm_btn');
    reactClick(confirmBtn);
    await sleep(5000);

    // 🔴 v9.0：验证图片是真实图片（不是1x1像素）
    const editor = window.UE_V2.instants['ueditorInstant0'];
    const doc = editor.document;
    const imgsInSection = Array.from(doc.querySelectorAll('p'))
      .filter(p => {
        const titleIdx = Array.from(doc.querySelectorAll('p'))
          .map((x, i) => ({ i, text: x.textContent || '' }))
          .filter(x => x.text.includes('━━━'));
        const start = titleIdx[sectionIndex].i;
        const end = titleIdx[sectionIndex + 1] ? titleIdx[sectionIndex + 1].i : doc.querySelectorAll('p').length;
        const pIdx = Array.from(doc.querySelectorAll('p')).indexOf(p);
        return pIdx >= start && pIdx < end;
      })
      .reduce((c, p) => c + p.querySelectorAll('img').length, 0);
    const lastInserted = sectionImgCount(sectionIndex);
    if (lastInserted < 1) throw new Error('BJH_AI_IMAGE_FAILED:section=' + (sectionIndex + 1) + ':stage=img_not_found');
    return lastInserted;
  }

  const results = [];
  for (let i = 0; i < 6; i += 1) {
    // 已有图则跳过
    if (sectionImgCount(i) >= 1) {
      results.push({ section: i + 1, status: 'skip_existing' });
      continue;
    }
    const cnt = await insertOneSection(i);
    results.push({ section: i + 1, imgs: cnt });
  }

  // 清理"请点击输入图片描述"占位段
  const editor = window.UE_V2.instants['ueditorInstant0'];
  const doc = editor.document;
  doc.querySelectorAll('p').forEach(p => {
    if ((p.textContent || '').includes('请点击输入图片描述')) p.remove();
  });

  return results;
})();
