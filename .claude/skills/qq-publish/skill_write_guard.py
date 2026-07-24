#!/usr/bin/env python3
"""
skill_write_guard.py — SKILL.md 覆盖保护门（§-1 的实现）

用法：
  python skill_write_guard.py SKILL.md SKILL.new.md

校验：
  1. 行数硬闸：新文件 >= max(旧文件-50, 旧文件*0.95)
  2. 代码围栏成对：``` 数量为偶数
  3. YAML 头完整：以 --- 开头，200字符内有第二个 ---
  4. 关键章节全部存在

通过后：
  1. 备份旧文件为 SKILL.md.bak-YYYYMMDD-HHMMSS
  2. 原子替换新文件到旧路径
  3. 打印 JSON 结果
"""

import sys, shutil, datetime, re
from pathlib import Path

def validate(old_path_str, new_path_str):
    old_path = Path(old_path_str).resolve()
    new_path = Path(new_path_str).resolve()

    if not old_path.exists():
        raise SystemExit("REFUSE WRITE: 旧文件不存在")
    if not new_path.exists():
        raise SystemExit("REFUSE WRITE: 新文件不存在")

    old = old_path.read_text(encoding="utf-8")
    new = new_path.read_text(encoding="utf-8")
    old_lines = old.splitlines()
    new_lines = new.splitlines()

    required = [
        "## §0", "## PHASE 0", "## PHASE 1", "## PHASE 2：",
        "## PHASE 2.5", "## PHASE 3", "## PHASE 4", "## §5", "## §6", "## §7"
    ]
    errors = []

    # 行数硬闸
    min_lines = max(int(len(old_lines) * 0.95), len(old_lines) - 50)
    if len(new_lines) < min_lines:
        errors.append(f"破坏性缩短：{len(old_lines)} -> {len(new_lines)}行（需 >= {min_lines}）")

    # 代码围栏
    fence_count = new.count("```")
    if fence_count % 2:
        errors.append(f"Markdown 代码围栏未闭合（{fence_count} 个 ```）")

    # YAML 头
    stripped_new = new.lstrip()
    if not stripped_new.startswith("---"):
        errors.append("YAML 头不完整：不以 --- 开头")
    else:
        # 查找第二个 ---
        second = stripped_new.find("---", 3)
        if second < 0 or second > 500:
            errors.append("YAML 头不完整：未找到结尾 ---")

    # 关键章节
    for heading in required:
        if heading not in new:
            errors.append("缺少关键章节：" + heading)

    if errors:
        raise SystemExit("REFUSE WRITE\n" + "\n".join(errors))

    return old, old_lines, new, new_lines


def main():
    if len(sys.argv) < 3:
        print("用法：python skill_write_guard.py <旧文件> <新文件>")
        sys.exit(1)

    old_path = sys.argv[1]
    new_path = sys.argv[2]

    old, old_lines, new, new_lines = validate(old_path, new_path)

    # 备份
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = Path(old_path).with_name(Path(old_path).name + ".bak-" + ts)
    shutil.copy2(old_path, backup_path)

    # 原子替换
    shutil.copy2(new_path, old_path)

    result = {
        "PASS": True,
        "oldLines": len(old_lines),
        "newLines": len(new_lines),
        "diff": len(new_lines) - len(old_lines),
        "backup": str(backup_path)
    }
    print(result)
    sys.exit(0)


if __name__ == "__main__":
    main()
