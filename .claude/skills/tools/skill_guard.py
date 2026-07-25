#!/usr/bin/env python3
"""
skill_guard.py — 技能强制守卫（类型分流 + 精准检查）

用法：
  python skill_guard.py pre <skill_name> [--task-id <id>]
  python skill_guard.py post <skill_name> --task-id <id> [--result-files ...]
  python skill_guard.py audit <skill_path>
  python skill_guard.py detect <skill_path>
  python skill_guard.py scan [vuln_type] [--path file] [--json]  # 扫描并给出行级证据
  python skill_guard.py plan [vuln_type] [--path file] [--json]  # 生成按类型修复计划（不改文件）
  python skill_guard.py fix [vuln_type] [--path file] [--apply]  # 干跑或执行受限自动修复
  python skill_guard.py rollback <manifest.json>   # 回滚一次自动修复
  python skill_guard.py test                 # 运行测试夹具

退出码：0=通过 1=拦截 2=内部错误
"""

import ast, json, os, re, sys, time, hashlib, tempfile, yaml, shutil
from pathlib import Path
from datetime import datetime

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))
from platform_utils import configure_utf8_stdio, read_json, write_json

configure_utf8_stdio()

SKILLS_DIR = TOOLS_DIR.parent
WORK_DIR = SKILLS_DIR.parent.parent
EVIDENCE_BASE = WORK_DIR / ".claude" / "evidence"
REPAIR_BACKUP_BASE = WORK_DIR / ".claude" / "skill_guard_backups"

# ═══════════════════════════════════════════════════════════════
# 一、类型检测（两层策略）
# ═══════════════════════════════════════════════════════════════

BROWSER_HARD_SIGNALS = [
    r'mcp__playwright__browser_',
    r'browser_navigate\s*\(',
    r'browser_run_code_unsafe\s*\(',
]

TYPE_SIGNALS = {
    "browser-publish": [
        r'browser_click', r'browser_snapshot', r'browser_type',
        r'browser_evaluate', r'browser_fill_form',
        r'Playwright', r'选择器表|坐标速查',
    ],
    "api": [
        r'requests\.(post|get|put|delete)\s*\(',
        r'curl\s',
        r'API\s*(发布|接口|直连|草稿|key|Key)',
        r'access_token|api_token',
    ],
    "content": [],
}

def detect_skill_type(text: str, manifest_type: str | None = None) -> str:
    """两层策略：manifest > 硬信号 > 软信号 > content 兜底"""
    if manifest_type in ("browser-publish", "api", "content"):
        return manifest_type
    for pat in BROWSER_HARD_SIGNALS:
        if re.search(pat, text, re.IGNORECASE):
            return "browser-publish"
    scores = {"browser-publish": 0, "api": 0, "content": 0}
    for ttype, patterns in TYPE_SIGNALS.items():
        for pat in patterns:
            if re.search(pat, text, re.IGNORECASE):
                scores[ttype] += 1
    best = max(scores, key=scores.get)
    if scores[best] > 0:
        return best
    return "content"

def skill_path(name: str) -> Path:
    candidates = [
        SKILLS_DIR / name / "SKILL.md",
        SKILLS_DIR / name / f"{name}.md",
        WORK_DIR / ".claude" / "skills" / name / "SKILL.md",
    ]
    for p in candidates:
        if p.exists():
            return p.resolve()
    raise FileNotFoundError(f"SKILL.md not found: '{name}'")

def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def read_skill_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")

def parse_frontmatter(text: str) -> tuple:
    if not text.startswith("---"):
        return None, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None, text
    try:
        meta = yaml.safe_load(parts[1])
        if not isinstance(meta, dict):
            return None, text
        return meta, parts[2]
    except Exception:
        return None, text


# ═══════════════════════════════════════════════════════════════
# 二、通用检查
# ═══════════════════════════════════════════════════════════════

def check_exists(name: str) -> tuple:
    try:
        p = skill_path(name)
        assert p.stat().st_size > 0
        return True, str(p)
    except (FileNotFoundError, AssertionError) as e:
        return False, str(e)

def check_frontmatter(p: Path) -> tuple:
    try:
        text = p.read_text(encoding="utf-8")
        meta, _ = parse_frontmatter(text)
        if meta is None:
            return False, "missing valid YAML frontmatter", None
        if "name" not in meta:
            return False, "frontmatter missing 'name'", None
        mtype = meta.get("type") if isinstance(meta.get("type"), str) else None
        return True, meta["name"], mtype
    except Exception as e:
        return False, f"frontmatter error: {e}", None


def check_branch_words(text: str) -> tuple:
    """只扫描流程性正文，跳过代码块/引用/示例/豁免区；并列可选路径才报错"""
    lines = text.split("\n")
    hits = []
    in_code_block = False
    exempt_headings = [
        "异常表", "已知问题", "已知坑铁律", "调研结论", "调研总结",
        "GitHub", "写作规范", "选题", "定位", "账号", "风格",
        "配图", "排版", "内容模式审计", "执行速查",
    ]
    branch_pattern = re.compile(r'(方案[A-Z]|方案[一二三])')

    for lineno, line in enumerate(lines, 1):
        s = line.strip()
        if s.startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue
        if not s or s.startswith((">", '"', "“", "//", "#", "|", "* ")):
            continue
        if "`" in s and "`" in s[s.index("`")+1:]:
            continue
        if any(h in s for h in exempt_headings):
            continue
        if s.startswith(("例如", "比如", "如：", "如:", "示例")):
            continue
        if branch_pattern.search(s):
            hits.append(f"  L{lineno}: {s[:80]}")

    return (len(hits) == 0, hits)


# ═══════════════════════════════════════════════════════════════
# 三、类型特定检查
# ═══════════════════════════════════════════════════════════════

