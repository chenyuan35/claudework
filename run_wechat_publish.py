#!/usr/bin/env python3
"""
run_wechat_publish.py -- 公众号发布状态机 v1.0
==============================================
无人值守全自动执行。非浏览器步骤脚本直接执行，浏览器步骤
输出指示供 Claude 通过 Playwright MCP 操作。

用法:
  python run_wechat_publish.py --status          # 查看当前状态
  python run_wechat_publish.py --step            # 执行当前 AUTO 步骤
  python run_wechat_publish.py --complete        # 标记当前 BROWSER 步骤完成
  python run_wechat_publish.py --dry-run         # 测试所有非浏览器步骤
  python run_wechat_publish.py --init TOPIC      # 初始化新会话
  python run_wechat_publish.py --rollback        # 回退到上一个恢复点
  python run_wechat_publish.py --reset           # 重置状态机
  python run_wechat_publish.py --abort REASON    # 异常终止

日志: logs/publish_YYYYMMDD.log
状态: session_state.json
"""

import hashlib, json, os, re, shutil, subprocess, sys, time, traceback
from datetime import datetime, timedelta
from pathlib import Path

# --- paths ---
WORKDIR = Path(r'C:\Users\59314\claudework')
SKILLDIR = Path(r'C:\Users\59314\.claude\skills\wechat-publish')
STATE_FILE = WORKDIR / 'session_state.json'
LOG_DIR = WORKDIR / 'logs'
BACKUP_DIR = WORKDIR / '_backups'
MAX_BACKUPS = 10
BACKUP_DAYS = 7

LOG_DIR.mkdir(parents=True, exist_ok=True)
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

# --- state definition ---
# each state: (name, category, description, max_retries, is_recovery_point)
# category: auto=bash script runs it, browser=claude via playwright, terminal=end state
STATES_DEF = [
    ('init',        'auto',     '初始化: 检查目录/依赖',             1, True),
    ('topic',       'browser',  '选题: 确定文章主题和标题',           2, True),
    ('write',       'auto',     '写作: 生成文章并保存 .txt',          2, True),
    ('qa_para',     'auto',     '段长闸: check_wechat_para.py',       2, False),
    ('qa_ai',       'auto',     'AI味闸: ai_score.py',               2, False),
    ('image_gen',   'auto',     '生图: cover.jpg + inline1-3',       2, True),
    ('dedup',       'browser',  '去重: Playwright提取已发表标题',     2, True),
    ('cors',        'auto',     'CORS服务: 启动HTTP服务器',           2, True),
    ('editor_open', 'browser',  '编辑器: 打开新文章编辑页',           2, True),
    ('title_author','browser',  '标题作者: 填入编辑器',               2, False),
    ('image_upload','browser',  '插图上传: 3张一次传完获取CDN',       2, True),
    ('bake',        'auto',     '烘焙: bake_wechat_html.py',          2, False),
    ('validate',    'auto',     '门禁: validate_wechat_html.py',      2, True),
    ('insert',      'browser',  '插入正文: 清空并逐块insertHTML',    2, True),
    ('visual_check','browser',  '视觉检查: 截图验证排版',             2, True),
    ('cover',       'browser',  '封面: 上传并设置封面图',             2, True),
    ('final_verify','browser',  '终极验证: DOM+CDN+表情+封面',        2, True),
    ('save',        'browser',  '保存草稿',                           2, True),
    ('review',      'auto',     '复盘: 更新选题账本',                 1, False),
    ('skill_fix',   'auto',     '技能修复: 固化本次经验',             1, False),
    ('cleanup',     'auto',     '清理: 临时文件+备份轮换',            1, False),
    ('done',        'terminal', '完成',                               0, True),
    ('error',       'terminal', '异常终止: 需人工介入',               0, True),
]

STATE_NAMES = [s[0] for s in STATES_DEF]


# --- utilities ---

def log(msg, level='INFO'):
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    line = f'[{ts}] [{level:5s}] {msg}'
    print(line, flush=True)
    logfile = LOG_DIR / f"publish_{datetime.now().strftime('%Y%m%d')}.log"
    with open(logfile, 'a', encoding='utf-8') as f:
        f.write(line + '\n')


