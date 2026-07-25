"""生成 Phase 4 单文件浏览器任务：上传三图、自动定位、段落完整性核验。"""
import hashlib
import json
import os
import shutil
from pathlib import Path


def _project_root() -> Path:
    """从脚本自身向上找包含 .git 或 .playwright-mcp 的目录，不依赖任何环境变量."""
    current = Path(__file__).resolve().parent  # scripts/
    for _ in range(20):
        if (current / ".git").exists() or (current / ".playwright-mcp").exists():
            return current
        parent = current.parent
        if parent == current:
            break
        current = parent
    fallback = Path.cwd().resolve()
    return fallback


def build_phase4_browser_task(*, title, html, article_hash, image_paths,
                              editor_selector, article_cfg):
    """复制图片到 Playwright 根目录并生成可直接执行的单文件任务。"""
    project_root = _project_root()
    artifact_dir = project_root / ".playwright-mcp" / "toutiao-article" / (
        article_hash or hashlib.sha256(title.encode("utf-8")).hexdigest()[:16]
    )
    artifact_dir.mkdir(parents=True, exist_ok=True)

    browser_images = []
    for index, source in enumerate(image_paths, 1):
        source_path = Path(source).resolve()
        target = artifact_dir / f"article_img{index}{source_path.suffix.lower()}"
        if source_path != target:
            shutil.copy2(source_path, target)
        browser_images.append(str(target))

    bands = article_cfg["image_distribution_bands"]
    cfg = {
        "required": article_cfg["images_required"],
        "targets": article_cfg["image_distribution_targets_pct"],
        "bands": [
            [bands["band1_min"], bands["band1_max"]],
            [bands["band2_min"], bands["band2_max"]],
            [bands["band3_min"], bands["band3_max"]],
        ],
        "gap": article_cfg["image_gap_min_pct"],
        "lastExcl": article_cfg["image_last_exclusion_pct"],
        "last": article_cfg["last_paras_no_image"],
        "uploadTimeout": article_cfg["image_upload_timeout_sec"] * 1000,
        "chineseMin": article_cfg["chinese_min"],
    }
    anchor_selector = f"{editor_selector} > p:last-child"

    code = f'''async (page) => {{
  const pmSelector = {json.dumps(editor_selector, ensure_ascii=False)};
  const anchorSelector = {json.dumps(anchor_selector, ensure_ascii=False)};
  const expectedTitle = {json.dumps(title, ensure_ascii=False)};
  const sourceHtml = {json.dumps(html, ensure_ascii=False)};
  const imagePaths = {json.dumps(browser_images, ensure_ascii=False)};
  const cfg = {json.dumps(cfg, ensure_ascii=False)};

  async function restoreValidatedBody() {{
    return await page.evaluate(function(a) {{
      const pm = document.querySelector(a.pm);
      const title = document.querySelector('textarea[placeholder*="请输入文章标题"]')?.value || '';
      if (!pm) throw new Error('NO_PROSEMIRROR');
      if (title !== a.title) throw new Error('TITLE_MISMATCH_BEFORE_IMAGES:' + title);
      pm.innerHTML = a.html + '<p><br></p>';
      pm.dispatchEvent(new Event('input', {{bubbles:true}}));
      const paragraphs = Array.from(pm.children)
        .filter(function(n) {{ return n.tagName === 'P'; }})
        .map(function(n) {{ return (n.textContent || '').trim(); }})
        .filter(Boolean);
      const chinese = ((pm.innerText || '').match(/[\\u4e00-\\u9fff\\u3400-\\u4dbf\\uf900-\\ufaff]/g) || []).length;
      return {{paragraphs:paragraphs, chinese:chinese}};
    }}, {{pm:pmSelector, title:expectedTitle, html:sourceHtml}});
  }}

  async function waitForBlocks(expected, timeout) {{
    await page.waitForFunction(function(a) {{
      const pm = document.querySelector(a.pm);
      if (!pm) return false;
      const blocks = Array.from(pm.children).filter(function(n) {{
        return n.tagName === 'DIV' && n.querySelector('img');
      }});
      return blocks.length === a.expected;
    }}, {{pm:pmSelector, expected:expected}}, {{timeout:timeout}});
  }}

  const baseline = await restoreValidatedBody();
  if (baseline.chinese < cfg.chineseMin) throw new Error('BODY_CHANGED_BEFORE_IMAGES');

  let uploadMode = 'single_drop_all_files';
  await page.locator(anchorSelector).drop({{files:imagePaths}});
  try {{
    await waitForBlocks(cfg.required, Math.min(cfg.uploadTimeout, 25000));
  }} catch (firstError) {{
    uploadMode = 'sequential_drop_same_empty_anchor';
    await restoreValidatedBody();
    for (let i = 0; i < imagePaths.length; i++) {{
      await page.locator(anchorSelector).drop({{files:[imagePaths[i]]}});
      await waitForBlocks(i + 1, cfg.uploadTimeout);
      await page.evaluate(function(a) {{
        const pm = document.querySelector(a.pm);
        const last = pm.lastElementChild;
        if (!last || last.tagName !== 'P' || (last.textContent || '').trim()) {{
          const anchor = document.createElement('p');
          anchor.innerHTML = '<br>';
          pm.appendChild(anchor);
        }}
      }}, {{pm:pmSelector}});
    }}
  }}

  await page.waitForFunction(function(a) {{
    const pm = document.querySelector(a.pm);
    if (!pm) return false;
    const blocks = Array.from(pm.children).filter(function(n) {{
      return n.tagName === 'DIV' && n.querySelector('img');
    }});
    if (blocks.length !== a.required) return false;
    return blocks.every(function(block) {{
      const img = block.querySelector('.pgc-img img') || block.querySelector('img');
      return img && img.src && !img.src.startsWith('blob:');
    }});
  }}, {{pm:pmSelector, required:cfg.required}}, {{timeout:cfg.uploadTimeout}});

  const result = await page.evaluate(function(a) {{
    const pm = document.querySelector(a.pm);
    if (!pm) return {{passed:false,error:'NO_PROSEMIRROR'}};
    const sentenceEnd = /[。！？.!?]$/;
    const blocks = Array.from(pm.children).filter(function(n) {{
      return n.tagName === 'DIV' && n.querySelector('img');
    }});
    if (blocks.length !== a.cfg.required) {{
      return {{passed:false,error:'IMAGE_BLOCK_COUNT',actual:blocks.length}};
    }}

    const textParas = Array.from(pm.children).filter(function(n) {{
      return n.tagName === 'P' && (n.textContent || '').trim();
    }});
    const paragraphTextsBefore = textParas.map(function(n) {{ return (n.textContent || '').trim(); }});
    const safe = textParas.map(function(node, index) {{
      return {{node:node,index:index,text:(node.textContent || '').trim()}};
    }}).filter(function(item) {{ return sentenceEnd.test(item.text); }});

    const anchors = [];
    let previousIndex = -1;
    for (let k = 0; k < a.cfg.targets.length; k++) {{
      const target = Math.round((textParas.length - 1) * a.cfg.targets[k] / 100);
      const band = a.cfg.bands[k];
      let candidates = safe.filter(function(item) {{
        const pct = Math.round(item.index * 100 / textParas.length);
        return item.index > previousIndex && pct >= band[0] && pct <= band[1];
      }});
      if (!candidates.length) {{
        candidates = safe.filter(function(item) {{ return item.index > previousIndex; }});
      }}
      candidates.sort(function(x,y) {{
        return Math.abs(x.index-target) - Math.abs(y.index-target);
      }});
      if (!candidates.length) return {{passed:false,error:'NO_SAFE_SENTENCE_ANCHOR',slot:k}};
      anchors.push(candidates[0]);
      previousIndex = candidates[0].index;
    }}

    for (let k = blocks.length - 1; k >= 0; k--) {{
      anchors[k].node.insertAdjacentElement('afterend', blocks[k]);
    }}
    const trailingEmpty = pm.lastElementChild;
    if (trailingEmpty && trailingEmpty.tagName === 'P' && !(trailingEmpty.textContent || '').trim()) trailingEmpty.remove();
    pm.dispatchEvent(new Event('input', {{bubbles:true}}));

    const children = Array.from(pm.children);
    const imageIndices = [];
    const canonical = [];
    for (let i = 0; i < children.length; i++) {{
      const node = children[i];
      if (node.tagName === 'DIV' && node.querySelector('img')) {{
        imageIndices.push(i);
        canonical.push(node.querySelector('.pgc-img img') || node.querySelector('img'));
      }}
    }}
    const paragraphTextsAfter = children
      .filter(function(n) {{ return n.tagName === 'P' && (n.textContent || '').trim(); }})
      .map(function(n) {{ return (n.textContent || '').trim(); }});
    const paragraphIntegrityOk = JSON.stringify(paragraphTextsBefore) === JSON.stringify(paragraphTextsAfter);
    const uniqueCdn = new Set(canonical.filter(function(img) {{
      return img && img.src && !img.src.startsWith('blob:') && /^https?:/.test(img.src);
    }}).map(function(img) {{ return img.src.split('~')[0].split('?')[0]; }})).size;
    const blobCount = canonical.filter(function(img) {{ return img && img.src && img.src.startsWith('blob:'); }}).length;
    const distribution = imageIndices.map(function(index) {{
      return {{index:index,percent:Math.round(index * 100 / children.length)}};
    }});
    const bandOk = distribution.every(function(item,index) {{
      return item.percent >= a.cfg.bands[index][0] && item.percent <= a.cfg.bands[index][1];
    }});
    const spacingOk = distribution.every(function(item,index) {{
      return index === 0 || item.percent - distribution[index-1].percent >= a.cfg.gap;
    }});
    const lastExclusionOk = distribution.every(function(item) {{ return item.percent <= a.cfg.lastExcl; }});
    const lastParasOk = imageIndices.every(function(index) {{ return index < children.length - a.cfg.last; }});
    const sentenceAnchorsOk = imageIndices.every(function(index) {{
      const previous = children[index-1];
      return previous && previous.tagName === 'P' && sentenceEnd.test((previous.textContent || '').trim());
    }});
    const passed = imageIndices.length === a.cfg.required && uniqueCdn === a.cfg.required &&
      blobCount === 0 && paragraphIntegrityOk && bandOk && spacingOk &&
      lastExclusionOk && lastParasOk && sentenceAnchorsOk;
    return {{
      passed:passed,
      uploadMode:a.uploadMode,
      imageBlockCount:imageIndices.length,
      uniqueCdnCount:uniqueCdn,
      blobCount:blobCount,
      paragraphIntegrityOk:paragraphIntegrityOk,
      sentenceAnchorsOk:sentenceAnchorsOk,
      bandOk:bandOk,
      spacingOk:spacingOk,
      lastExclusionOk:lastExclusionOk,
      lastParasOk:lastParasOk,
      distribution:distribution,
      selectedParagraphIndices:anchors.map(function(item) {{ return item.index; }})
    }};
  }}, {{pm:pmSelector,cfg:cfg,uploadMode:uploadMode}});

  if (!result.passed) throw new Error('PHASE4_IMAGE_PIPELINE_FAILED:' + JSON.stringify(result));
  return {{uploaded:true,relocated:true,validated:result}};
}}'''

    code_file = artifact_dir / "phase4_upload_relocate_validate.js"
    code_file.write_text(code, encoding="utf-8")
    return {
        "code_file": str(code_file),
        "image_paths": browser_images,
        "drop_target": anchor_selector,
        "execution": "browser_run_code_unsafe_only",
    }