def check_browser_publish(text: str) -> list:
    checks = []
    h = bool(re.search(r'\|.*browser_(evaluate|click|wait|fill|upload).*\|', text, re.IGNORECASE))
    has_coord_table = bool(re.search(r'\|.*步骤.*\|.*工具.*\|.*命令.*\|', text))
    has_eval_table = bool(re.search(r'\|.*evaluate 代码.*\|.*验收条件.*\|', text))
    h = h or has_coord_table or has_eval_table
    checks.append({"name": "BR-01: selector_table", "severity": "error", "pass": h, "detail": "OK" if h else "建议有选择器/坐标表"})
    h = bool(re.search(r'验收|验证|pass[=\s]|snapshot|screenshot', text, re.IGNORECASE))
    checks.append({"name": "BR-02: visual_acceptance", "severity": "error", "pass": h, "detail": "OK" if h else "需要视觉验收"})
    has_checklist = bool(re.search(r'- \[[ x]\]', text))
    has_publish_condition = bool(re.search(r'通过|禁止.*点击|通过.*才', text))
    h = has_checklist and has_publish_condition
    checks.append({"name": "BR-03: publish_gate", "severity": "error", "pass": h, "detail": "OK" if h else "建议有发布门"})
    return checks


def check_api(text: str) -> list:
    checks = []
    h = bool(re.search(r'验收|验证|status.*code|response|返回.*200|HTTP.*状态|检查.*响应', text, re.IGNORECASE))
    checks.append({"name": "API-01: interface_acceptance", "severity": "error", "pass": h, "detail": "OK" if h else "建议有接口验收"})
    h = bool(re.search(r'重试|retry|超时|备用|fallback', text, re.IGNORECASE))
    checks.append({"name": "API-02: retry", "severity": "warning", "pass": h, "detail": "OK" if h else "建议有重试机制"})
    return checks


def check_content(text: str) -> list:
    checks = []
    has_dedup = bool(re.search(r'去重|重复|已发布|标题.*比对|查重|duplicate|已存在|历史.*标题', text, re.IGNORECASE))
    is_publish = bool(re.search(r'发布|发表|publish|deploy|推送', text, re.IGNORECASE))
    sev = "error" if is_publish and not has_dedup else "warning"
    det = ("OK" if has_dedup else ("发布型内容技能需要去重/已发布比对" if is_publish else "建议有去重检测"))
    checks.append({"name": "CT-01: dedup", "severity": sev, "pass": has_dedup or not is_publish, "detail": det})
    h = bool(re.search(r'质量门|评分|阈值|score|检查清单|checklist|审核|review|AI.*检测', text, re.IGNORECASE))
    checks.append({"name": "CT-02: quality_gate", "severity": "warning", "pass": h, "detail": "OK" if h else "建议有质量门"})
    h = bool(re.search(r'cover\.jpg|final\.html|output|result|交付|产出|产物|生成.*文件|article', text, re.IGNORECASE))
    checks.append({"name": "CT-03: result_files", "severity": "warning", "pass": h, "detail": "OK" if h else "建议声明结果文件"})
    return checks


# ═══════════════════════════════════════════════════════════════
# 四、POST 证据
# ═══════════════════════════════════════════════════════════════

def _inside(path: Path, root: Path) -> bool:
    """Return whether a resolved path stays below a resolved root."""
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def save_evidence(task_id: str, skill_name: str, result_files: list | None = None) -> tuple:
    ev_dir = EVIDENCE_BASE / task_id
    ev_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "task_id": task_id,
        "skill": skill_name,
        "timestamp": datetime.now().isoformat(),
        "files": {},
        "missing": [],
    }
    for fname in result_files or []:
        raw_path = Path(fname)
        fp = (raw_path if raw_path.is_absolute() else WORK_DIR / raw_path).resolve()
        if not _inside(fp, WORK_DIR) or not fp.is_file():
            manifest["missing"].append(str(fname))
            continue
        relative = fp.relative_to(WORK_DIR.resolve())
        destination = ev_dir / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(fp, destination)
        manifest["files"][str(relative)] = {"sha256": sha256_of(fp), "size": fp.stat().st_size}

    write_json(ev_dir / "manifest.json", manifest)
    ok = bool(result_files) and bool(manifest["files"]) and not manifest["missing"]
    return ok, manifest


def cleanup_evidence(max_keep: int = 5, max_days: int = 7) -> tuple:
    if not EVIDENCE_BASE.exists():
        return 0, 0
    entries = sorted(
        [(d.stat().st_mtime, d.name, d) for d in EVIDENCE_BASE.iterdir() if d.is_dir()],
        key=lambda x: x[0], reverse=True
    )
    deleted = 0; kept = 0; now = time.time()
    for i, (mtime, name, d) in enumerate(entries):
        age_days = (now - mtime) / 86400
        if i >= max_keep or age_days > max_days:
            shutil.rmtree(d, ignore_errors=True); deleted += 1
        else:
            kept += 1
    return kept, deleted


# ═══════════════════════════════════════════════════════════════
# 五、PRE / POST / AUDIT / DETECT
# ═══════════════════════════════════════════════════════════════

def pre_check(skill_name: str) -> dict:
    p = skill_path(skill_name); text = read_skill_text(p)
    meta, _ = parse_frontmatter(text)
    mtype = meta.get("type") if meta and isinstance(meta.get("type"), str) else None
    stype = detect_skill_type(text, mtype)
    checks = []; all_pass = True

    ok, d = check_exists(skill_name)
    checks.append({"name": "skill_exists", "severity": "error", "pass": ok, "detail": d})
    if not ok: all_pass = False

    ok, d, _ = check_frontmatter(p)
    checks.append({"name": "frontmatter_valid", "severity": "error", "pass": ok, "detail": d})
    if not ok: all_pass = False

    ok, hits = check_branch_words(text)
    checks.append({"name": "branch_words_clean", "severity": "error", "pass": ok, "detail": hits if hits else "OK"})
    if not ok: all_pass = False

    tc = (check_browser_publish(text) if stype == "browser-publish"
          else check_api(text) if stype == "api" else check_content(text))
    checks.extend(tc)
    for c in tc:
        if c["severity"] == "error" and not c["pass"]: all_pass = False

    return {"pass": all_pass, "skill_type": stype, "checks": checks}


