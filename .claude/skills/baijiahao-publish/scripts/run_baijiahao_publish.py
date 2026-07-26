from __future__ import annotations

import argparse
from dataclasses import dataclass, field
import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Any, Literal

SKILL_DIR = Path(__file__).resolve().parents[1]
RUNTIME_DIR = SKILL_DIR / "runtime"
STATE_FILE = RUNTIME_DIR / "pipeline_state.json"
TASK_FILE = RUNTIME_DIR / "_task.json"
MAX_FAILURES_PER_STAGE = 2
sys.path.insert(0, str(SKILL_DIR))
sys.path.insert(0, str(SKILL_DIR / "scripts"))

import article_contract  # noqa: E402
import generate_inject  # noqa: E402


@dataclass(frozen=True)
class Stage:
    name: str
    type: Literal["browser", "reasoning", "python"]
    expected_status: str  # 空字符串表示 python 自动阶段，不需外部验证
    operations: tuple[dict[str, Any], ...] = ()
    reasoning_prompt: str = ""


def script_operation(filename: str) -> dict[str, Any]:
    return {
        "tool": "mcp__playwright__browser_evaluate",
        "sourceFile": str((SKILL_DIR / "scripts" / filename).resolve()),
        "instruction": "读取 sourceFile 全文，将其作为 browser_evaluate 的 function 参数执行",
    }


