from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mapping_tools import (
    REVIEW_COLUMNS,
    REVIEW_EXTRA_COLUMNS,
    connect_readonly,
    ensure_reports_dir,
    template_rows,
    write_csv,
)


def main() -> int:
    reports_dir = ensure_reports_dir()
    output = reports_dir / "mapping_review_template.csv"

    with connect_readonly() as conn:
        rows = template_rows(conn)

    fieldnames = [
        "topic_id",
        *REVIEW_COLUMNS[:7],
        "normative_reference",
        "candidate_article_count",
        "current_linked_article_ids",
        *REVIEW_COLUMNS[7:],
        "mapping_basis",
    ]
    # Keep the user-requested minimum columns and add technical helpers.
    fieldnames = [name for name in fieldnames if name in set(REVIEW_COLUMNS + REVIEW_EXTRA_COLUMNS)]
    write_csv(output, rows, fieldnames)

    print(f"Wrote {output}")
    print(f"Rows: {len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