def post_check(skill_name: str, task_id: str, result_files: list | None = None) -> dict:
    ok, m = save_evidence(task_id, skill_name, result_files)
    k, d = cleanup_evidence()
    evidence_detail = f"{len(m['files'])} files -> {EVIDENCE_BASE / task_id}"
    if not result_files:
        evidence_detail += "; no result files supplied"
    elif m["missing"]:
        evidence_detail += f"; missing/outside workspace: {', '.join(m['missing'])}"
    return {"pass": ok, "task_id": task_id, "checks": [
        {"name": "POST-01: evidence_saved", "severity": "error", "pass": ok,
         "detail": evidence_detail},
        {"name": "POST-02: cleanup", "severity": "info", "pass": True,
         "detail": f"kept={k} deleted={d}"}
    ]}


def audit_mode(p: Path) -> dict:
    if not p.exists(): return {"pass": False, "error": f"file not found: {p}"}
    text = read_skill_text(p)
    meta, _ = parse_frontmatter(text)
    mtype = meta.get("type") if meta and isinstance(meta.get("type"), str) else None
    st = detect_skill_type(text, mtype)
    ok, d, _ = check_frontmatter(p)
    checks = [{"name": "frontmatter", "severity": "error", "pass": ok, "detail": d}]
    ap = ok
    ok, hits = check_branch_words(text)
    checks.append({"name": "branch_words", "severity": "error", "pass": ok, "detail": hits if hits else "OK"})
    if not ok: ap = False
    tc = (check_browser_publish(text) if st == "browser-publish"
          else check_api(text) if st == "api" else check_content(text))
    checks.extend(tc)
    for c in tc:
        if c["severity"] == "error" and not c["pass"]: ap = False
    return {"pass": ap, "file": str(p.resolve()), "detected_type": st,
            "sha256": sha256_of(p), "checks": checks}


def detect_mode(p: Path) -> dict:
    if not p.exists(): return {"pass": False, "error": f"file not found: {p}"}
    text = read_skill_text(p)
    meta, _ = parse_frontmatter(text)
    mtype = meta.get("type") if meta and isinstance(meta.get("type"), str) else None
    return {"pass": True, "file": str(p.resolve()), "detected_type": detect_skill_type(text, mtype)}


# ═══════════════════════════════════════════════════════════════
# 六、测试夹具
# ═══════════════════════════════════════════════════════════════

def run_tests() -> dict:
    tests = []; fails = 0

    def T(name, got_pass, want_desc, detail=None):
        nonlocal fails
        t = {"name": name, "pass": bool(got_pass), "want": want_desc}
        if detail is not None: t["detail"] = detail
        tests.append(t)
        if not bool(got_pass): fails += 1

    # t1: browser 硬信号 -> browser-publish
    r = detect_skill_type("## 流程\nbrowser_navigate('https://x.com')")
    T("browser_hard_signal", r == "browser-publish", "browser-publish", r)

    # t2: manifest 优先
    r = detect_skill_type("## 流程\nimport requests", "api")
    T("api_manifest", r == "api", "api", r)

    # t3: content 兜底
    r = detect_skill_type("写一篇 2000 字文章")
    T("content_fallback", r == "content", "content", r)

    # t4: 写作技能不应判为 browser
    r = detect_skill_type("写一篇小说，Plot 紧凑")
    T("no_false_browser", r != "browser-publish", "not browser-publish", r)

    # t5: 代码块内的 方案A/方案B 跳过
    r, hits = check_branch_words("## 流程\n代码：\n```\n方案A(); 方案B()\n```\n执行 SOP")
    T("branch_skip_codeblock", r, "no hits", f"{len(hits)} hits")

    # t6: 引用句跳过
    r, hits = check_branch_words("## 流程\n> 你可能觉得\n直接执行")
    T("branch_skip_quote", r, "no hits", f"{len(hits)} hits")

    # t7: 真实分支(方案A/方案B并列) -> 拦截
    r, hits = check_branch_words("## 流程\n方案A：用浏览器\n方案B：用 API")
    T("branch_detect_real", not r, "at least 1 hit", f"{len(hits)} hits: {hits}")

    # t8: 非发布内容技能 CT-01 warning 不阻断
    c = check_content("写一段短视频脚本")
    T("ct01_nonpublish_noblock", c[0]["severity"] != "error" or c[0]["pass"],
      "warning not error", c[0])

    # t9: 发布内容技能缺去重 -> 阻断
    c = check_content("写文章 -> 发表")
    T("ct01_publish_block", c[0]["severity"] == "error" and not c[0]["pass"],
      "blocked", c[0])

    # t10: "如果/否则" 单句放过（不是并列路径）
    r, hits = check_branch_words("## 流程\n如果登录超时，重试一次\n否则返回错误")
    T("branch_allow_simple_if_else", r, "no hits", f"{len(hits)} hits")

    # t11: 自动修复必须可精确回滚（临时夹具，不触碰工作区）
    try:
        with tempfile.TemporaryDirectory(prefix="skill_guard_fixture_") as temp_dir:
            root = Path(temp_dir)
            source = root / "entry.py"
            original = "with open('state.json', 'w') as handle:\n    handle.write('ok')\n"
            source.write_text(original, encoding="utf-8")
            candidates = encoding_candidates_for_python(source)
            applied = apply_encoding_candidates(candidates, workspace_root=root, backup_base=root / "backups")
            fixed = source.read_text(encoding="utf-8")
            restored = rollback_repair(
                Path(applied["manifest"]), workspace_root=root, backup_base=root / "backups"
            ) if applied.get("manifest") else {"pass": False}
            T(
                "encoding_fix_roundtrip",
                applied.get("pass") and restored.get("pass")
                and 'encoding="utf-8"' in fixed and source.read_text(encoding="utf-8") == original,
                "safe fix then exact rollback",
            )
    except Exception as exc:
        T("encoding_fix_roundtrip", False, "safe fix then exact rollback", str(exc))

    # t12: Markdown code examples get the same narrow, one-line UTF-8 repair.
    try:
        with tempfile.TemporaryDirectory(prefix="skill_guard_markdown_") as temp_dir:
            root = Path(temp_dir)
            source = root / "SKILL.md"
            original = "```bash\npython -c \"with open('state.json', 'r') as handle: pass\"\n```\n"
            source.write_text(original, encoding="utf-8")
            candidates = encoding_candidates_for_markdown(source)
            applied = apply_encoding_candidates(candidates, workspace_root=root, backup_base=root / "backups")
            fixed = source.read_text(encoding="utf-8")
            restored = rollback_repair(
                Path(applied["manifest"]), workspace_root=root, backup_base=root / "backups"
            ) if applied.get("manifest") else {"pass": False}
            T(
                "markdown_encoding_fix_roundtrip",
                applied.get("pass") and restored.get("pass")
                and "encoding='utf-8'" in fixed and source.read_text(encoding="utf-8") == original,
                "Markdown example fix then exact rollback",
            )
    except Exception as exc:
        T("markdown_encoding_fix_roundtrip", False, "Markdown example fix then exact rollback", str(exc))

    return {"pass": fails == 0, "total": len(tests), "pass_count": len(tests) - fails, "fail": fails, "tests": tests}


