"""Limpia el texto extraído de los PDFs CEF del watermark, pies de página
y referencias a la academia, y lo guarda en topic_study_resources.

Uso:
    python scripts/clean_cef_competencias_text.py [--preview topic_number]
"""
from __future__ import annotations

import re
import sys
import sqlite3
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "db" / "gvadicto.sqlite"


# ── Patrones a eliminar completamente (líneas) ────────────────────────────────

# Artefactos del watermark vertical del PDF (1-4 chars en minúscula + @)
_STRAY_CHAR = re.compile(r'^[a-z @]{1,5}$')

# Pies de página CEF
_FOOTER_CEF = re.compile(
    r'www\.cef\.es|cef\.\-|Centro de Estudios Financieros|FEBRERO 20\d\d|'
    r'Tema \d+ - \d+$|TEMA \d+ - \d+$',
    re.IGNORECASE
)

# Bloque de copyright / derechos reservados
_COPYRIGHT = re.compile(
    r'derechos reservados|propiedad intelectual|prohibida su|'
    r'reproducci[oó]n.*distribuci[oó]n|cesi[oó]n de los derechos|'
    r'Centro de Estudios Financieros|queda prohibida',
    re.IGNORECASE
)

# Cabecera del archivo
_FILE_HEADER = re.compile(
    r'^Oposiciones Competencias de la Generalitat$|'
    r'^NOTA IMPORTANTE:.*academia|^NOTA IMPORTANTE.*CEF',
    re.IGNORECASE
)

# Línea de solo URL o path
_URL_LINE = re.compile(r'^\s*https?://\S+\s*$|^\s*www\.\S+\s*$')


def _is_artifact_line(line: str) -> bool:
    """True si la línea es un artefacto del PDF (watermark, footer, etc.)."""
    s = line.strip()
    if not s:
        return False
    if _STRAY_CHAR.match(s):
        return True
    if _FOOTER_CEF.search(s):
        return True
    if _COPYRIGHT.search(s):
        return True
    if _URL_LINE.match(s):
        return True
    return False


def _is_nota_importante_block(lines: list[str], i: int) -> bool:
    """True si la línea i inicia un bloque NOTA IMPORTANTE que refiere al CEF/academia."""
    return bool(re.match(r'^NOTA IMPORTANTE', lines[i].strip(), re.IGNORECASE))


def clean_cef_text(raw: str) -> str:
    """
    Limpia el texto crudo extraído por pdfplumber de los PDFs CEF.

    Elimina:
    - Artefactos del watermark vertical (letras sueltas)
    - Pies de página (www.cef.es, FEBRERO 2026, Tema N - P)
    - Bloques de copyright
    - Cabeceras del fichero ("Oposiciones Competencias de la Generalitat")
    - Referencias a CEF/academia en bloque NOTA IMPORTANTE
    """
    lines = raw.split('\n')
    out: list[str] = []
    skip_until_blank_count = 0

    for i, line in enumerate(lines):
        stripped = line.strip()

        # Saltar bloque copyright de múltiples líneas
        if skip_until_blank_count > 0:
            skip_until_blank_count -= 1
            continue

        # Línea vacía siempre pasa (salvo si ya hay muchas vacías seguidas)
        if not stripped:
            if out and out[-1] == '':
                continue  # no duplicar vacíos
            out.append('')
            continue

        # Artefactos: eliminar
        if _is_artifact_line(stripped):
            continue

        # Cabecera del archivo: eliminar
        if i == 0 and re.match(r'^Oposiciones Competencias', stripped, re.IGNORECASE):
            continue

        # Bloque NOTA IMPORTANTE con referencia a CEF/academia: eliminar
        if _is_nota_importante_block(lines, i):
            # Ver si la nota menciona CEF o academia (si es advertencia legal)
            # Tomamos las 5 próximas líneas para verificar
            block = ' '.join(lines[i:i+6])
            if re.search(r'CEF|academia|aula|virtual', block, re.IGNORECASE):
                skip_until_blank_count = 5
                continue

        # Línea con "CEF" sola o en contexto no académico legal -> eliminar
        if re.search(r'\bCEF\b', stripped) and not re.search(
            r'art[íi]culo|ley |decreto|orden |reglamento', stripped, re.IGNORECASE
        ):
            continue

        out.append(line)

    # Unir líneas que son continuación de párrafo (igual que clean_article_text)
    merged: list[str] = []
    for line in out:
        s = line.strip()
        if not s:
            merged.append('')
            continue
        if (merged and merged[-1].strip()
                and not merged[-1].rstrip().endswith(('.', ';', ':', '–', '—', '?', '!'))
                and s and s[0].islower()):
            merged[-1] = merged[-1].rstrip() + ' ' + s
        else:
            merged.append(line)

    # Eliminar bloques de vacíos al inicio/final
    result = '\n'.join(merged).strip()
    # Colapsar 3+ líneas vacías en 2
    result = re.sub(r'\n{3,}', '\n\n', result)
    # Eliminar símbolos de watermark que quedan sueltos
    result = re.sub(r'[ \t]*[■▪▶◼◆●][ \t]*', ' ', result)
    # Quitar espacios excesivos dentro de líneas (sin tocar saltos)
    result = '\n'.join(re.sub(r'[ \t]{2,}', ' ', line) for line in result.split('\n'))
    return result.strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--preview', type=int, metavar='TOPIC_NUMBER',
                        help='Solo previsualizar la limpieza de este tema')
    args = parser.parse_args()

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    rows = conn.execute(
        """
        SELECT tsr.id, tsr.content_text, t.topic_number
        FROM topic_study_resources tsr
        JOIN topics t ON t.id = tsr.topic_id
        WHERE tsr.resource_kind = 'temario_academia_cef'
          AND tsr.content_text IS NOT NULL
        ORDER BY t.topic_number
        """
    ).fetchall()

    print(f"Recursos CEF a limpiar: {len(rows)}")

    for row in rows:
        row = dict(row)
        tnum = row['topic_number']
        raw = row['content_text']
        clean = clean_cef_text(raw)

        reduction = 100 * (1 - len(clean) / len(raw)) if raw else 0

        if args.preview:
            if tnum == args.preview:
                print(f"\n=== PREVIEW Tema {tnum} ===")
                print(f"Original: {len(raw)} chars | Limpio: {len(clean)} chars | "
                      f"Reducción: {reduction:.1f}%\n")
                print(clean[:3000])
            continue

        conn.execute(
            "UPDATE topic_study_resources SET content_text=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (clean, row['id'])
        )
        print(f"  Tema {tnum}: {len(raw)} -> {len(clean)} chars ({reduction:.1f}% reduccion)")

    if not args.preview:
        conn.commit()
        print("\nLimpieza completada.")

    conn.close()


if __name__ == "__main__":
    main()
