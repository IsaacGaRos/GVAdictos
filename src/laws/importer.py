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


def parse_articles(text: str) -> list[ParsedArticle]:
    matches = list(ARTICLE_RE.finditer(text))
    if not matches:
        cleaned = text.strip()
        return [ParsedArticle("sin_articulo_detectado", "Pendiente de clasificar", cleaned)] if cleaned else []

    articles: list[ParsedArticle] = []
    seen_refs = set()

    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        block = text[start:end].strip()
        article_ref = match.group(2).strip()
        title = match.group(3).strip() or f"Articulo {article_ref}"

        # Skip index/TOC lines: very short, mostly dots, or ending with page numbers
        if len(block) < 150 and ("." * 5 in block or re.match(r".*\d+\s*$", block)):
            continue

        # Skip duplicates (same article ref already seen)
        if article_ref in seen_refs:
            continue

        seen_refs.add(article_ref)
        articles.append(ParsedArticle(article_ref=article_ref, title=title, text=block))
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
