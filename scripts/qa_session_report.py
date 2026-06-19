from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = ROOT / "reports"


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def split_multi(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        for part in value.split(";"):
            cleaned = part.strip()
            if cleaned:
                result.append(cleaned)
    return result


def yes_no_unknown(value: str) -> str:
    normalized = value.strip().lower()
    if normalized in {"yes", "y", "si", "s", "true", "1"}:
        return "yes"
    if normalized in {"no", "n", "false", "0"}:
        return "no"
    return "unknown"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create a manual QA/browser session report without touching the database."
    )
    parser.add_argument("--topic", default="", help="Topic reviewed, e.g. especial 18")
    parser.add_argument("--law", default="", help="Law/norma reviewed")
    parser.add_argument("--articles", action="append", default=[], help="Article refs/ids, repeat or separate by ;")
    parser.add_argument("--fallback", default="unknown", help="yes/no/unknown")
    parser.add_argument("--fine-mapping", default="unknown", help="yes/no/unknown")
    parser.add_argument("--visual-result", default="pending", help="pass/fail/pending/notes")
    parser.add_argument("--error", action="append", default=[], help="Error observed, repeatable")
    parser.add_argument("--capture", action="append", default=[], help="Screenshot/artifact path or URL, repeatable")
    parser.add_argument("--log", action="append", default=[], help="Log path or URL, repeatable")
    parser.add_argument("--notes", default="", help="Free-form notes")
    parser.add_argument("--reviewer", default="Claude/Codex", help="Reviewer label")
    return parser


def render_markdown(payload: dict[str, object]) -> str:
    articles = payload["articles_visualized"] or ["pendiente"]
    errors = payload["errors"] or ["none"]
    captures = payload["captures"] or ["none"]
    logs = payload["logs"] or ["none"]
    lines = [
        "# QA session report",
        "",
        f"- Generated at: {payload['generated_at']}",
        f"- Reviewer: {payload['reviewer']}",
        f"- Topic reviewed: {payload['topic_reviewed'] or 'pendiente'}",
        f"- Law reviewed: {payload['law_reviewed'] or 'pendiente'}",
        f"- Had fallback: {payload['had_fallback']}",
        f"- Had fine mapping: {payload['had_fine_mapping']}",
        f"- Visual result: {payload['visual_result']}",
        "",
        "## Articles visualized",
        "",
        *[f"- {article}" for article in articles],
        "",
        "## Errors",
        "",
        *[f"- {error}" for error in errors],
        "",
        "## Captures",
        "",
        *[f"- {capture}" for capture in captures],
        "",
        "## Logs",
        "",
        *[f"- {log}" for log in logs],
        "",
        "## Notes",
        "",
        str(payload["notes"] or "pendiente"),
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    args = build_parser().parse_args()
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": now_iso(),
        "reviewer": args.reviewer,
        "topic_reviewed": args.topic,
        "law_reviewed": args.law,
        "articles_visualized": split_multi(args.articles),
        "had_fallback": yes_no_unknown(args.fallback),
        "had_fine_mapping": yes_no_unknown(args.fine_mapping),
        "visual_result": args.visual_result,
        "errors": split_multi(args.error),
        "captures": split_multi(args.capture),
        "logs": split_multi(args.log),
        "notes": args.notes,
    }
    json_path = REPORTS_DIR / "qa_session_report.json"
    md_path = REPORTS_DIR / "qa_session_report.md"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_markdown(payload), encoding="utf-8")
    print(f"Wrote {md_path}")
    print(f"Wrote {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