def stages(inject_file: Path, title: str) -> list[Stage]:
    """返回完整管道阶段列表。browser 阶段用 inject_file 和 title 构建操作。"""
    inject_path = str(inject_file.resolve())
    return [
        # ── 运营前段：首次发布必经，--start 传入 article+title 时跳过 ──
        Stage(
            "check_dashboard", "reasoning", "dashboard_read",
            reasoning_prompt=(
                "打开百家号数据中心，检查最近 7 天已发布文章的阅读量、推荐量、评论数等表现数据。\n"
                "使用 browser_navigate 进入数据中心页面，再 browser_snapshot 或 evaluate 提取数据。\n"
                "输出结构化结果，包含每篇文章的关键指标和整体趋势判断。"
            ),
        ),
        Stage(
            "find_trending", "reasoning", "trending_found",
            reasoning_prompt=(
                "搜索当前生活/健康/居家/省钱领域的热点话题。\n"
                "使用 WebSearch 或 Tavily 搜索，也可以浏览器访问百度热点热搜页面。\n"
                "找到 5-8 个可能与家庭生活、健康误区、省钱技巧等相关的热点方向。"
            ),
        ),
        Stage(
            "select_topic", "reasoning", "topic_selected",
            reasoning_prompt=(
                "基于以下信息选择下篇百家号文章主题：\n"
                "1. 数据中心表现数据（近期哪类文章数据好、哪类差）\n"
                "2. 当前热点趋势方向\n"
                "3. 结构轮换规则：排除最近 2 篇已用结构，按清单体 > 实验报告 > 踩坑叙事优先\n"
                "4. 领域切换规则：连续 3 篇同领域后必须切换\n"
                "5. 标题公式：首选警告清单式，次选恐惧+指南；20-26 汉字最佳\n"
                "输出选题决策，包含：标题、结构类型、领域、1-2 个关键词"
            ),
        ),
        Stage(
            "write_article", "reasoning", "article_written",
            reasoning_prompt=(
                "写一篇百家号文章 HTML，严格遵循以下 HTML 契约：\n"
                '- 4 个 p[data-bjh-role="intro"]\n'
                "- 6 节，每节 1 个 p[data-bjh-role=section-title][data-bjh-section=N]"
                " + 7 个 p[data-bjh-role=section-body][data-bjh-section=N]\n"
                '- 3 个 p[data-bjh-role="outro"]\n'
                "- 正文段每段 40-80 汉字，含我/我家视角\n"
                "- 全文至少一处对话，至少一个阿拉伯数字\n"
                '- 无权威口吻（你应该/你必须/你一定/建议你）\n'
                "- 无评论区/留言区引导\n"
                "- 全文 >= 2000 汉字\n"
                "输出时先写完整 HTML 到 runtime/article.html 文件（用 Write 工具），\n"
                "再返回包含 status、title、keywords（列表）、articleFile 的结构化结果。"
            ),
        ),
        # ── Python 自动阶段：入口自执行，不需外部交互 ──
        Stage("validate_article", "python", ""),
        Stage("generate_inject", "python", ""),
        # ── 浏览器发布阶段 ──
        Stage(
            "prepare_home", "browser", "home_ready",
            operations=(
                {"tool": "mcp__playwright__browser_navigate", "url": "https://baijiahao.baidu.com"},
                script_operation("prepare_home.js"),
            ),
        ),
        Stage(
            "open_editor", "browser", "editor_ready",
            operations=(
                {"tool": "mcp__playwright__browser_click", "target": "text=发布作品"},
                script_operation("open_editor_ready.js"),
            ),
        ),
        Stage(
            "inject_content", "browser", "content_gate_passed",
            operations=(
                {"tool": "mcp__playwright__browser_click", "target": '[data-bjh-title="true"]'},
                {"tool": "mcp__playwright__browser_type", "target": '[data-bjh-title="true"]', "text": title},
                {
                    "tool": "mcp__playwright__browser_evaluate",
                    "function": "() => { const e=window.UE_V2?.instants?.ueditorInstant0; "
                    "if(!e) throw new Error('BJH_EDITOR_NOT_READY'); e.setContent(''); "
                    "return {status:'editor_cleared'}; }",
                },
                {
                    "tool": "mcp__playwright__browser_evaluate",
                    "sourceFile": inject_path,
                    "instruction": "读取 sourceFile 全文，将其作为 browser_evaluate 的 function 参数执行",
                },
                {
                    "tool": "mcp__playwright__browser_evaluate",
                    "function": "() => { sessionStorage.setItem('bjh_gate_stage','content'); "
                    "return {status:'content_stage_set'}; }",
                },
                script_operation("check_article_gate.js"),
            ),
        ),
        Stage(
            "insert_images", "browser", "images_complete",
            operations=(script_operation("insert_ai_images.js"),),
        ),
        Stage(
            "set_cover", "browser", "cover_complete",
            operations=(
                {"tool": "mcp__playwright__browser_click", "target": "text=选择封面"},
                {"tool": "mcp__playwright__browser_click", "target": "text=AI封图"},
                script_operation("set_cover.js"),
            ),
        ),
        Stage(
            "publish_gate", "browser", "publish_gate_passed",
            operations=(
                {"tool": "mcp__playwright__browser_click",
                 "target": "label:has(.aigc_bjh_status) .cheetah-checkbox"},
                {
                    "tool": "mcp__playwright__browser_evaluate",
                    "function": "() => { sessionStorage.setItem('bjh_gate_stage','publish'); "
                    "return {status:'publish_stage_set'}; }",
                },
                script_operation("check_article_gate.js"),
            ),
        ),
        Stage(
            "schedule_publish", "browser", "scheduled",
            operations=(script_operation("publish_timing.js"),),
        ),
        Stage(
            "verify_submission", "browser", "submission_verified",
            operations=(script_operation("verify_submission.js"),),
        ),
    ]


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _run_python_stage(stage: Stage, state: dict[str, Any]) -> dict[str, Any]:
    """在 emit_task 内自动执行 Python 阶段，不经过外部 --complete。"""
    article_str = state.get("article", "")
    if not article_str:
        raise RuntimeError(f"BJH_PYTHON_STAGE_FAILED:{stage.name}:article_not_set")
    article_path = Path(article_str)
    if not article_path.exists():
        raise RuntimeError(f"BJH_PYTHON_STAGE_FAILED:{stage.name}:article_not_found:{article_str}")
    title = state.get("title", "")
    keywords = state.get("keywords", [])

    if stage.name == "validate_article":
        result = article_contract.validate_file(article_path, title=title, keywords=keywords)
        if not result.pass_gate:
            detail = article_contract.format_failures(result.failures)
            raise RuntimeError(f"BJH_ARTICLE_INVALID:{detail}")
        # 验证通过后更新文章哈希（可能经人工修正过）
        state["articleSha256"] = hashlib.sha256(article_path.read_bytes()).hexdigest()
        return {"status": "article_valid", "pass": True, "metrics": result.metrics}

    if stage.name == "generate_inject":
        inject_file = Path(state.get("injectFile", str(RUNTIME_DIR / "inject.js")))
        output = generate_inject.generate(article_path, inject_file, title=title, keywords=keywords)
        state["injectFile"] = str(inject_file.resolve())
        # 如果 write_article 未写入 articleSha256，此处补充
        if not state.get("articleSha256"):
            state["articleSha256"] = hashlib.sha256(article_path.read_bytes()).hexdigest()
        return {"status": "inject_ready", "articleSha256": state.get("articleSha256", "")}

    raise RuntimeError(f"BJH_UNKNOWN_PYTHON_STAGE:{stage.name}")


