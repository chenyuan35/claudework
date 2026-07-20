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

import json, os, re, shutil, subprocess, sys, time, traceback
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
    ('topic',       'auto',     '选题: 确定文章主题和标题',           2, True),
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
    'version': '1',
    'current_state': 'init',
    'retry_count': 0,
    'last_recovery': '',
    'history': [],
    'topic': '',
    'title': '',
    'article_file': '',
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


def step_auto_topic(state):
    """Select topic and write article skeleton."""
    # Claude writes the article; this step signals Claude to do it
    # For auto mode, just validate the topic exists
    log('topic step: awaiting Claude to write article')
    return True


def step_auto_write(state):
    """Check article file exists and meets basic requirements."""
    articles = sorted(WORKDIR.glob('wechat_article_*.txt'))
    if not articles:
        log('no article file found', 'ERROR')
        return False
    af = articles[-1]
    text = af.read_text('utf-8')
    cn = len(re.findall(r'[一-鿿]', text))
    if cn < 2000:
        log(f'article too short: {cn} chars', 'ERROR')
        return False
    state['article_file'] = str(af)
    log(f'article ok: {af.name} ({cn} chars)')
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
    """Generate cover + inline images. Skip if already exist."""
    af = state.get('article_file', '')
    imgs = [WORKDIR / 'cover.jpg'] + [WORKDIR / f'inline{i}.jpg' for i in range(1, 4)]
    all_exist = all(i.exists() and i.stat().st_size >= 10000 for i in imgs)

    if all_exist:
        log('images already exist, skip generation')
        return True

    log('generating images...')
    if af:
        rc, out, err = run(f'python {escape_path(WORKDIR)}/auto_gen_images.py {escape_path(af)}', timeout=600)
        if rc == 0 or rc is None:
            pass  # might have succeeded even with odd rc

    # verify
    missing = [i.name for i in imgs if not i.exists() or i.stat().st_size < 10000]
    if missing:
        log(f'missing images: {missing}', 'ERROR')
        return False
    log('all images generated')
    return True


def step_auto_cors(state):
    """Start CORS HTTP server in background. Keep port in state."""
    script = (
        f'import http.server, socketserver, os, socket, threading; '
        f'os.chdir(r"{escape_path(WORKDIR)}"); '
        f'class H(http.server.SimpleHTTPRequestHandler): '
        f'  def end_headers(self): '
        f'    self.send_header("Access-Control-Allow-Origin", "*"); '
        f'    super().end_headers(); '
        f'  def log_message(self, *a): pass; '
        f'port=8768; '
        f'while True: '
        f'  s=socket.socket(); '
        f'  try: s.bind(("127.0.0.1",port)); s.close(); break; '
        f'  except OSError: port+=1; '
        f'print("PORT",port); '
        f'with open(r"{escape_path(WORKDIR)}/_cors_port.txt","w") as f: f.write(str(port)); '
        f'socketserver.TCPServer(("127.0.0.1",port), H).serve_forever()'
    )
    # kill existing first
    run('pkill -f "socketserver.TCPServer" 2>/dev/null || true')
    run(f'python -c "{script}" &', timeout=5)
    time.sleep(2)
    # read port
    port_file = WORKDIR / '_cors_port.txt'
    if port_file.exists():
        port = int(port_file.read_text('utf-8').strip())
        state['cors_port'] = port
    else:
        state['cors_port'] = 8768
    # verify
    rc, out, err = run(f'curl -s -o /dev/null -w "%{{http_code}}" http://127.0.0.1:{state["cors_port"]}/cover.jpg')
    if '200' in out:
        log(f'CORS running on {state["cors_port"]}')
        return True
    log('CORS start FAIL', 'ERROR')
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
    cmd = f'python {escape_path(WORKDIR)}/bake_wechat_html.py {escape_path(af)}'
    for url in cdn[:3]:
        cmd += f' "{url}"'
    rc, out, err = run(cmd)
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
    """Post-publish review. Update topic ledger."""
    log('review step: update topic ledger')
    return True


def step_auto_skill_fix(state):
    """After publish, fix SKILL.md with any insights."""
    log('skill fix step: find and fix SKILL.md issues')
    return True


def step_auto_cleanup(state):
    """Remove temp files, rotate backups."""
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
    'topic': step_auto_topic,
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