# ═══════════════════════════════════════════════════════════════
# 八、脆弱模式扫描 / 修复计划 / 受限批量修复
# ═══════════════════════════════════════════════════════════════

VULN_PATTERNS = {
    "encoding": {
        "name": "missing_encoding",
        "severity": "high",
        "detail": "文本 open() 缺少 encoding=，Windows 默认 GBK 会损坏 UTF-8 内容",
    },
    "pkill": {
        "name": "cross_platform_pkill",
        "severity": "high",
        "detail": "pkill 是 Linux 命令，Windows 不可用",
        "re": r"\bpkill\b",
    },
    "execCommand": {
        "name": "editor_execCommand",
        "severity": "medium",
        "detail": "execCommand('insertHTML'/'insertText') 需按目标编辑器验证，ProseMirror 中不可用",
        "re": r"\bexecCommand\s*\(\s*['\"](?:insertHTML|insertText)['\"]",
    },
    "name_sort": {
        "name": "name_sort_glob",
        "severity": "medium",
        "detail": "sorted(glob()) 可能按名称而非修改时间选择文件",
    },
    "hardcoded_threshold": {
        "name": "hardcoded_threshold",
        "severity": "low",
        "detail": "硬编码数字阈值，建议抽为具名常量或可传入参数",
        "re": r"(?:min[-_ ]?(?:chars?|words?|length)|max[-_ ]?(?:chars?|words?|length)|汉字数|字数|字符数)\s*[<>=:]+\s*\d{3,}",
    },
    "fixed_wait": {
        "name": "fixed_wait_timeout",
        "severity": "low",
        "detail": "固定 waitForTimeout 应替换为可观测的 Playwright 等待条件",
        "re": r"waitForTimeout\s*\(\s*\d{4,}",
    },
}

VULN_TYPES = tuple(VULN_PATTERNS)
SCAN_SUFFIXES = {".md", ".py", ".js", ".ts", ".ps1", ".sh"}
SCAN_EXCLUDED_PARTS = {".git", "__pycache__", "node_modules", ".venv", "skill_guard_backups"}


def relative_file(path: Path, root: Path = WORK_DIR) -> str:
    """Prefer a portable workspace-relative path in machine-readable reports."""
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path.resolve())


def finding_id(vuln_type: str, path: Path, line: int, column: int) -> str:
    return f"{vuln_type}:{relative_file(path)}:{line}:{column}"


def read_utf8_source(path: Path) -> tuple[str | None, str | None]:
    try:
        return path.read_bytes().decode("utf-8"), None
    except UnicodeDecodeError as exc:
        return None, f"not valid UTF-8: {exc}"
    except OSError as exc:
        return None, str(exc)


def should_scan(path: Path) -> bool:
    if not path.is_file() or path.suffix.lower() not in SCAN_SUFFIXES:
        return False
    if any(part in SCAN_EXCLUDED_PARTS for part in path.parts):
        return False
    try:
        relative = path.resolve().relative_to(SKILLS_DIR.resolve())
    except ValueError:
        return path.name.startswith("run_") and path.suffix.lower() == ".py"
    return not relative.parts or relative.parts[0] != "tools"


def discover_scan_targets() -> list[Path]:
    """Scan skill entry docs, executable skill code, and root run_*.py scripts.

    Reference manuals nested below a skill are intentionally excluded: they can
    mention a platform API without being an executable workflow, which would
    create noisy findings and unsafe batch changes.
    """
    targets: set[Path] = set()
    for skill_dir in SKILLS_DIR.iterdir():
        if not skill_dir.is_dir() or skill_dir.name == "tools":
            continue
        skill_markdown = skill_dir / "SKILL.md"
        if should_scan(skill_markdown):
            targets.add(skill_markdown.resolve())
        for path in skill_dir.rglob("*"):
            if path.suffix.lower() == ".md":
                continue
            if should_scan(path):
                targets.add(path.resolve())
    targets.update(path.resolve() for path in WORK_DIR.glob("run_*.py") if should_scan(path))
    return sorted(targets, key=lambda path: relative_file(path).lower())


def resolve_scan_targets(requested_paths: list[str] | None = None) -> list[Path]:
    """Resolve optional workspace-relative paths without letting a hook escape scope."""
    if not requested_paths:
        return discover_scan_targets()
    targets: set[Path] = set()
    for raw in requested_paths:
        candidate = (Path(raw) if Path(raw).is_absolute() else WORK_DIR / raw).resolve()
        if not _inside(candidate, WORK_DIR):
            raise ValueError(f"scan path outside workspace: {raw}")
        if candidate.is_dir():
            for child in candidate.rglob("*"):
                if should_scan(child):
                    targets.add(child.resolve())
        elif should_scan(candidate):
            targets.add(candidate)
        else:
            raise ValueError(f"not a supported scan target: {raw}")
    return sorted(targets, key=lambda path: relative_file(path).lower())


def line_and_column(text: str, offset: int) -> tuple[int, int]:
    line = text.count("\n", 0, offset) + 1
    last_newline = text.rfind("\n", 0, offset)
    return line, offset - last_newline


def line_excerpt(text: str, line: int, limit: int = 220) -> str:
    lines = text.splitlines()
    if line < 1 or line > len(lines):
        return ""
    return lines[line - 1].strip()[:limit]