def _build_browser_task(stage: Stage, state: dict[str, Any]) -> dict[str, Any]:
    """生成带令牌和下个操作的浏览器任务。"""
    task_token = os.urandom(16).hex()
    nonce = {
        "tool": "mcp__playwright__browser_evaluate",
        "function": f"() => {{ sessionStorage.setItem('bjh_task_token','{task_token}'); "
        f"return {{taskToken:'{task_token}'}}; }}",
        "instruction": "将指定的 task_token 写入 sessionStorage",
    }
    verify = {
        "tool": "mcp__playwright__browser_evaluate",
        "function": "() => { const t=sessionStorage.getItem('bjh_task_token')||''; "
        "sessionStorage.removeItem('bjh_task_token'); return {taskToken:t}; }",
        "instruction": "读取并清除 sessionStorage 中的 bjh_task_token",
    }
    ops: list[dict[str, Any]] = []
    for op in stage.operations:
        if op.get("tool") == "mcp__playwright__browser_evaluate" and op.get("sourceFile"):
            ops.append(nonce)
            ops.append(op)
            ops.append(verify)
        else:
            ops.append(op)
    return {
        "type": "browser",
        "pipeline": "baijiahao-publish",
        "stage": stage.name,
        "expectedStatus": stage.expected_status,
        "taskToken": task_token,
        "operations": ops,
        "rules": [
            "只使用列出的 mcp__playwright__browser_* 工具",
            "按 operations 顺序执行，不插入未列出的浏览器操作",
            "任一操作失败立即停止，并把真实错误作为阶段结果",
            "成功后保存最后一个操作的结构化返回值，再调用统一入口 --complete",
        ],
    }


def _build_reasoning_task(stage: Stage, context: dict[str, Any]) -> dict[str, Any]:
    """生成推理阶段任务——Claude 使用搜索/浏览器/推理工具完成。"""
    task_token = os.urandom(16).hex()
    return {
        "type": "reasoning",
        "pipeline": "baijiahao-publish",
        "stage": stage.name,
        "expectedStatus": stage.expected_status,
        "taskToken": task_token,
        "prompt": stage.reasoning_prompt,
        "context": context,
        "rules": [
            "按 prompt 使用可用工具完成分析，然后以结构化 JSON 结果调用 --complete",
            "如果 prompt 要求写入文件，请先写文件再返回结果",
            "任一工具失败停止当前任务，使用 --fail 报告",
        ],
    }


def emit_task(state: dict[str, Any]) -> dict[str, Any]:
    """
    从当前 stageIndex 开始推进管道：
    - python 阶段：自动执行并前进
    - browser/reasoning 阶段：发出 _task.json 并返回
    - 全部完成：标记 completed
    """
    pipeline = stages(
        Path(state.get("injectFile", str(RUNTIME_DIR / "inject.js"))),
        state.get("title", ""),
    )
    while True:
        index = state["stageIndex"]
        if index >= len(pipeline):
            state["status"] = "completed"
            state["stage"] = ""
            atomic_write_json(STATE_FILE, state)
            TASK_FILE.unlink(missing_ok=True)
            return {"status": "completed", "stateFile": str(STATE_FILE)}

        stage = pipeline[index]

        # Python 阶段自动执行
        if stage.type == "python":
            try:
                result = _run_python_stage(stage, state)
            except RuntimeError as exc:
                state["status"] = "failed"
                state["error"] = str(exc)
                atomic_write_json(STATE_FILE, state)
                return {"status": "failed", "stage": stage.name, "error": str(exc)}
            state.setdefault("results", {})[stage.name] = result
            state["stageIndex"] = index + 1
            continue  # 继续下一个阶段

        # 构造推理或浏览器上下文
        context: dict[str, Any] = {
            "results": {
                k: v for k, v in state.get("results", {}).items()
                if k in {"check_dashboard", "find_trending", "select_topic", "write_article"}
            },
            "title": state.get("title", ""),
            "keywords": state.get("keywords", []),
        }

        if stage.type == "reasoning":
            task = _build_reasoning_task(stage, context)
        elif stage.type == "browser":
            task = _build_browser_task(stage, state)
        else:
            raise RuntimeError(f"BJH_UNKNOWN_STAGE_TYPE:{stage.type}")

        atomic_write_json(TASK_FILE, task)
        state["status"] = "waiting_external"
        state["stage"] = stage.name
        atomic_write_json(STATE_FILE, state)
        return {
            "status": "waiting_external",
            "type": stage.type,
            "stage": stage.name,
            "taskFile": str(TASK_FILE),
        }