def escape_path(p):
    """Convert backslashes to forward for shell safety."""
    return str(p).replace('\\', '/')


def run(cmd, timeout=120):
    """Run a shell command, return (rc, stdout, stderr)."""
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                          timeout=timeout, cwd=str(WORKDIR))
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return -1, '', 'TIMEOUT'
    except Exception as e:
        return -1, '', str(e)


# --- state persistence ---

DEFAULT_STATE = {
    'version': '2',
    'current_state': 'init',
    'retry_count': 0,
    'last_recovery': '',
    'history': [],
    'topic': '',
    'title': '',
    'article_file': '',
    'image_article_sha256': '',
    'image_manifest': '',
    'content_pillar': '',
    'marketing_job': '',
    'topic_score': 0,
    'topic_evidence': '',
    'actionable_asset': '',
    'pillar_counts_last10': {},
    'age_title_count_last10': 0,
    'cdn_urls': [],
    'draft_url': '',
    'appmsgid': '',
    'token': '',
    'created_at': '',
    'updated_at': '',
    'errors': [],
    'logs': [],
}


def load_state():
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text('utf-8'))
        except:
            log('state file corrupt, resetting', 'WARN')
    s = dict(DEFAULT_STATE)
    s['created_at'] = datetime.now().isoformat()
    return s


def save_state(state):
    state['updated_at'] = datetime.now().isoformat()
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), 'utf-8')
    log(f'state saved: {state["current_state"]}')


def current_step_idx(state):
    try:
        return STATE_NAMES.index(state['current_state'])
    except ValueError:
        return 0


# --- heartbeat ---

HEARTBEAT_FILE = WORKDIR / '_publish_heartbeat.txt'


def write_heartbeat(state_name):
    ts = datetime.now().isoformat()
    HEARTBEAT_FILE.write_text(f'{ts} {state_name}', 'utf-8')


def check_heartbeat():
    if not HEARTBEAT_FILE.exists():
        return True
    content = HEARTBEAT_FILE.read_text('utf-8').strip()
    if not content:
        return True
    parts = content.split(' ', 1)
    if len(parts) < 2:
        return True
    try:
        last_ts = datetime.fromisoformat(parts[0])
        elapsed = (datetime.now() - last_ts).total_seconds()
        if elapsed > 300:  # 5 min
            log(f'heartbeat stale: {elapsed:.0f}s since {parts[0]}', 'WARN')
            return False
        return True
    except:
        return True


# --- backup ---

def create_backup():
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = BACKUP_DIR / ts
    backup_path.mkdir(exist_ok=True)
    for f in ['wechat_article_*.txt', 'article_final.html', 'session_state.json']:
        for p in WORKDIR.glob(f):
            shutil.copy2(p, backup_path / p.name)
    log(f'backup created: {ts}')


def rotate_backups():
    """Keep last MAX_BACKUPS backups, remove older than BACKUP_DAYS."""
    backups = sorted(BACKUP_DIR.iterdir())
    cutoff = datetime.now() - timedelta(days=BACKUP_DAYS)
    for b in backups:
        if not b.is_dir():
            continue
        try:
            mtime = datetime.fromtimestamp(b.stat().st_mtime)
            if mtime < cutoff:
                shutil.rmtree(b)
                log(f'old backup removed: {b.name}')
        except:
            pass
    backups = sorted([b for b in BACKUP_DIR.iterdir() if b.is_dir()])
    while len(backups) > MAX_BACKUPS:
        old = backups.pop(0)
        shutil.rmtree(old)
        log(f'excess backup removed: {old.name}')


# --- step runners (auto steps) ---

def step_auto_init(state):
    """Check that workdir, scripts, and python exist."""
    checks = [
        ('workdir', WORKDIR.exists()),
        ('skill dir', SKILLDIR.exists()),
    ]
    for name, ok in checks:
        if not ok:
            log(f'init check FAIL: {name}', 'ERROR')
            return False
    # Python deps
    for script in ['bake_wechat_html.py', 'check_wechat_para.py',
                   'ai_score.py', 'validate_wechat_html.py']:
        if not (WORKDIR / script).exists():
            log(f'missing script: {script}', 'ERROR')
            return False
    log('init checks passed')
    return True