def ast_offset(text: str, lineno: int, byte_column: int) -> int:
    """Convert AST's UTF-8 byte column to a Python string character offset."""
    lines = text.splitlines(keepends=True)
    before = sum(len(line) for line in lines[:lineno - 1])
    line = lines[lineno - 1]
    character_column = len(line.encode("utf-8")[:byte_column].decode("utf-8"))
    return before + character_column


def markdown_code_lines(text: str) -> set[int]:
    """Return fenced-code line numbers; encoding examples outside code are prose."""
    in_block = False
    lines: set[int] = set()
    for number, line in enumerate(text.splitlines(), 1):
        if line.strip().startswith("```"):
            in_block = not in_block
            continue
        if in_block:
            lines.add(number)
    return lines


MARKDOWN_OPEN_PATTERN = re.compile(r"(?<![.\w])(?:with\s+)?open\s*\([^\n)]*\)")


def markdown_text_open_matches(text: str):
    """Yield one-line builtin-looking text open() calls from fenced examples."""
    code_lines = markdown_code_lines(text)
    for match in MARKDOWN_OPEN_PATTERN.finditer(text):
        line, _ = line_and_column(text, match.start())
        call = match.group(0)
        if line not in code_lines or "encoding" in call:
            continue
        mode_match = re.search(r"[,=]\s*['\"]([^'\"]+)['\"]", call)
        if mode_match and "b" in mode_match.group(1):
            continue
        yield match


def new_finding(
    vuln_type: str,
    path: Path,
    text: str,
    offset: int,
    match: str,
    *,
    autofix: str = "manual",
    note: str | None = None,
) -> dict:
    line, column = line_and_column(text, offset)
    info = VULN_PATTERNS[vuln_type]
    result = {
        "id": finding_id(vuln_type, path, line, column),
        "file": relative_file(path),
        "line": line,
        "column": column,
        "vuln_type": vuln_type,
        "vuln_name": info["name"],
        "severity": info["severity"],
        "detail": info["detail"],
        "match": match[:160],
        "excerpt": line_excerpt(text, line),
        "autofix": autofix,
    }
    if note:
        result["note"] = note
    return result


def parse_python(text: str) -> ast.AST | None:
    try:
        return ast.parse(text)
    except SyntaxError:
        return None


def is_builtin_open(call: ast.Call) -> bool:
    return isinstance(call.func, ast.Name) and call.func.id == "open"


def open_has_encoding(call: ast.Call) -> bool:
    return any(keyword.arg == "encoding" for keyword in call.keywords)


def open_mode(call: ast.Call) -> str | None:
    mode_node = call.args[1] if len(call.args) >= 2 else None
    if mode_node is None:
        for keyword in call.keywords:
            if keyword.arg == "mode":
                mode_node = keyword.value
                break
    if isinstance(mode_node, ast.Constant) and isinstance(mode_node.value, str):
        return mode_node.value
    return None


def encoding_fix_candidate(path: Path, text: str, call: ast.Call) -> dict | None:
    """Return one mechanically safe UTF-8 insertion, or None for manual review."""
    mode = open_mode(call)
    if mode is not None and "b" in mode:
        return None
    if not getattr(call, "end_lineno", None) or call.lineno != call.end_lineno:
        return None
    if any(keyword.arg is None for keyword in call.keywords):
        return None
    end_offset = ast_offset(text, call.end_lineno, call.end_col_offset)
    if end_offset <= 0 or text[end_offset - 1:end_offset] != ")":
        return None
    start_offset = ast_offset(text, call.lineno, call.col_offset)
    before_close = text[start_offset:end_offset - 1].rstrip()
    insertion = ' encoding="utf-8"' if before_close.endswith(",") else ', encoding="utf-8"'
    line = call.lineno
    column = len(text.splitlines()[line - 1].encode("utf-8")[:call.col_offset].decode("utf-8")) + 1
    return {
        "id": finding_id("encoding", path, line, column),
        "path": path.resolve(),
        "line": line,
        "column": column,
        "insert_at": end_offset - 1,
        "insert_text": insertion,
        "before_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
    }


def encoding_findings_for_python(path: Path, text: str) -> list[dict]:
    tree = parse_python(text)
    if tree is None:
        return []
    findings = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not is_builtin_open(node) or open_has_encoding(node):
            continue
        mode = open_mode(node)
        if mode is not None and "b" in mode:
            continue
        offset = ast_offset(text, node.lineno, node.col_offset)
        candidate = encoding_fix_candidate(path, text, node)
        findings.append(new_finding(
            "encoding", path, text, offset, ast.get_source_segment(text, node) or "open(...)" ,
            autofix="safe" if candidate else "manual",
            note=None if candidate else "multi-line, dynamic, or non-standard call; review manually",
        ))
    return findings


def encoding_candidates_for_python(path: Path) -> list[dict]:
    if path.suffix.lower() != ".py":
        return []
    text, error = read_utf8_source(path)
    if error or text is None:
        return []
    tree = parse_python(text)
    if tree is None:
        return []
    candidates = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not is_builtin_open(node) or open_has_encoding(node):
            continue
        candidate = encoding_fix_candidate(path, text, node)
        if candidate:
            candidates.append(candidate)
    return candidates


def encoding_findings_for_markdown(path: Path, text: str) -> list[dict]:
    return [
        new_finding("encoding", path, text, match.start(), match.group(0))
        for match in markdown_text_open_matches(text)
    ]


def encoding_candidates_for_markdown(path: Path) -> list[dict]:
    if path.suffix.lower() != ".md":
        return []
    text, error = read_utf8_source(path)
    if error or text is None:
        return []
    before_sha256 = hashlib.sha256(text.encode("utf-8")).hexdigest()
    candidates = []
    for match in markdown_text_open_matches(text):
        line, column = line_and_column(text, match.start())
        candidates.append({
            "id": finding_id("encoding", path, line, column),
            "path": path.resolve(),
            "line": line,
            "column": column,
            "insert_at": match.end() - 1,
            # Markdown examples are often embedded in `python -c "..."`.
            # Single quotes keep that outer shell string valid.
            "insert_text": ", encoding='utf-8'",
            "before_sha256": before_sha256,
        })
    return candidates


