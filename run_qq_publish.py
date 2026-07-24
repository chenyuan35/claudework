#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""run_qq_publish.py - Q-zone publish state machine v1.0

Auto-execute for non-browser steps; browser steps output
instructions for Claude to execute via Playwright MCP.

Usage:
  python run_qq_publish.py --status
  python run_qq_publish.py --step
  python run_qq_publish.py --complete
  python run_qq_publish.py --dry-run
  python run_qq_publish.py --init TOPIC
  python run_qq_publish.py --rollback
  python run_qq_publish.py --reset
  python run_qq_publish.py --abort REASON
"""

import json, os, re, shutil, subprocess, sys, time, traceback
from datetime import datetime, timedelta
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlopen
import random

WORKDIR = Path(__file__).resolve().parent
TOOLS_DIR = WORKDIR / '.claude' / 'skills' / 'tools'
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))
from platform_utils import configure_utf8_stdio, newest_file, read_json, write_json

configure_utf8_stdio()
SKILLDIR = WORKDIR / '.claude' / 'skills' / 'qq-publish'
STATE_FILE = WORKDIR / 'session_state.json'
LOG_DIR = WORKDIR / 'logs'
BACKUP_DIR = WORKDIR / '_qq_backups'
MAX_BACKUPS = 10
BACKUP_DAYS = 7
QQ_PUBLISH_MIN_HANZI = 3000

LOG_DIR.mkdir(parents=True, exist_ok=True)
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

STATES_DEF = [
    ('init',           'auto',     'init: check dirs/deps',                   1, True),
    ('dedup',          'browser',  'dedup: extract titles from content mgmt', 2, True),
    ('topic',          'browser',  'topic+write: select topic + write',       2, True),
    ('write_verify',   'auto',     'verify: hanzi/h2/para quality gate',     2, True),
    ('image_gen',      'auto',     'image: generate cover.jpg (5-element)',   2, True),
    ('cors',           'auto',     'cors: start HTTP server port 8768',       2, True),
    ('editor_open',    'browser',  'editor: navigate to new article page',    2, True),
    ('title_input',    'browser',  'title: fill in title span',               2, False),
    ('cover_upload',   'browser',  'cover: DataTransfer upload cover.jpg',    2, True),
    ('body_insert',    'browser',  'body: insertHTML into ProseMirror',       2, True),
    ('body_img_upload','browser',  'body imgs: DataTransfer upload inline',   2, True),
    ('tags',           'browser',  'tags: input 3 tag chips',                 2, False),
    ('category',       'browser',  'category: select game category',          2, False),
    ('ai_declaration', 'browser',  'AI declare: OP7 + OP8',                   2, False),
    ('publish',        'browser',  'publish: click publish button',           2, True),
    ('publish_verify', 'browser',  'verify: confirm publish success',         2, False),
    ('review',         'auto',     'review: update topic ledger',              1, False),
    ('cleanup',        'auto',     'cleanup: temp files + backup rotation',   1, False),
    ('done',           'terminal', 'done',                                     0, True),
    ('error',          'terminal', 'error: need human intervention',           0, True),
]

STATE_NAMES = [s[0] for s in STATES_DEF]

# --- utilities ---

def log(msg, level="INFO"):
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    line = f'[{ts}] [{level:5s}] {msg}'
    print(line, flush=True)
    logfile = LOG_DIR / f"qq_publish_{datetime.now().strftime('%Y%m%d')}.log"
    with open(logfile, 'a', encoding='utf-8') as f:
        f.write(line + chr(10))

def escape_path(p):
    return str(p).replace(chr(92), "/")

def run(cmd, timeout=120):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                          encoding='utf-8', errors='replace', timeout=timeout, cwd=str(WORKDIR))
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return -1, '', 'TIMEOUT'
    except Exception as e:
        return -1, '', str(e)

def count_hanzi(text):
    return len(re.findall(r'[一-鿿豈-﫿]', text))

# --- state persistence ---

DEFAULT_STATE = {
    'version': '1',
    'current_state': 'init',
    'retry_count': 0,
    'last_recovery': '',
    'history': [],
    'topic': '',
    'topic_category': '',
    'title': '',
    'article_file': '',
    'dedup_result': [],
    'cors_port': 0,
    'created_at': '',
    'updated_at': '',
    'errors': [],
}

def load_state():
    if STATE_FILE.exists():
        try:
            return read_json(STATE_FILE)
        except:
            log('state file corrupt, resetting', 'WARN')
    s = dict(DEFAULT_STATE)
    s['created_at'] = datetime.now().isoformat()
    return s

def save_state(state):
    state['updated_at'] = datetime.now().isoformat()
    write_json(STATE_FILE, state)
    log(f'state saved: {state["current_state"]}')

def current_step_idx(state):
    try:
        return STATE_NAMES.index(state['current_state'])
    except ValueError:
        return 0

# --- heartbeat ---

HEARTBEAT_FILE = WORKDIR / '_qq_heartbeat.txt'

def write_heartbeat(state_name):
    ts = datetime.now().isoformat()
    HEARTBEAT_FILE.write_text(f'{ts} {state_name}', 'utf-8')

# --- backup ---

def create_backup():
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = BACKUP_DIR / ts
    backup_path.mkdir(exist_ok=True)
    patterns = ['qq_article_*.txt', 'article_final.html', 'session_state.json', 'qq_topic_ledger.json']
    for pat in patterns:
        for p in WORKDIR.glob(pat):
            shutil.copy2(p, backup_path / p.name)
    log(f'backup created: {ts}')

def rotate_backups():
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

# --- topic ledger ---

TOPIC_LEDGER_FILE = WORKDIR / 'qq_topic_ledger.json'

DEFAULT_TOPIC_LEDGER = {
    'version': '1',
    'rotation_index': 0,
    'categories': [
        'game/battle',
        'game/rpg',
        'game/moba',
        'game/party',
        'emotion/family',
        'lifestyle/money',
        'history/figures',
    ],
    'history': [],
}

def load_topic_ledger():
    if TOPIC_LEDGER_FILE.exists():
        try:
            return read_json(TOPIC_LEDGER_FILE)
        except:
            log('topic ledger corrupt, resetting', 'WARN')
    s = dict(DEFAULT_TOPIC_LEDGER)
    save_topic_ledger(s)
    return s

def save_topic_ledger(ledger):
    write_json(TOPIC_LEDGER_FILE, ledger)


def step_auto_init(state):
    checks = [
        ('workdir', WORKDIR.exists()),
        ('skill dir', SKILLDIR.exists()),
        ('generate_image.py', (WORKDIR / 'generate_image.py').exists()),
    ]
    for name, ok in checks:
        if not ok:
            log(f'init check FAIL: {name}', 'ERROR')
            return False
    log('init checks passed')
    return True


def step_auto_write_verify(state):
    '''Verify article meets quality gate.'''
    qq_article = newest_file("qq_article_*.txt", WORKDIR)
    if qq_article is None:
        log('no article file found (qq_article_*.txt)', 'ERROR')
        return False
    text = qq_article.read_text(encoding="utf-8")
    cn = count_hanzi(text)
    if cn < QQ_PUBLISH_MIN_HANZI:
        log(f'article too short: {cn} hanzi < {QQ_PUBLISH_MIN_HANZI}', 'ERROR')
        return False
    state["article_file"] = str(qq_article.resolve())
    log(f'article ok: {qq_article.name} ({cn} hanzi)')
    return True




# --- CORS server ---

CORS_SERVER = TOOLS_DIR / 'cors_server.py'

def cors_paths():
    return WORKDIR / '_qq_cors_port.txt', WORKDIR / '_qq_cors_stop.txt'

def stop_cors_server(state):
    port_file, default_stop = cors_paths()
    if 'cors_stop_file' not in state and not port_file.is_file():
        return
    stop_file = Path(state.get('cors_stop_file', default_stop)).resolve()
    try:
        stop_file.relative_to(WORKDIR.resolve())
    except ValueError:
        log(f'ignore unsafe CORS stop path: {stop_file}', 'WARN')
        return
    stop_file.write_text('stop\n', encoding='utf-8')
    state['cors_stopped_at'] = datetime.now().isoformat()
    log('CORS stop signal written')

def step_auto_cors(state):
    if not CORS_SERVER.is_file():
        log(f'CORS helper missing: {CORS_SERVER}', 'ERROR')
        return False
    if state.get('cors_stop_file'):
        stop_cors_server(state)
        time.sleep(0.3)
    port_file, stop_file = cors_paths()
    port_file.unlink(missing_ok=True)
    stop_file.unlink(missing_ok=True)
    popen_kwargs = {
        'cwd': str(WORKDIR),
        'stdout': subprocess.DEVNULL,
        'stderr': subprocess.DEVNULL,
    }
    if os.name == "nt":
        popen_kwargs['creationflags'] = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
    else:
        popen_kwargs['start_new_session'] = True
    try:
        process = subprocess.Popen(
            [sys.executable, str(CORS_SERVER), "--root", str(WORKDIR),
             "--port-file", str(port_file), "--stop-file", str(stop_file)],
            **popen_kwargs,
        )
    except OSError as exc:
        log(f'CORS start exception: {exc}', 'ERROR')
        return False
    deadline = time.monotonic() + 5
    port = None
    while time.monotonic() < deadline:
        if port_file.is_file():
            try:
                port = int(port_file.read_text(encoding="utf-8").strip())
                break
            except ValueError:
                pass
        time.sleep(0.1)
    if port is None:
        log(f'CORS did not publish a port (pid={process.pid})', 'ERROR')
        stop_file.write_text('stop\n', encoding='utf-8')
        return False
    state['cors_port'] = port
    state['cors_pid'] = process.pid
    state['cors_stop_file'] = str(stop_file)
    try:
        with urlopen(f'http://127.0.0.1:{port}/cover.jpg', timeout=5) as response:
            healthy = response.status == 200
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        healthy = False
        log(f'CORS health check failed: {exc}', 'ERROR')
    if healthy:
        log(f'CORS running on {port} (pid={process.pid})')
        return True
    stop_file.write_text('stop\n', encoding='utf-8')
    log('CORS start FAIL', 'ERROR')
    return False

# --- auto step handlers (continued) ---

def step_auto_image_gen(state):
    '''Generate cover.jpg using generate_image.py.'''
    img = WORKDIR / "cover.jpg"
    if img.exists():
        img.unlink()
        log('removed old cover.jpg')
    scene_options = [
        'intense mobile gaming moment on smartphone screen',
        'close-up of hands gripping phone in the dark',
        'gaming setup with glowing keyboard and RGB lights',
        'two players facing off in a tense moment',
        'digital battlefield map with glowing markers',
        'a player lost in thought after a game',
        'neon-lit gaming room with trophies',
        'smartphone screen showing match results',
    ]
    style_options = [
        'anime style, cel shaded',
        'photorealistic, hyper-detailed',
        'cinematic, film grain, anamorphic',
    ]
    light_options = [
        'dramatic neon backlight, blue and purple',
        'soft ambient light from monitor glow',
        'harsh contrast, shadows and highlights',
        'warm golden hour light from window',
    ]
    mood_options = [
        'tense, competitive, high stakes atmosphere',
        'melancholic, reflective, quiet mood',
        'energetic, excited, vibrant vibe',
        'mysterious, suspenseful, player vs system',
    ]
    scene = random.choice(scene_options)
    style = random.choice(style_options)
    light = random.choice(light_options)
    mood = random.choice(mood_options)
    quality = '4K, highly detailed, masterpiece, sharp focus'
    prompt = ', '.join([scene, style, light, mood, quality])
    log(f'image prompt: {prompt[:80]}...')
    escaped_workdir = escape_path(WORKDIR)
    cmd = f"python {escaped_workdir}/generate_image.py \"{prompt}\" cover.jpg 1024x1024"
    rc, out, err = run(cmd, timeout=300)
    if rc != 0:
        log(f'image gen FAIL (rc={rc}): {out[:200]} {err[:200]}', 'ERROR')
        return False
    if not img.exists() or img.stat().st_size < 10000:
        log(f'cover.jpg missing or too small', 'ERROR')
        return False
    log(f'cover.jpg generated: {img.stat().st_size} bytes')
    return True

def step_auto_review(state):
    '''Post-publish review: update topic ledger.'''
    ledger = load_topic_ledger()
    title = state.get('title', '')
    if not title:
        log('review: no title, skip ledger update', 'WARN')
        return True
    entry = {
        'title': title,
        'topic_category': state.get('topic_category', ''),
        'date': datetime.now().strftime('%Y-%m-%d'),
        'article_file': state.get('article_file', ''),
    }
    ledger['history'].append(entry)
    ledger['rotation_index'] = (ledger.get('rotation_index', 0) + 1) % len(ledger['categories'])
    save_topic_ledger(ledger)
    log(f'review: topic ledger updated - "{title}" ({entry["topic_category"]})')
    return True

def step_auto_cleanup(state):
    stop_cors_server(state)
    patterns = ['_qq_cors_port.txt', '_qq_heartbeat.txt', 'cover.jpg']
    for pat in patterns:
        for f in WORKDIR.glob(pat):
            f.unlink(missing_ok=True)
    rotate_backups()
    log('cleanup done')
    return True

# --- state machine dispatch ---

AUTO_HANDLERS = {
    'init': step_auto_init,
    'write_verify': step_auto_write_verify,
    'image_gen': step_auto_image_gen,
    'cors': step_auto_cors,
    'review': step_auto_review,
    'cleanup': step_auto_cleanup,
}

def run_current_step(state):
    '''Execute the current step if AUTO type. Return True/BROWSER/False.'''
    name = state['current_state']
    idx = current_step_idx(state)
    if idx >= len(STATES_DEF):
        return False
    sdef = STATES_DEF[idx]
    cat = sdef[1]
    write_heartbeat(name)
    log(f'--- step [{idx}] {name} ({cat}) ---')
    if cat == "browser":
        log(f'browser step requires Claude: {sdef[2]}', 'INFO')
        return 'BROWSER'
    if cat == "terminal":
        log(f'terminal state: {name}', 'INFO')
        return True
    handler = AUTO_HANDLERS.get(name)
    if not handler:
        log(f'no auto handler for {name}', 'ERROR')
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
        if state["retry_count"] > max_retries:
            log(f'step {name} failed after {max_retries} retries', 'ERROR')
            state['current_state'] = 'error'
            state['errors'] = state.get('errors', []) + [f'{name}: max retries']
            save_state(state)
            return False
        log(f'step {name} failed (retry {state["retry_count"]}/{max_retries})', 'WARN')
        return False

def advance_state(state):
    idx = current_step_idx(state)
    sdef = STATES_DEF[idx]
    if sdef[4]:
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
    print(f'  Status: {state["current_state"]}')
    if sdef:
        print(f'  Type: {sdef[1]}')
        print(f'  Desc: {sdef[2]}')
        print(f'  Retry: {state["retry_count"]}/{sdef[3]}')
    print(f'  Recovery: {state["last_recovery"]}')
    print(f'  Topic: {state.get("topic", "")}')
    print(f'  Title: {state.get("title", "")}')
    print(f'  Updated: {state["updated_at"]}')
    log_date = datetime.now().strftime('%Y%m%d')
    print(f'  Log: logs/qq_publish_{log_date}.log')
    print(f'  Steps: {len(state.get("history", []))}')
    if state.get("errors"):
        print(f'  Last error: {state["errors"][-1]}')
    print('=' * 55)

def cli_dry_run(state):
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

def main():
    state = load_state()
    if len(sys.argv) < 2:
        cli_status(state)
        return
    cmd = sys.argv[1]
    if cmd == "--status":
        cli_status(state)
    elif cmd == "--step":
        ok = run_current_step(state)
        if not ok:
            idx = current_step_idx(state)
            if idx < len(STATES_DEF) and STATES_DEF[idx][1] == "browser":
                print(f'NEEDS_BROWSER:{state["current_state"]}')
                sys.exit(0)
            sys.exit(1)
    elif cmd == "--complete":
        advance_state(state)
        log(f'browser step completed, advanced to {state["current_state"]}')
    elif cmd == "--dry-run":
        cli_dry_run(state)
    elif cmd == "--init":
        topic = ' '.join(sys.argv[2:]) if len(sys.argv) > 2 else ''
        state = dict(DEFAULT_STATE)
        state['created_at'] = datetime.now().isoformat()
        state['topic'] = topic
        if not topic:
            ledger = load_topic_ledger()
            idx = ledger.get('rotation_index', 0)
            cats = ledger.get('categories', [])
            if cats:
                next_cat = cats[idx % len(cats)]
                state['topic_category'] = next_cat
                log(f'auto-selected category: {next_cat}')
            else:
                state['topic_category'] = 'game/battle'
                log('default category: game/battle')
        else:
            state['topic_category'] = ''
        save_state(state)
        log(f'state initialized (topic: {topic or "auto-selected"})')
    elif cmd == "--topic-ledger":
        ledger = load_topic_ledger()
        print(json.dumps(ledger, ensure_ascii=False, indent=2))
    elif cmd == "--topic-category":
        if len(sys.argv) < 3:
            print('usage: --topic-category <category>')
            sys.exit(1)
        state['topic_category'] = sys.argv[2]
        save_state(state)
        log(f'topic category set: {sys.argv[2]}')
    elif cmd == "--rollback":
        recovery = state.get('last_recovery', 'init')
        if recovery in STATE_NAMES:
            state['current_state'] = recovery
            state['retry_count'] = 0
            save_state(state)
            log(f'rolled back to {recovery}')
    elif cmd == "--reset":
        state = dict(DEFAULT_STATE)
        state['created_at'] = datetime.now().isoformat()
        save_state(state)
        log('state reset')
    elif cmd == "--abort":
        reason = ' '.join(sys.argv[2:]) if len(sys.argv) > 2 else 'manual abort'
        state['current_state'] = 'error'
        state['errors'] = state.get('errors', []) + [reason]
        save_state(state)
        log(f'aborted: {reason}', 'ERROR')
    else:
        print(f'unknown command: {cmd}')
        print("""
run_qq_publish.py - Q-zone publish state machine v1.0

Usage:
  python run_qq_publish.py --status
  python run_qq_publish.py --step
  python run_qq_publish.py --complete
  python run_qq_publish.py --dry-run
  python run_qq_publish.py --init TOPIC
  python run_qq_publish.py --rollback
  python run_qq_publish.py --reset
  python run_qq_publish.py --abort REASON
""")

if __name__ == "__main__":
    main()