def step_auto_write(state):
    """Enforce brand strategy and validate the exact article selected in topic state."""
    valid_pillars = {'谋生工具箱', '人性账本', '现实选择题'}
    valid_jobs = {'搜索拉新', '信任建立', '收藏沉淀'}
    pillar = state.get('content_pillar', '')
    job = state.get('marketing_job', '')
    if pillar not in valid_pillars or job not in valid_jobs:
        log(f'strategy metadata FAIL: pillar={pillar!r} job={job!r}', 'ERROR')
        return False
    try:
        topic_score = int(state.get('topic_score', 0))
    except (TypeError, ValueError):
        topic_score = 0
    if topic_score < 75:
        log(f'topic score FAIL: {topic_score} < 75', 'ERROR')
        return False
    if not state.get('topic_evidence') or not state.get('actionable_asset'):
        log('topic evidence/actionable asset missing', 'ERROR')
        return False

    title = state.get('title', '').strip()
    age_count = int(state.get('age_title_count_last10', 0) or 0)
    has_age_label = bool(re.search(r'人到中年|中年人|中年|四十岁|五十岁|40岁|50岁', title))
    if has_age_label and age_count >= 2:
        log(f'age-label cap FAIL: last10 already has {age_count}', 'ERROR')
        return False

    article_path = state.get('article_file', '')
    af = Path(article_path) if article_path else None
    if not af or not af.exists():
        articles = list(WORKDIR.glob('wechat_article_*.txt'))
        if not articles:
            log('no article file found', 'ERROR')
            return False
        af = max(articles, key=lambda p: p.stat().st_mtime)
    text = af.read_text('utf-8')
    article_title = text.splitlines()[0].strip().lstrip('#').strip()
    if not title or article_title != title:
        log(f'title mismatch: state={title!r} article={article_title!r}', 'ERROR')
        return False
    cn = len(re.findall(r'[一-鿿豈-﫿]', text))
    if not 2400 <= cn <= 2800:
        log(f'article length FAIL: {cn}, expect 2400-2800 hanzi', 'ERROR')
        return False
    state['article_file'] = str(af)
    log(f'article ok: {af.name} ({cn} hanzi, {pillar}/{job}, score={topic_score})')
    return True


def step_auto_qa_para(state):
    """Run paragraph gate."""
    af = state.get('article_file', '')
    if not af:
        log('no article file in state', 'ERROR')
        return False
    rc, out, err = run(f'python {escape_path(WORKDIR)}/check_wechat_para.py {escape_path(af)}')
    if rc != 0:
        log(f'para gate FAIL (rc={rc}): {out[:200]} {err[:200]}', 'ERROR')
        return False
    log(f'para gate PASS')
    return True


def step_auto_qa_ai(state):
    """Run AI score gate."""
    af = state.get('article_file', '')
    if not af:
        log('no article file in state', 'ERROR')
        return False
    rc, out, err = run(f'python {escape_path(WORKDIR)}/ai_score.py {escape_path(af)} --threshold 45')
    if rc != 0:
        log(f'AI gate FAIL (rc={rc}): {out[:200]} {err[:200]}', 'ERROR')
        return False
    log(f'AI gate PASS')
    return True