def contains_glob_call(node: ast.AST) -> bool:
    return any(
        isinstance(item, ast.Call)
        and isinstance(item.func, ast.Attribute)
        and item.func.attr == "glob"
        for item in ast.walk(node)
    )


def name_sort_findings_for_python(path: Path, text: str) -> list[dict]:
    tree = parse_python(text)
    if tree is None:
        return []
    findings = []
    for node in ast.walk(tree):
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "sorted"
            and node.args
            and contains_glob_call(node.args[0])
        ):
            continue
        if any(keyword.arg == "key" for keyword in node.keywords):
            continue
        offset = ast_offset(text, node.lineno, node.col_offset)
        findings.append(new_finding(
            "name_sort", path, text, offset, ast.get_source_segment(text, node) or "sorted(glob(...))"
        ))
    return findings


def name_sort_findings_for_markdown(path: Path, text: str) -> list[dict]:
    findings = []
    for number, line in enumerate(text.splitlines(), 1):
        compact = line.replace(" ", "")
        if "sorted(" not in compact or ".glob(" not in compact or "key=" in compact:
            continue
        offset = sum(len(part) + 1 for part in text.splitlines()[:number - 1]) + line.find("sorted(")
        findings.append(new_finding("name_sort", path, text, offset, line.strip()))
    return findings


def regex_findings(vuln_type: str, path: Path, text: str) -> list[dict]:
    pattern = re.compile(VULN_PATTERNS[vuln_type]["re"], re.IGNORECASE)
    negative_reference = re.compile(
        r"(?:不再使用|不可用|禁止|不要使用|勿用|避免使用|已废弃|改用|替换为|不用).{0,36}"
        r"(?:execCommand|waitForTimeout|pkill)|"
        r"(?:execCommand|waitForTimeout|pkill).{0,36}(?:不可用|不再使用|禁止|不要使用|勿用|已废弃|改用|替换)",
        re.IGNORECASE,
    )
    findings = []
    for match in pattern.finditer(text):
        line, _ = line_and_column(text, match.start())
        if negative_reference.search(line_excerpt(text, line)):
            continue
        if vuln_type == "pkill" and path.suffix.lower() == ".md":
            block_start = text.rfind("```", 0, match.start())
            block_end = text.find("```", match.end())
            if block_start >= 0 and block_end >= 0:
                block = text[block_start:block_end]
                if "taskkill" in block and re.search(r"Windows.*(?:Linux|macOS)|(?:Linux|macOS).*Windows", block, re.IGNORECASE | re.DOTALL):
                    continue
        findings.append(new_finding(vuln_type, path, text, match.start(), match.group(0)))
    return findings


def scan_vulns(pattern_type: str | None = None, requested_paths: list[str] | None = None) -> dict:
    """Return line-level evidence for every selected vulnerability type."""
    if pattern_type and pattern_type not in VULN_TYPES:
        raise ValueError(f"unknown vulnerability type: {pattern_type}; choose from {', '.join(VULN_TYPES)}")
    selected = (pattern_type,) if pattern_type else VULN_TYPES
    targets = resolve_scan_targets(requested_paths)
    findings: list[dict] = []
    unreadable: list[dict] = []

    for path in targets:
        text, error = read_utf8_source(path)
        if error or text is None:
            unreadable.append({"file": relative_file(path), "error": error})
            continue
        is_python = path.suffix.lower() == ".py"
        is_markdown = path.suffix.lower() == ".md"
        for vuln_type in selected:
            if vuln_type == "encoding":
                if is_python:
                    findings.extend(encoding_findings_for_python(path, text))
                elif is_markdown:
                    findings.extend(encoding_findings_for_markdown(path, text))
            elif vuln_type == "name_sort":
                if is_python:
                    findings.extend(name_sort_findings_for_python(path, text))
                elif is_markdown:
                    findings.extend(name_sort_findings_for_markdown(path, text))
            elif vuln_type == "hardcoded_threshold" and is_markdown:
                # A literal quality gate belongs in a human SOP; only executable
                # code needs a named constant or configurable parameter.
                continue
            else:
                findings.extend(regex_findings(vuln_type, path, text))

    findings.sort(key=lambda item: (item["vuln_type"], item["file"].lower(), item["line"], item["column"]))
    by_type = {vuln_type: 0 for vuln_type in selected}
    for finding in findings:
        by_type[finding["vuln_type"]] += 1
    return {
        "pass": not findings and not unreadable,
        "scope": {
            "skills_root": relative_file(SKILLS_DIR),
            "entry_script_pattern": "run_*.py",
            "tools_excluded": True,
            "targeted": bool(requested_paths),
        },
        "summary": {
            "files_scanned": len(targets),
            "findings": len(findings),
            "unreadable_files": len(unreadable),
            "by_type": by_type,
        },
        "findings": findings,
        "unreadable": unreadable,
    }


MANUAL_REPAIR_GUIDANCE = {
    "encoding": "精确的一行文本 open() 可自动补 UTF-8；多行、动态或非 Python 调用需人工确认。",
    "pkill": "按进程所有权改为显式启动/停止逻辑；需要命令分派时调用 os_aware_run()，不可直接字符串替换。",
    "execCommand": "按目标编辑器实现 innerHTML/事件或编辑器 API，再做浏览器回归，不可泛化替换。",
    "name_sort": "仅在语义确为“取最新文件”时改用 newest_file(pattern, root)，保留需要稳定名称排序的场景。",
    "hardcoded_threshold": "将阈值提为具名常量或命令参数，并保留原有验收语义。",
    "fixed_wait": "改为等待可观测 DOM/API 条件，并在失败时记录证据。",
}


