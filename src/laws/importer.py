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

# Detect boundaries where articles end (dispositions, annexes, etc.)
SECTION_BOUNDARY_RE = re.compile(
    r"(?im)^(disposici[óo]n\s+(adicional|transitoria|final|común)|"
    r"anexo\s+[ivxlc\dáéíóúñ]+|"
    r"^derogaci[óo]n\s+de\s+normas)",
    re.MULTILINE
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
    # For PDFs, try to extract text using available tools
    if path.suffix.lower() == '.pdf':
        # Try pdfplumber first
        try:
            import pdfplumber
            with pdfplumber.open(path) as pdf:
                text = '\n'.join([page.extract_text() or '' for page in pdf.pages])
                if text.strip():
                    return text
        except ImportError:
            pass
        except Exception:
            pass

        # Try pypdf as fallback
        try:
            from pypdf import PdfReader
            reader = PdfReader(path)
            text = '\n'.join([page.extract_text() or '' for page in reader.pages])
            if text.strip():
                return text
        except ImportError:
            pass
        except Exception:
            pass

        # Last resort: try pdfminer (via subprocess)
        try:
            import subprocess
            result = subprocess.run(
                ['pdftotext', str(path), '-'],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout
        except Exception:
            pass

    # For regular text files, use standard approach
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(errors="replace")


def _find_articles_end(text: str) -> int:
    """Find where regular articles end (before dispositions/annexes).

    Skip past indices and tables of contents by requiring actual content context.
    """
    # Find all matches of section boundaries
    matches = list(SECTION_BOUNDARY_RE.finditer(text))
    if not matches:
        return len(text)

    # The valid section boundary is usually after "Artículo 1" has appeared
    # and is the last substantial boundary before the document end
    # Most laws have a pattern where articles start ~page 6+, dispositions much later
    # Skip matches that are too early (likely in index)
    for match in matches:
        # Check context: after a match, look for "Disposición adicional primera" pattern
        context_start = match.start()
        context_end = min(match.start() + 200, len(text))
        context = text[context_start:context_end]

        # A real disposition section usually has full number/name after it
        if re.search(r'disposici[óo]n\s+(adicional\s+(primera|segunda|tercera|única)|transitoria|final)',
                     context, re.IGNORECASE):
            return match.start()

    # If no clear boundary found, use the last match as fallback
    return matches[-1].start() if matches else len(text)


def _clean_article_text(text: str, max_length: int = 8000) -> str:
    """Clean contaminated article text by removing appended dispositions/amendments.

    If article contains disposition/annexo markers, cut at that point.
    """
    if len(text) > max_length:
        # Look for contamination markers within the text
        lines = text.split('\n')
        for i, line in enumerate(lines):
            if re.search(r'(?i)disposici[óo]n\s+(adicional|transitoria)', line):
                # Cut at this point - probably appended content
                return '\n'.join(lines[:i]).strip()
            # Also cut if we hit a section header that shouldn't be in an article
            if re.match(r'(?i)^(ANEXO|TITULO|LIBRO|CAPITULO|SECCION)\s+', line.strip()):
                return '\n'.join(lines[:i]).strip()

        # If still too long, try to find natural breaks
        if len(text) > max_length:
            # Cut at roughly max_length but at a line boundary
            lines = text.split('\n')
            accumulated = ''
            for line in lines:
                if len(accumulated) + len(line) > max_length:
                    break
                accumulated += line + '\n'
            return accumulated.strip() if accumulated else text[:max_length]

    return text.strip()


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
    # Find where regular articles end (before dispositions/annexes)
    articles_end = _find_articles_end(text)
    text_articles_only = text[:articles_end]

    matches = list(ARTICLE_RE.finditer(text_articles_only))
    if not matches:
        return []  # Return empty list if no articles found

    articles: list[ParsedArticle] = []
    seen_refs = set()
    recovered_articles = []

    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text_articles_only)
        block = text_articles_only[start:end].strip()
        article_ref = match.group(2).strip()
        title = match.group(3).strip() or f"Articulo {article_ref}"

        # Skip index/TOC lines: very short, mostly dots, or ending with page numbers
        if len(block) < 150 and ("." * 5 in block or re.match(r".*\d+\s*$", block)):
            continue

        # Skip duplicates
        if article_ref in seen_refs:
            continue

        # Clean contaminated text (remove appended dispositions)
        block = _clean_article_text(block)

        # Check if block has meaningful text
        text_only = block.replace(title, "", 1).strip()
        if len(text_only) < 50:
            # Try to recover text from lookahead
            recovered = _find_article_text(article_ref, start, text_articles_only, end)
            if recovered and len(recovered) >= 50:
                block = f"{title}\n{recovered}"
                text_only = recovered
                recovered_articles.append(article_ref)
            else:
                # Still no text, skip it
                continue

        seen_refs.add(article_ref)
        articles.append(ParsedArticle(article_ref=article_ref, title=title, text=block))

    # Log recovered/cleaned articles
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