def step_auto_image_gen(state):
    """Generate an article-bound four-image package and reject stale images."""
    af = state.get('article_file', '')
    article_path = Path(af) if af else None
    if not article_path or not article_path.exists():
        log('image generation FAIL: article file missing', 'ERROR')
        return False

    imgs = [WORKDIR / 'cover.jpg'] + [WORKDIR / f'inline{i}.jpg' for i in range(1, 4)]
    manifest_path = WORKDIR / 'image_manifest.json'
    article_sha = hashlib.sha256(article_path.read_bytes()).hexdigest()

    def valid_manifest(path, expected_dir):
        try:
            manifest = json.loads(path.read_text('utf-8'))
            if manifest.get('article_sha256') != article_sha:
                return False, 'article fingerprint mismatch', None
            records = manifest.get('images', [])
            by_name = {item.get('file'): item for item in records}
            expected_names = {'cover.jpg', 'inline1.jpg', 'inline2.jpg', 'inline3.jpg'}
            if set(by_name) != expected_names:
                return False, 'manifest must contain exactly four images', None
            inline_scenes = []
            for name in expected_names:
                image_path = expected_dir / name
                record = by_name[name]
                if not image_path.exists() or image_path.stat().st_size < 10000:
                    return False, f'{name} missing or smaller than 10KB', None
                actual_sha = hashlib.sha256(image_path.read_bytes()).hexdigest()
                if record.get('sha256') != actual_sha:
                    return False, f'{name} hash mismatch', None
                if name.startswith('inline'):
                    scene = re.sub(r'\s+', '', record.get('scene', ''))
                    if len(scene) < 20:
                        return False, f'{name} has no usable article scene', None
                    inline_scenes.append(scene)
            if len(set(inline_scenes)) != 3:
                return False, 'inline scenes are not distinct', None
            return True, 'ok', manifest
        except Exception as exc:
            return False, str(exc), None

    current_ok, current_reason, current_manifest = valid_manifest(manifest_path, WORKDIR)
    if current_ok:
        state['image_article_sha256'] = article_sha
        state['image_manifest'] = str(manifest_path)
        log(f'images match current article, resume package sha256={article_sha[:12]}')
        return True

    log(f'generating fresh article-bound images ({current_reason})...')
    stage_dir = (WORKDIR / '_wechat_image_stage').resolve()
    if stage_dir.parent != WORKDIR.resolve():
        log(f'image stage path escaped workspace: {stage_dir}', 'ERROR')
        return False
    if stage_dir.exists():
        shutil.rmtree(stage_dir)
    stage_dir.mkdir(parents=True)

    cmd = [
        sys.executable,
        str(WORKDIR / 'auto_gen_images.py'),
        str(article_path),
        '--out-dir',
        str(stage_dir),
    ]
    try:
        result = subprocess.run(
            cmd,
            cwd=str(WORKDIR),
            capture_output=True,
            text=True,
            timeout=600,
        )
    except subprocess.TimeoutExpired:
        log('image generation TIMEOUT after 600s', 'ERROR')
        return False
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or 'unknown error').strip()[-500:]
        log(f'image generation FAIL: {detail}', 'ERROR')
        return False

    stage_manifest = stage_dir / 'image_manifest.json'
    stage_ok, stage_reason, stage_data = valid_manifest(stage_manifest, stage_dir)
    if not stage_ok:
        log(f'image package gate FAIL: {stage_reason}', 'ERROR')
        return False

    for image_path in imgs:
        os.replace(stage_dir / image_path.name, image_path)
    os.replace(stage_manifest, manifest_path)
    shutil.rmtree(stage_dir)
    state['image_article_sha256'] = article_sha
    state['image_manifest'] = str(manifest_path)
    sections = [
        item['section_title'] for item in stage_data['images']
        if item['file'].startswith('inline')
    ]
    log(f'all images generated for article sha256={article_sha[:12]}, sections={sections}')
    return True


def step_auto_cors(state):
    """Start the bundled CORS image server in a hidden background process."""
    import socket
    import urllib.request

    port = 8768
    while port < 8788:
        with socket.socket() as probe:
            try:
                probe.bind(('127.0.0.1', port))
                break
            except OSError:
                port += 1
    if port >= 8788:
        log('CORS start FAIL: no free port in 8768-8787', 'ERROR')
        return False

    cmd = [sys.executable, str(WORKDIR / 'img_server.py'), str(port)]
    popen_kwargs = {
        'cwd': str(WORKDIR),
        'stdin': subprocess.DEVNULL,
        'stdout': subprocess.DEVNULL,
        'stderr': subprocess.DEVNULL,
    }
    if os.name == 'nt':
        popen_kwargs['creationflags'] = (
            subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP
        )
    proc = subprocess.Popen(cmd, **popen_kwargs)
    (WORKDIR / '_cors_port.txt').write_text(str(port), 'utf-8')
    (WORKDIR / '_cors_pid.txt').write_text(str(proc.pid), 'utf-8')

    url = f'http://127.0.0.1:{port}/cover.jpg'
    for _ in range(20):
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                if response.status == 200:
                    state['cors_port'] = port
                    log(f'CORS running on {port}')
                    return True
        except Exception:
            time.sleep(0.25)

    log(f'CORS start FAIL: {url} unavailable', 'ERROR')
    return False