def start(article: Path | None, title: str | None, keywords: list[str] | None = None,
          restart: bool = False) -> dict[str, Any]:
    """
    启动管道：
    - restart=True（--start/--restart）：删除旧状态从头开始
    - restart=False（--resume）：从当前阶段恢复（如果状态存在）
    """
    if STATE_FILE.exists() and not restart:
        existing = read_json(STATE_FILE)
        if existing.get("status") in {"waiting_external", "prepared", "failed"}:
            # 恢复：从当前阶段重新发射任务
            return emit_task(existing)
    elif restart:
        STATE_FILE.unlink(missing_ok=True)
        TASK_FILE.unlink(missing_ok=True)

    state: dict[str, Any] = {
        "pipelineVersion": 2,
        "status": "prepared",
        "stageIndex": 0,
        "stage": "",
        "article": "",
        "articleSha256": "",
        "injectFile": str((RUNTIME_DIR / "inject.js").resolve()),
        "title": "",
        "keywords": keywords or [],
        "results": {},
        "failures": {},
    }

    if article and title:
        # 跳过 reasoning 阶段（stageIndex 0-3），从 validate_article（stageIndex 4）开始
        article = article.resolve()
        if not article.exists():
            raise RuntimeError(f"BJH_ARTICLE_NOT_FOUND:{article}")
        state["article"] = str(article)
        state["articleSha256"] = hashlib.sha256(article.read_bytes()).hexdigest()
        state["title"] = title
        state["stageIndex"] = 4  # validate_article

    atomic_write_json(STATE_FILE, state)
    return emit_task(state)


def normalize_result(
    stage_name: str,
    expected_status: str,
    result: dict[str, Any],
    expected_token: str | None = None,
) -> dict[str, Any]:
    """校验阶段结果的 status/pass/taskToken。"""
    if expected_token:
        actual = result.get("taskToken", "")
        if actual != expected_token:
            raise RuntimeError(
                f"BJH_STAGE_FAILED:{stage_name}:taskToken_mismatch"
                f":expected={expected_token[:16]}...:actual={actual[:16]}..."
            )
    # 内容门/发布门检查 pass 字段
    if stage_name in {"inject_content", "publish_gate"}:
        if result.get("pass") is not True:
            raise RuntimeError(f"BJH_STAGE_FAILED:{stage_name}:gate_not_passed")
        normalized = dict(result)
        normalized["status"] = expected_status
        return normalized
    # 其他阶段检查 status 字段
    if result.get("status") != expected_status:
        raise RuntimeError(
            f"BJH_STAGE_FAILED:{stage_name}:status={result.get('status')}:expected={expected_status}"
        )
    result.pop("taskToken", None)
    return result


