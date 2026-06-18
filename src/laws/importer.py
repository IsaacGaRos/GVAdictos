from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from src.core.db import connect, init_db


ARTICLE_RE = re.compile(
    "(?im)^\\s*(art(?:i|\\u00ed|\\u00c3\\u00ad)culo|article|art\\.)\\s+"
    "([0-9]+(?:\\s*[a-z])?(?:\\.[0-9]+)?)\\.?\\s*(.*)$"
)


@dataclass(frozen=True)
class ParsedArticle:
    article_ref: str
    title: str
    text: str


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_text_file(path: Path) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(errors="replace")


def _find_article_text(article_ref: str, start_pos: int, text: str, next_match_pos: int) -> str:
    """Try to recover article text if initial block is too short.

    Searches forward from start_pos for substantial text that belongs to this article.
    """
    # Look ahead up to 1000 chars or until next article match
    search_end = min(start_pos + 1000, next_match_pos, len(text))
    lookahead = text[start_pos:search_end]
    lines = lookahead.split('\n')

    # Skip first 1-2 lines (usually the article header), collect remaining text
    collected = []
    for i, line in enumerate(lines[1:], start=1):
        stripped = line.strip()
        # Stop if we hit another article marker or TOC-like pattern
        if ARTICLE_RE.match(stripped) or (len(stripped) < 80 and "." * 3 in stripped):
            break
        if stripped and len(stripped) > 10:
            collected.append(stripped)

    if collected:
        return '\n'.join(collected)
    return ""


def parse_articles(text: str) -> list[ParsedArticle]:
    matches = list(ARTICLE_RE.finditer(text))
    if not matches:
        cleaned = text.strip()
        return [ParsedArticle("sin_articulo_detectado", "Pendiente de clasificar", cleaned)] if cleaned else []

    articles: list[ParsedArticle] = []
    seen_refs = set()
    recovered_articles = []

    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        block = text[start:end].strip()
        article_ref = match.group(2).strip()
        title = match.group(3).strip() or f"Articulo {article_ref}"

        # Skip index/TOC lines: very short, mostly dots, or ending with page numbers
        if len(block) < 150 and ("." * 5 in block or re.match(r".*\d+\s*$", block)):
            continue

        # Skip duplicates
        if article_ref in seen_refs:
            continue

        # Check if block has meaningful text
        text_only = block.replace(title, "", 1).strip()
        if len(text_only) < 50:
            # Try to recover text from lookahead
            recovered = _find_article_text(article_ref, start, text, end)
            if recovered and len(recovered) >= 50:
                block = f"{title}\n{recovered}"
                text_only = recovered
                recovered_articles.append(article_ref)
            else:
                # Still no text, skip it
                continue

        seen_refs.add(article_ref)
        articles.append(ParsedArticle(article_ref=article_ref, title=title, text=block))

    # Log recovered articles
    if recovered_articles:
        import sys
        print(f"[Parser] Recovered {len(recovered_articles)} articles: {', '.join(recovered_articles[:5])}", file=sys.stderr)

    return articles


def import_law(path: Path, law_name: str | None = None, original_source_path: Path | None = None) -> int:
    init_db()
    source_path = original_source_path or path
    source_hash = file_sha256(source_path)
    text = read_text_file(path)
    articles = parse_articles(text)
    name = law_name or path.stem

    with connect() as conn:
        row = conn.execute(
            "SELECT id FROM laws WHERE name = ? AND source_hash = ?",
            (name, source_hash),
        ).fetchone()
        if not row:
            row = conn.execute(
                "SELECT id FROM laws WHERE name = ? AND source_path = ? ORDER BY id DESC LIMIT 1",
                (name, str(source_path)),
            ).fetchone()
        if row:
            law_id = int(row["id"])
            conn.execute(
                "UPDATE laws SET source_hash = ?, imported_at = CURRENT_TIMESTAMP WHERE id = ?",
                (source_hash, law_id),
            )
            conn.execute("DELETE FROM articles WHERE law_id = ?", (law_id,))
        else:
            cursor = conn.execute(
                "INSERT INTO laws(name, source_path, source_hash) VALUES (?, ?, ?)",
                (name, str(source_path), source_hash),
            )
            law_id = int(cursor.lastrowid)

        for article in articles:
            conn.execute(
                """
                INSERT INTO articles(
                    law_id, article_ref, title, text, source, original_hash
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (law_id, article.article_ref, article.title, article.text, str(source_path), source_hash),
            )
    return law_id