def step_auto_bake(state):
    """Run bake_wechat_html.py with CDN URLs (or test URLs in dry-run)."""
    cdn = state.get('cdn_urls', [])
    if len(cdn) < 3:
        if os.environ.get('RUN_MODE') == 'dry-run' or '--dry-run' in ' '.join(sys.argv):
            cdn = ['data:image/gif;base64,R0lGODlhAQABAAAAACwAAAAAAQABAAA='] * 3
            log('dry-run: using placeholder URLs')
        else:
            log(f'need 3 CDN urls, got {len(cdn)}', 'ERROR')
            return False
    af = state.get('article_file', '')
    if not af:
        log('no article file', 'ERROR')
        return False
    # Use list-based subprocess to avoid shell & escaping issues
    bake_script = escape_path(WORKDIR) + '/bake_wechat_html.py'
    cmd_list = ['python', bake_script, escape_path(af), '--auto-position']
    for url in cdn[:3]:
        cmd_list += ['--cdn', url]
    try:
        r = subprocess.run(cmd_list, capture_output=True, text=True, timeout=120, cwd=str(WORKDIR))
        rc, out, err = r.returncode, r.stdout, r.stderr
    except Exception as e:
        log(f'bake exception: {e}', 'ERROR')
        return False
    if rc != 0:
        log(f'bake FAIL: {out[:200]} {err[:200]}', 'ERROR')
        return False
    log(f'bake OK: {out.strip()}')
    return True


def step_auto_validate(state):
    """Run validate_wechat_html.py."""
    rc, out, err = run(
        f'python {escape_path(WORKDIR)}/validate_wechat_html.py '
        f'{escape_path(WORKDIR)}/article_final.html --min-chars 2400 --max-chars 3000 --img-count 3'
    )
    if rc != 0:
        log(f'validate FAIL: {out[:300]} {err[:300]}', 'ERROR')
        return False
    log('validate PASS')
    return True


def step_auto_review(state):
    """Record the strategy classification carried by the completed draft."""
    log(
        f'review recorded: {state.get("content_pillar", "")}/'
        f'{state.get("marketing_job", "")} score={state.get("topic_score", 0)}'
    )
    return True


def step_auto_skill_fix(state):
    """After publish, fix SKILL.md with any insights."""
    log('skill fix step: find and fix SKILL.md issues')
    return True


def step_auto_cleanup(state):
    """Remove temp files, rotate backups."""
    pid_file = WORKDIR / '_cors_pid.txt'
    if pid_file.exists():
        try:
            server_pid = int(pid_file.read_text('utf-8').strip())
            if os.name == 'nt':
                subprocess.run(
                    ['taskkill', '/PID', str(server_pid), '/T', '/F'],
                    capture_output=True,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                    timeout=10,
                )
            else:
                os.kill(server_pid, 15)
        except Exception as e:
            log(f'CORS cleanup warning: {e}', 'WARN')
        pid_file.unlink(missing_ok=True)
    patterns = ['voice_temp.*', 'test_*.mp3', 'test_*.wav', 'article_audio.*',
                'audio_*.mp3', '_cors_port.txt', '_publish_heartbeat.txt']
    for pat in patterns:
        for f in WORKDIR.glob(pat):
            f.unlink(missing_ok=True)
    # Keep article_final.html and article .txt (draft evidence)
    rotate_backups()
    log('cleanup done')
    return True


# --- state machine dispatch ---