def build_repair_plan(pattern_type: str | None = None, requested_paths: list[str] | None = None) -> dict:
    targets = resolve_scan_targets(requested_paths)
    report = scan_vulns(pattern_type, requested_paths)
    safe_candidates = {
        candidate["id"]: candidate
        for path in targets
        for candidate in (encoding_candidates_for_python(path) + encoding_candidates_for_markdown(path))
    }
    actions = []
    for finding in report["findings"]:
        candidate = safe_candidates.get(finding["id"])
        if candidate and finding["vuln_type"] == "encoding":
            actions.append({
                "id": finding["id"],
                "file": finding["file"],
                "line": finding["line"],
                "vuln_type": "encoding",
                "strategy": "insert_utf8_encoding",
                "applyable": True,
                "detail": "在同一行文本 open() 的右括号前插入 encoding=\"utf-8\"",
            })
        else:
            actions.append({
                "id": finding["id"],
                "file": finding["file"],
                "line": finding["line"],
                "vuln_type": finding["vuln_type"],
                "strategy": "manual_review",
                "applyable": False,
                "detail": MANUAL_REPAIR_GUIDANCE[finding["vuln_type"]],
            })
    groups = []
    for vuln_type in VULN_TYPES:
        group_actions = [action for action in actions if action["vuln_type"] == vuln_type]
        if not group_actions:
            continue
        groups.append({
            "vuln_type": vuln_type,
            "action_count": len(group_actions),
            "safe_action_count": sum(action["applyable"] for action in group_actions),
            "affected_files": sorted({action["file"] for action in group_actions}),
            "next_action": MANUAL_REPAIR_GUIDANCE[vuln_type],
        })
    return {
        "pass": True,
        "dry_run": True,
        "scan_summary": report["summary"],
        "actions": actions,
        "groups": groups,
        "safe_action_count": sum(action["applyable"] for action in actions),
        "manual_action_count": sum(not action["applyable"] for action in actions),
    }


def write_source_atomically(path: Path, content: bytes) -> None:
    """Replace one source file without exposing a partially written version."""
    original_mode = path.stat().st_mode
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, original_mode)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def apply_encoding_candidates(
    candidates: list[dict],
    *,
    workspace_root: Path = WORK_DIR,
    backup_base: Path = REPAIR_BACKUP_BASE,
) -> dict:
    """Apply validated UTF-8 insertions as one recoverable transaction."""
    if not candidates:
        return {"pass": True, "changed_files": [], "manifest": None, "message": "no safe changes"}

    grouped: dict[Path, list[dict]] = {}
    for candidate in candidates:
        grouped.setdefault(candidate["path"], []).append(candidate)

    prepared = []
    for path, file_candidates in grouped.items():
        source = path.read_bytes()
        current_hash = hashlib.sha256(source).hexdigest()
        if any(candidate["before_sha256"] != current_hash for candidate in file_candidates):
            return {
                "pass": False,
                "error": f"source changed since plan: {relative_file(path, workspace_root)}",
                "changed_files": [],
                "manifest": None,
            }
        text = source.decode("utf-8")
        for candidate in sorted(file_candidates, key=lambda item: item["insert_at"], reverse=True):
            text = text[:candidate["insert_at"]] + candidate["insert_text"] + text[candidate["insert_at"]:]
        prepared.append((path, source, text.encode("utf-8"), file_candidates))

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    transaction_dir = backup_base / stamp
    manifest_path = transaction_dir / "manifest.json"
    entries = []
    changed = []
    try:
        for path, source, updated, file_candidates in prepared:
            relative = relative_file(path, workspace_root)
            backup_path = transaction_dir / "files" / relative
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, backup_path)
            write_source_atomically(path, updated)
            entries.append({
                "path": relative,
                "backup": str(backup_path.relative_to(transaction_dir)),
                "before_sha256": hashlib.sha256(source).hexdigest(),
                "after_sha256": sha256_of(path),
                "insertions": len(file_candidates),
            })
            changed.append((path, backup_path))
        manifest = {
            "version": 1,
            "kind": "skill_guard_encoding_fix",
            "created_at": datetime.now().isoformat(),
            "workspace": str(workspace_root.resolve()),
            "files": entries,
        }
        write_json(manifest_path, manifest)
        return {
            "pass": True,
            "changed_files": [entry["path"] for entry in entries],
            "manifest": str(manifest_path),
            "message": "safe UTF-8 fixes applied; use rollback <manifest> to restore",
        }
    except Exception as exc:
        for path, backup_path in reversed(changed):
            if backup_path.exists():
                write_source_atomically(path, backup_path.read_bytes())
        return {"pass": False, "error": str(exc), "changed_files": [], "manifest": None}


def rollback_repair(
    manifest_path: Path,
    *,
    workspace_root: Path = WORK_DIR,
    backup_base: Path = REPAIR_BACKUP_BASE,
) -> dict:
    """Restore a transaction only when no later edit has touched its targets."""
    manifest_path = manifest_path.resolve()
    if not _inside(manifest_path, backup_base) or not manifest_path.is_file():
        return {"pass": False, "error": "manifest must be inside .claude/skill_guard_backups"}
    manifest = read_json(manifest_path)
    entries = manifest.get("files", []) if isinstance(manifest, dict) else []
    conflicts = []
    validated = []
    for entry in entries:
        target = (workspace_root / entry.get("path", "")).resolve()
        backup = (manifest_path.parent / entry.get("backup", "")).resolve()
        if not _inside(target, workspace_root) or not _inside(backup, manifest_path.parent) or not backup.is_file():
            conflicts.append(entry.get("path", "<invalid path>"))
            continue
        if not target.is_file() or sha256_of(target) != entry.get("after_sha256"):
            conflicts.append(entry.get("path", "<changed file>"))
            continue
        validated.append((target, backup, entry.get("path", str(target))))
    if conflicts:
        return {
            "pass": False,
            "error": "rollback refused because a target changed or a backup is invalid",
            "conflicts": conflicts,
        }
    try:
        for target, backup, _ in validated:
            write_source_atomically(target, backup.read_bytes())
    except Exception as exc:
        return {"pass": False, "error": str(exc)}
    return {"pass": True, "restored_files": [relative for _, _, relative in validated]}


