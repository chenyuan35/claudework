// 🔴 封面 AI封图脚本 v2.3（2026-07-27 修复：新增SOP-2正文图去重，原SOP-2→SOP-3）
// 🔴 此脚本不再包含"选择封面"+"AI封图"tab 点击——这两步必须用 Playwright 原生 click
// 🔴 本脚本只负责：取标题做 prompt → 点生成 → 轮询等图片（40s）→ 点"确定" → 验证封面
// 🔴 前置条件：封面选择弹窗已打开且 AI封图 tab 已激活（由 Playwright browser_click 完成）

(async () => {
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const $ = (sel, root) => (root || document).querySelector(sel);
  const $$ = (sel, root) => Array.from((root || document).querySelectorAll(sel));

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

  // 0. 前置条件：封面弹窗已打开且 AI封图 tab 已激活（由 Playwright browser_click 完成，不在此检验）
  //    移除 querySelectorAll('*') 全文搜索——该方式在 dialog 未完全渲染时必然失败

  // 🔴 SOP-1：验证编辑器内是正确文章（正文非空，非空白草稿）
  const editorCheck = window.UE_V2?.instants?.ueditorInstant0;
  if (!editorCheck) throw new Error('BJH_COVER_FAILED:stage=no_editor');
  const bodyContent = editorCheck.getContent ? editorCheck.getContent() : '';
  // 剔除 HTML 标签取纯文本长度
  const bodyText = bodyContent.replace(/<[^>]+>/g, '').replace(/&nbsp;/g, ' ').trim();
  if (bodyText.length < 50) throw new Error('BJH_COVER_FAILED:stage=body_too_short');

  // 1. 取标题写入 textarea 作为 prompt
  const titleInput = Array.from(document.querySelectorAll('div[contenteditable="true"]'))
    .find((el) => el.getClientRects().length > 0);
  if (!titleInput) throw new Error('BJH_COVER_FAILED:stage=no_title_input');
  const titleText = (titleInput.textContent || '').trim();
  if (!titleText) throw new Error('BJH_COVER_FAILED:stage=title_empty');

  const ta = $('textarea');
  if (!ta) throw new Error('BJH_COVER_FAILED:stage=no_textarea');
  const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
  nativeSetter.call(ta, titleText);
  ta.dispatchEvent(new Event('input', { bubbles: true }));
  ta.dispatchEvent(new Event('change', { bubbles: true }));
  if (ta.value !== titleText) throw new Error('BJH_COVER_FAILED:stage=prompt_not_applied');
  await sleep(500);

  // 2. 点生成按钮（固定 class：和正文配图同款）
  const genBtn = $('.FeEditorApp-_65f7660e096d0b20-btn');
  if (!genBtn) throw new Error('BJH_COVER_FAILED:stage=no_gen_btn');
  reactClick(genBtn);

  // 3. 等 AI 生成完毕（轮询直到生成图片出现，最长 40s）
  const waitForGenerated = (timeoutMs) => {
    const deadline = Date.now() + timeoutMs;
    return new Promise((resolve, reject) => {
      const check = () => {
        // AI封图 tab 生成后会在 tab 标题上显示 (N)，panel 内出现图片元素
        const genCount = document.querySelector(
          '.cheetah-tabs-tabpane-active [class*="cover"] img, ' +
          '.cheetah-tabs-tabpane-active [class*="preview"] img'
        );
        if (genCount) return resolve(genCount);
        if (Date.now() >= deadline) return reject(new Error('GENERATE_TIMEOUT'));
        setTimeout(check, 1000);
      };
      check();
    });
  };
  try {
    await waitForGenerated(40000);
  } catch (e) {
    throw new Error('BJH_COVER_FAILED:stage=generate_timeout');
  }

  // 4. 点"确定 (1)"按钮（在当前激活的 tabpane 内找，避免误点另一个 tab 的确定按钮）
  const activePane = $('.cheetah-tabs-tabpane-active');
  if (!activePane) throw new Error('BJH_COVER_FAILED:stage=no_active_pane');
  const confirmBtn = Array.from(activePane.querySelectorAll('button'))
    .find((b) => /^确定/.test((b.textContent || '').trim()));
  if (!confirmBtn) throw new Error('BJH_COVER_FAILED:stage=no_confirm_btn');
  reactClick(confirmBtn);
  await sleep(2000);

  // 5. 验证封面已设：检查封面图片元素是否存在且有有效 src
  await sleep(3000);
  const coverSelectors = [
    '[class*="cover-uploader"] img', '[class*="Cover"] img',
    '[class*="cover"] img', '[class*="coverImg"] img',
    '.FeEditorApp-_73a3a52aab7e3a36-coverImg'
  ];
  let coverArea = null;
  for (const sel of coverSelectors) {
    coverArea = document.querySelector(sel);
    if (coverArea && coverArea.getAttribute('src') && coverArea.getAttribute('src').length > 20) break;
  }
  const coverSrc = coverArea ? (coverArea.getAttribute('src') || '') : '';
  if (coverSrc.length < 20) throw new Error('BJH_COVER_FAILED:stage=verify_failed');

  // 🔴 SOP-2：验证正文图片互不重复（2026-07-27 新增）
  const editor2 = window.UE_V2?.instants?.ueditorInstant0;
  if (editor2 && editor2.document) {
    const bodyImgs = Array.from(editor2.document.querySelectorAll('img'));
    const bodySrcs = bodyImgs.map(img => (img.getAttribute('src') || '')).filter(s => s.length > 20);
    // 全等匹配 + 末尾 60 字符模糊匹配
    for (let a = 0; a < bodySrcs.length; a++) {
      for (let b = a + 1; b < bodySrcs.length; b++) {
        if (bodySrcs[a] === bodySrcs[b] || bodySrcs[a].slice(-60) === bodySrcs[b].slice(-60)) {
          throw new Error('BJH_COVER_FAILED:stage=body_img_dup');
        }
      }
    }
  }

  // 🔴 SOP-3：封面 src 不与任何正文图片 src 重复（原SOP-2升级）
  const editor3 = window.UE_V2?.instants?.ueditorInstant0;
  if (editor3 && editor3.document) {
    const bodySrcs = Array.from(editor3.document.querySelectorAll('img'))
      .map(img => (img.getAttribute('src') || '')).filter(s => s.length > 20);
    const coverTail = coverSrc.slice(-60);
    for (const bodySrc of bodySrcs) {
      if (bodySrc === coverSrc || bodySrc.endsWith(coverTail)) {
        throw new Error('BJH_COVER_FAILED:stage=cover_dup_with_body');
      }
    }
  }

  return { status: 'cover_set_via_ai', src: coverSrc.slice(0, 50) };
})();