AUTO_HANDLERS = {
    'init': step_auto_init,
    'write': step_auto_write,
    'qa_para': step_auto_qa_para,
    'qa_ai': step_auto_qa_ai,
    'image_gen': step_auto_image_gen,
    'cors': step_auto_cors,
    'bake': step_auto_bake,
    'validate': step_auto_validate,
    'review': step_auto_review,
    'skill_fix': step_auto_skill_fix,
    'cleanup': step_auto_cleanup,
}


def run_current_step(state):
    """Execute the current step if it's AUTO type. Return True on success."""
    name = state['current_state']
    idx = current_step_idx(state)
    if idx >= len(STATES_DEF):
        return False
    sdef = STATES_DEF[idx]
    cat = sdef[1]

    write_heartbeat(name)
    log(f'--- step [{idx}] {name} ({cat}) ---')

    if cat == 'browser':
        log(f'browser step requires Claude to execute: {sdef[2]}', 'INFO')
        return 'BROWSER'

    if cat == 'terminal':
        log(f'terminal state: {name}', 'INFO')
        return True

    handler = AUTO_HANDLERS.get(name)
    if not handler:
        log(f'no handler for {name}', 'ERROR')
        return False

    try:
        ok = handler(state)
    except Exception as e:
        log(f'handler {name} exception: {e}', 'ERROR')
        traceback.print_exc()
        ok = False

    if ok:
        advance_state(state)
        return True
    else:
        state['retry_count'] = state.get('retry_count', 0) + 1
        sdef = STATES_DEF[current_step_idx(state)]
        max_retries = sdef[3]
        if state['retry_count'] > max_retries:
            log(f'step {name} failed after {max_retries} retries', 'ERROR')
            state['current_state'] = 'error'
            state['errors'] = state.get('errors', []) + [f'{name}: max retries']
            save_state(state)
            return False
        log(f'step {name} failed (retry {state["retry_count"]}/{max_retries})', 'WARN')
        return False


def advance_state(state):
    """Move to next state, respecting recovery points."""
    idx = current_step_idx(state)
    sdef = STATES_DEF[idx]
    if sdef[4]:  # is_recovery_point
        state['last_recovery'] = state['current_state']
    state['retry_count'] = 0
    if idx + 1 < len(STATES_DEF):
        next_name = STATES_DEF[idx + 1][0]
        state['current_state'] = next_name
    else:
        state['current_state'] = 'done'
    state['history'] = state.get('history', []) + [sdef[0]]
    save_state(state)


# --- CLI ---

def cli_status(state):
    idx = current_step_idx(state)
    sdef = STATES_DEF[idx] if idx < len(STATES_DEF) else None
    print('=' * 55)
    print(f'  状态: {state["current_state"]}')
    if sdef:
        print(f'  类型: {sdef[1]}')
        print(f'  描述: {sdef[2]}')
        print(f'  重试: {state["retry_count"]}/{sdef[3]}')
    print(f'  恢复点: {state["last_recovery"]}')
    if state.get('appmsgid'):
        print(f'  草稿: appmsgid={state["appmsgid"]}')
    if state.get('draft_url'):
        print(f'  URL: {state["draft_url"]}')
    print(f'  更新: {state["updated_at"]}')
    log_date = datetime.now().strftime('%Y%m%d')
    print(f'  日志: {LOG_DIR / f"publish_{log_date}.log"}')
    print(f'  步骤数: {len(state.get("history", []))}')
    if state.get('errors'):
        print(f'  错误: {state["errors"][-1]}')
    print('=' * 55)


def cli_dry_run(state):
    """Run all auto steps without browser interaction."""
    log('=== DRY RUN START ===')
    os.environ['RUN_MODE'] = 'dry-run'
    max_steps = 50
    for _ in range(max_steps):
        write_heartbeat(state['current_state'])
        idx = current_step_idx(state)
        if idx >= len(STATES_DEF):
            break
        sdef = STATES_DEF[idx]
        if sdef[1] == 'terminal':
            log(f'reached terminal state: {state["current_state"]}')
            break
        if sdef[1] == 'browser':
            log(f'BROWSER step {state["current_state"]}: SKIP in dry-run')
            advance_state(state)
            continue
        ok = run_current_step(state)
        if not ok:
            log(f'DRY RUN FAILED at {state["current_state"]}', 'ERROR')
            return False
        if state['current_state'] == 'done':
            break
    log('=== DRY RUN COMPLETE ===')
    cli_status(load_state())
    return True