def execute_repair(
    pattern_type: str | None = None, *, apply: bool = False, requested_paths: list[str] | None = None
) -> dict:
    targets = resolve_scan_targets(requested_paths)
    plan = build_repair_plan(pattern_type, requested_paths)
    safe_ids = {action["id"] for action in plan["actions"] if action["applyable"]}
    candidates = [
        candidate
        for path in targets
        for candidate in (encoding_candidates_for_python(path) + encoding_candidates_for_markdown(path))
        if candidate["id"] in safe_ids
    ]
    result = {
        "pass": True,
        "applied": apply,
        "safe_action_count": plan["safe_action_count"],
        "manual_action_count": plan["manual_action_count"],
        "actions": plan["actions"],
    }
    if not apply:
        result["message"] = "dry run only; pass --apply to execute safe actions"
        return result
    applied = apply_encoding_candidates(candidates)
    result.update(applied)
    result["pass"] = bool(applied.get("pass"))
    if applied.get("pass"):
        result["post_scan_summary"] = scan_vulns(pattern_type, requested_paths)["summary"]
    return result


def print_scan(report: dict) -> None:
    for finding in report["findings"]:
        print(
            f"  [{finding['severity']:6s}] {finding['vuln_type']:20s} "
            f"{finding['file']}:{finding['line']}:{finding['column']} "
            f"({finding['autofix']})"
        )
    for item in report["unreadable"]:
        print(f"  [error ] unreadable           {item['file']}: {item['error']}")
    summary = report["summary"]
    print(
        f"\nscanned {summary['files_scanned']} files; "
        f"{summary['findings']} finding(s), {summary['unreadable_files']} unreadable"
    )


def print_plan(plan: dict) -> None:
    for group in plan.get("groups", []):
        print(
            f"  [GROUP ] {group['vuln_type']:20s} {group['action_count']} action(s) "
            f"across {len(group['affected_files'])} file(s)"
        )
    for action in plan["actions"]:
        state = "AUTO" if action["applyable"] else "MANUAL"
        print(f"  [{state:6s}] {action['vuln_type']:20s} {action['file']}:{action['line']}")
    print(
        f"\nsafe={plan['safe_action_count']} manual={plan['manual_action_count']} "
        f"(dry run; no files changed)"
    )


def parse_vulnerability_args(
    args: list[str], *, allow_apply: bool = False
) -> tuple[str | None, bool, bool, list[str]]:
    pattern_type = None
    as_json = False
    apply = False
    paths: list[str] = []
    index = 0
    while index < len(args):
        arg = args[index]
        if arg == "--json":
            as_json = True
        elif arg == "--apply" and allow_apply:
            apply = True
        elif arg == "--path":
            if index + 1 >= len(args):
                raise ValueError("--path needs a workspace-relative file or directory")
            index += 1
            paths.append(args[index])
        elif arg.startswith("--"):
            raise ValueError(f"unknown option: {arg}")
        elif pattern_type is None:
            pattern_type = arg
        else:
            raise ValueError(f"unexpected argument: {arg}")
        index += 1
    return pattern_type, as_json, apply, paths


# ═══════════════════════════════════════════════════════════════
# 九、主入口
# ═══════════════════════════════════════════════════════════════

def main():
    if len(sys.argv) < 2:
        print("usage: skill_guard.py <pre|post|audit|detect|test|scan|plan|fix|rollback> [args]", file=sys.stderr)
        sys.exit(2)

    mode = sys.argv[1]
    args = sys.argv[2:]

    try:
        if mode == "test":
            result = run_tests()
            print(json.dumps(result, ensure_ascii=False, indent=2))
            sys.exit(0 if result.get("pass") else 1)

        if mode in {"scan", "plan", "fix"}:
            pattern_type, as_json, apply, paths = parse_vulnerability_args(args, allow_apply=mode == "fix")
            if mode == "scan":
                result = scan_vulns(pattern_type, paths or None)
                if as_json:
                    print(json.dumps(result, ensure_ascii=False, indent=2))
                else:
                    print_scan(result)
                sys.exit(0 if result["pass"] else 1)
            if mode == "plan":
                result = build_repair_plan(pattern_type, paths or None)
                if as_json:
                    print(json.dumps(result, ensure_ascii=False, indent=2))
                else:
                    print_plan(result)
                sys.exit(0)
            result = execute_repair(pattern_type, apply=apply, requested_paths=paths or None)
            if as_json:
                print(json.dumps(result, ensure_ascii=False, indent=2))
            else:
                print_plan({"actions": result["actions"], "safe_action_count": result["safe_action_count"], "manual_action_count": result["manual_action_count"]})
                print(result.get("message", result.get("error", "")))
                if result.get("manifest"):
                    print(f"manifest: {result['manifest']}")
            sys.exit(0 if result.get("pass") else 1)

        if mode == "rollback":
            if not args:
                raise ValueError("rollback needs a manifest path")
            as_json = "--json" in args
            paths = [arg for arg in args if arg != "--json"]
            if len(paths) != 1:
                raise ValueError("rollback needs exactly one manifest path")
            result = rollback_repair(Path(paths[0]))
            print(json.dumps(result, ensure_ascii=False, indent=2))
            sys.exit(0 if result.get("pass") else 1)

        if len(args) < 1:
            raise ValueError(f"{mode} needs argument")
        target = args[0]
        extra = args[1:]
        if mode == "pre":
            result = pre_check(target)
        elif mode == "post":
            task_id = None; result_files = []; i = 0
            while i < len(extra):
                if extra[i] == "--task-id":
                    task_id = extra[i+1] if i+1 < len(extra) else None; i += 2
                elif extra[i] == "--result-files":
                    i += 1
                    while i < len(extra) and not extra[i].startswith("--"):
                        result_files.append(extra[i]); i += 1
                else:
                    i += 1
            if not task_id:
                raise ValueError("post needs --task-id")
            result = post_check(target, task_id, result_files or None)
        elif mode == "audit":
            result = audit_mode(Path(target))
        elif mode == "detect":
            result = detect_mode(Path(target))
        else:
            raise ValueError(f"unknown mode: {mode}")

        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(0 if result.get("pass") else 1)

    except Exception as exc:
        print(json.dumps({"pass": False, "error": str(exc)}, ensure_ascii=False))
        sys.exit(2)


if __name__ == "__main__":
    main()