def complete(stage_name: str, result_file: Path) -> dict[str, Any]:
    """完成当前阶段，写入结果并推进到下一阶段。"""
    if not STATE_FILE.exists():
        raise RuntimeError("BJH_PIPELINE_NOT_STARTED")
    if not TASK_FILE.exists():
        raise RuntimeError("BJH_TASK_FILE_MISSING")
    state = read_json(STATE_FILE)
    pipeline = stages(
        Path(state.get("injectFile", str(RUNTIME_DIR / "inject.js"))),
        state.get("title", ""),
    )
    index = state["stageIndex"]
    if index >= len(pipeline):
        raise RuntimeError("BJH_PIPELINE_ALREADY_COMPLETED")
    stage = pipeline[index]
    if stage.name != stage_name:
        raise RuntimeError(
            f"BJH_STAGE_ORDER_ERROR:current={stage.name}:received={stage_name}"
        )

    # 校验文章未被篡改（仅当 article 已设置时）
    article_str = state.get("article", "")
    if article_str:
        expected_sha = state.get("articleSha256", "")
        current_sha = hashlib.sha256(Path(article_str).read_bytes()).hexdigest()
        if current_sha != expected_sha:
            raise RuntimeError("BJH_ARTICLE_CHANGED_AFTER_START")

    task = read_json(TASK_FILE)
    expected_token = task.get("taskToken")
    raw_result = read_json(result_file.resolve())
    result = normalize_result(stage.name, stage.expected_status, raw_result, expected_token)

    # 推理阶段结果可能带回 title / keywords / articleFile
    if stage.name == "select_topic":
        if result.get("title"):
            state["title"] = result["title"]
        if result.get("keywords"):
            state["keywords"] = result["keywords"]
    if stage.name == "write_article":
        if result.get("title"):
            state["title"] = result["title"]
        if result.get("keywords"):
            state["keywords"] = result["keywords"]
        article_file = result.get("articleFile", "")
        if article_file:
            ap = Path(article_file)
            if not ap.is_absolute():
                ap = RUNTIME_DIR / ap.name  # articleFile is relative to runtime/
            if ap.exists():
                state["article"] = str(ap.resolve())
                state["articleSha256"] = hashlib.sha256(ap.read_bytes()).hexdigest()

    state.setdefault("results", {})[stage.name] = result
    state["stageIndex"] = index + 1
    state["failures"].pop(stage_name, None)
    return emit_task(state)


def fail(stage_name: str, error: str) -> dict[str, Any]:
    """记录阶段失败，达到上限则硬熔断。"""
    if not STATE_FILE.exists():
        raise RuntimeError("BJH_PIPELINE_NOT_STARTED")
    state = read_json(STATE_FILE)
    if state.get("stage") != stage_name:
        raise RuntimeError(
            f"BJH_STAGE_ORDER_ERROR:current={state.get('stage')}:received={stage_name}"
        )
    failures = state.setdefault("failures", {})
    count = failures.get(stage_name, 0) + 1
    failures[stage_name] = count
    if count >= MAX_FAILURES_PER_STAGE:
        state["status"] = "hard_failed"
        state["error"] = f"BJH_MAX_RETRIES:{stage_name}:{count}"
        atomic_write_json(STATE_FILE, state)
        TASK_FILE.unlink(missing_ok=True)
        return {
            "status": "hard_failed",
            "stage": stage_name,
            "error": state["error"],
            "attempts": count,
        }
    state["status"] = "failed"
    state["error"] = error
    state["failures"] = failures
    atomic_write_json(STATE_FILE, state)
    TASK_FILE.unlink(missing_ok=True)
    return {
        "status": "failed",
        "stage": stage_name,
        "error": error,
        "attempts": count,
        "remaining_retries": MAX_FAILURES_PER_STAGE - count,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Baijiahao modular publishing pipeline")
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument(
        "--start", action="store_true",
        help="全新的管道，删除旧状态从头开始",
    )
    action.add_argument(
        "--resume", action="store_true",
        help="恢复上次中断的管道，保留旧状态继续",
    )
    action.add_argument("--restart", action="store_true", help="同 --start（兼容旧调用）")
    action.add_argument("--complete", action="store_true", help="完成当前阶段")
    action.add_argument("--fail", action="store_true", help="报告当前阶段失败")
    action.add_argument("--status", action="store_true", help="查看管道当前状态")
    parser.add_argument("--article", type=Path, help="已写好的文章 HTML 文件路径（与 --start/--restart 配合）")
    parser.add_argument("--title", help="文章标题（与 --article 配合）")
    parser.add_argument("--keyword", action="append", default=[], help="标题关键词（可重复）")
    parser.add_argument("--stage", help="--complete / --fail 的阶段名称")
    parser.add_argument("--result", type=Path, help="--complete 的阶段结果 JSON 文件")
    parser.add_argument("--error", help="--fail 的错误描述")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.start or args.restart:
            output = start(args.article, args.title, args.keyword, restart=True)
        elif args.resume:
            output = start(args.article, args.title, args.keyword, restart=False)
        elif args.complete:
            if not args.stage or not args.result:
                raise RuntimeError("--complete requires --stage and --result")
            output = complete(args.stage, args.result)
        elif args.fail:
            if not args.stage or not args.error:
                raise RuntimeError("--fail requires --stage and --error")
            output = fail(args.stage, args.error)
        else:
            output = read_json(STATE_FILE) if STATE_FILE.exists() else {"status": "not_started"}
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as error:
        print(str(error), file=sys.stderr)
        return 1
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
