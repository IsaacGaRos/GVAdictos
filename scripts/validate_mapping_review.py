from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mapping_tools import format_validation_summary, validate_review_template


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate a reviewed mapping CSV without writing to the database."
    )
    parser.add_argument("csv_path", type=Path)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    result = validate_review_template(args.csv_path)

    print("Validation:", format_validation_summary(result))
    for issue in result.issues:
        row = f"row {issue.row_number}" if issue.row_number else "global"
        print(f"[{issue.level}] {row} {issue.code}: {issue.message}")

    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