# --- regression test ---

REGRESSION_SCRIPT = """
() => {
  const bp = document.querySelectorAll('.ProseMirror')[1];
  if (!bp) return {pass: false, error: 'no editor body'};
  const sections = bp.children;
  const t = bp.innerText;
  const preview = document.querySelector('.js_cover_preview_new');
  const hasCover = preview ? /mmbiz/.test(getComputedStyle(preview).backgroundImage) : false;
  let dotCount = 0, imgIdx = [];
  for (let i = 0; i < sections.length; i++) {
    const txt = sections[i].innerText.trim();
    if (/^\\.+$/.test(txt)) dotCount++;
    if (sections[i].querySelector('img')) imgIdx.push(i);
  }
  const textTotal = total - imgIdx.length; // count only text paras
  const imgPcts = imgIdx.map(idx => Math.round((idx / textTotal) * 100));
  const subtitles = (t.match(/[一二三四五六七八九十]+、/g) || []).length;
  const passes = [
    hasCover,                                       // 0: cover exists
    dotCount === 0,                                 // 1: no dot paragraphs
    imgIdx.length === 3,                            // 2: exactly 3 images
    imgPcts.every((p, i) => Math.abs(p - [25,55,82][i]) <= 5),  // 3: positions within 5%
    subtitles >= 4 && subtitles <= 7                // 4: 4-7 subtitles
  ];
  return {
    pass: passes.every(Boolean),
    checks: { hasCover, dotCount, imgCount: imgIdx.length, imgPcts, subtitles },
    details: passes
  };
}
"""


def cli_regression_test():
    log('=== REGRESSION TEST START ===')
    # The test must be run in the browser context via Playwright
    # This CLI just prints the expected check format
    print('Run in browser:')
    print(REGRESSION_SCRIPT)
    print()
    print('pass=false → rollback + re-run golden path')
    log('=== REGRESSION TEST READY ===')


def main():
    state = load_state()

    if len(sys.argv) < 2:
        cli_status(state)
        return

    cmd = sys.argv[1]

    if cmd == '--status':
        cli_status(state)
    elif cmd == '--step':
        ok = run_current_step(state)
        if not ok:
            # browser steps still need claude
            idx = current_step_idx(state)
            if idx < len(STATES_DEF) and STATES_DEF[idx][1] == 'browser':
                print(f'NEEDS_BROWSER:{state["current_state"]}')
                sys.exit(0)
            sys.exit(1)
    elif cmd == '--complete':
        advance_state(state)
        log(f'browser step completed, advanced to {state["current_state"]}')
    elif cmd == '--dry-run':
        cli_dry_run(state)
    elif cmd == '--regression-test':
        cli_regression_test()
    elif cmd == '--init':
        topic = ' '.join(sys.argv[2:]) if len(sys.argv) > 2 else ''
        state = dict(DEFAULT_STATE)
        state['created_at'] = datetime.now().isoformat()
        state['topic'] = topic
        save_state(state)
        log(f'state initialized (topic: {topic or "auto"}')
    elif cmd == '--rollback':
        recovery = state.get('last_recovery', 'init')
        if recovery in STATE_NAMES:
            state['current_state'] = recovery
            state['retry_count'] = 0
            save_state(state)
            log(f'rolled back to {recovery}')
    elif cmd == '--reset':
        state = dict(DEFAULT_STATE)
        state['created_at'] = datetime.now().isoformat()
        save_state(state)
        log('state reset')
    elif cmd == '--abort':
        reason = ' '.join(sys.argv[2:]) if len(sys.argv) > 2 else 'manual abort'
        state['current_state'] = 'error'
        state['errors'] = state.get('errors', []) + [reason]
        save_state(state)
        log(f'aborted: {reason}', 'ERROR')
    else:
        print(f'unknown command: {cmd}')
        print(__doc__)


if __name__ == '__main__':
    main()
