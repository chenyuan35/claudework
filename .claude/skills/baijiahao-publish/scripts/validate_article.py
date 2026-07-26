from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from article_contract import format_failures, validate_file


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate a Baijiahao article contract")
    parser.add_argument("article", type=Path)
    parser.add_argument("--title")
    parser.add_argument("--keyword", action="append")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = validate_file(args.article.resolve(), title=args.title, keywords=args.keyword)
    print(json.dumps(result.as_dict(), ensure_ascii=False, indent=2))
    if result.pass_gate:
        return 0
    print(f"BJH_ARTICLE_INVALID:{format_failures(result.failures)}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
