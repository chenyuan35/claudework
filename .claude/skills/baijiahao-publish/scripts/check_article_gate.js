// 🔴 纯页面内自包含脚本（2026-07-26 审计修复：移除 dataset 死注释，正文无加粗后直接数全部 <strong>）
// 执行方式：mcp__playwright__browser_evaluate 包进 async () => {...} 注入执行
// 单一阶段：content（正文硬指标）。publish 阶段已废弃——发布前检查由各阶段自身负责。

// 闸门通过 rawHtml 统计 <strong> 数量判定小节数（正文已无加粗，所有 <strong> 都是节标题）
(async () => {
  const stage = sessionStorage.getItem('bjh_gate_stage') || 'content';

  const hardFailures = [];
  const warnings = [];
  const editor = window.UE_V2 && window.UE_V2.instants && window.UE_V2.instants['ueditorInstant0'];
  if (!editor || typeof editor.getContent !== 'function') {
    throw new Error('BJH_EDITOR_NOT_READY');
  }

  const rawHtml = editor.getContent();
  const bodyText = rawHtml.replace(/<img[^>]*>/g, '');
  const plainText = bodyText.replace(/<[^>]+>/g, '').replace(/\s+/g, '');
  const textLen = plainText.length;
  // 🔴 2026-07-22 汉字计数铁律：只统计 CJK 汉字，不混入标点/英文/数字
  const hanCount = (plainText.match(/[一-鿿㐀-䶿豈-﫿]/g) || []).length;
  const paras = rawHtml
    .replace(/<[^>]+>/g, '⏎')
    .split('⏎')
    .map((value) => value.trim())
    .filter(Boolean);
  const contentParas = paras.length - sectionCount;
  // 🔴 2026-07-26 修复：源头已扼杀正文加粗，直接数全部 <strong> 即节数
  // UEditor 会剥离 data-bjh-role，但正文已无 <strong>，所以所有 <strong> 都是节标题
  const allStrong = rawHtml.match(/<strong[^>]*>[\s\S]*?<\/strong>/g) || [];
  const sectionCount = allStrong.length;
  const imgCount = (rawHtml.match(/<img/g) || []).length;
  const imageSources = Array.from(rawHtml.matchAll(/<img[^>]+src="([^"]+)"/g)).map((m) => m[1]);
  const uniqueSources = new Set(imageSources.filter(Boolean));
  const signatureHtml = rawHtml
    .replace(/<p[^>]*>[^<]*请点击输入图片描述[^<]*<\/p>/gi, '')
    .replace(/<img[^>]*>/gi, '');
  const signatureText = signatureHtml.replace(/<[^>]+>/g, '').replace(/\s+/g, '');
  let signatureHash = 2166136261;
  for (let index = 0; index < signatureText.length; index += 1) {
    signatureHash ^= signatureText.charCodeAt(index);
    signatureHash = Math.imul(signatureHash, 16777619);
  }
  const contentSignature = `${signatureText.length}:${sectionCount}:${(signatureHash >>> 0).toString(16)}`;

  if (hanCount < 2000) hardFailures.push(`汉字数：${hanCount}<2000`);
  if (textLen < 2200) warnings.push(`总字符偏少：${textLen}，建议≥2200`);
  if (contentParas < 42) hardFailures.push(`段数：${contentParas}<42`);
  if (sectionCount !== 6) hardFailures.push(`小节数：${sectionCount}≠6`);

  // 🔴 段落长度闸门（2026-07-22 新增：任何段落 ≥81 字硬拦截，防止文字墙）
  const pTexts = rawHtml.match(/<p[^>]*>([\s\S]*?)<\/p>/gi) || [];
  for (const pTag of pTexts) {
    const pLen = pTag.replace(/<[^>]+>/g, '').replace(/\s+/g, '').length;
    if (pLen >= 81) {
      hardFailures.push(`段落长度：${pLen}字≥81，最大80`);
      break;
    }
  }

  if (stage === 'publish') {
    const titleEl = Array.from(document.querySelectorAll('[contenteditable="true"]'))
      .find((element) => element.getClientRects().length > 0);
    const title = titleEl ? titleEl.textContent.trim() : '';
    if (title.length < 2 || title.length > 64) {
      hardFailures.push(`标题：长度${title.length}，要求2-64`);
    }
    if (imgCount < sectionCount) {
      hardFailures.push(`配图：${imgCount}张<${sectionCount}个小节`);
    }
    if (!document.body.innerHTML.includes('更换封面')) {
      hardFailures.push('封面：尚未设置');
    }
    const aiCheckbox = document.querySelector(
      'label:has(.aigc_bjh_status) .cheetah-checkbox.cheetah-checkbox-checked',
    );
    if (!aiCheckbox) hardFailures.push('AI声明：未勾选');

    const last200 = rawHtml.slice(-200).replace(/<[^>]+>/g, '');
    if (last200.includes('评论区聊聊') || last200.includes('在评论区')) {
      hardFailures.push('引导语：含评论区引导话术');
    }
    for (const phrase of ['你应该', '你必须', '你一定', '建议你']) {
      if (rawHtml.includes(phrase)) {
        hardFailures.push(`权威口吻：含“${phrase}”`);
        break;
      }
    }

    const boldCount = (rawHtml.match(/<strong>/g) || []).length;
    if (contentParas && boldCount < contentParas * 2) {
      warnings.push(`加粗密度：${boldCount}/${contentParas}段`);
    }
    const hasNumberList = /(?:第[一二三四五六七八九十]|[1-9]\.\s|①|②|③)/.test(plainText);
    const hasParallel = /(?:误区|步骤|要点|原因|症状|做法|注意)/.test(plainText);
    if (hasParallel && !hasNumberList) warnings.push('列表格式：并列信息未用数字编号');
    if (sectionCount > 0 && textLen / sectionCount > 350) {
      warnings.push(`小标题密度：平均每节${Math.round(textLen / sectionCount)}字`);
    }
  }

  const result = {
    stage,
    pass: hardFailures.length === 0,
    hardFailures,
    warnings,
    metrics: { textLen, hanCount, contentParas, sectionCount, imgCount },
    contentSignature,
  };

  if (!result.pass) {
    throw new Error(`BJH_GATE_FAILED:${result.hardFailures.join(';')}`);
  }
  if (result.stage === 'content') {
    sessionStorage.setItem('bjh_content_gate_signature', result.contentSignature);
    sessionStorage.removeItem('bjh_ai_images_complete');
  }
  return result;
})();
