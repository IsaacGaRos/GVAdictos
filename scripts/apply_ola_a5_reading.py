#!/usr/bin/env python3
"""
Ola A5: Lectura optimizada (design tokens + preferencias).

Demo: muestra diferentes presets y genera CSS.
"""

from __future__ import annotations

import argparse
import sys

from src.core.db import connect
from src.study.reading_schema import apply_reading_schema, reading_schema_exists
from src.study.reading_service import ReadingPreferencesService


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Ola A5: Lectura optimizada"
    )
    args = parser.parse_args()

    print("=" * 70)
    print("OLA A5: Lectura optimizada (tipografia, contraste, accesibilidad)")
    print("=" * 70)

    try:
        with connect() as conn:
            print("\nPaso 1: Crear tablas de lectura...")
            apply_reading_schema(conn)
            if reading_schema_exists(conn):
                print("[OK] Tablas user_reading_preferences, design_tokens, reading_presets creadas")
            else:
                print("[ERROR] Las tablas no se crearon correctamente")
                return 1

            print("\nPaso 2: Listar presets disponibles...")
            service = ReadingPreferencesService(conn, user_id=1)
            presets = service.list_presets()
            for preset in presets:
                print(f"  - {preset['preset_name']}: {preset['description']}")

            print("\nPaso 3: Demo - Aplicar presets y generar CSS...")

            presets_to_demo = ["standard", "large_print", "dyslexia_friendly", "dark_mode"]

            for preset_name in presets_to_demo:
                if preset_name in [p["preset_name"] for p in presets]:
                    service.apply_preset(preset_name)
                    prefs = service.get_preferences()
                    css = service.generate_css()

                    print(f"\n  Preset: {preset_name}")
                    print(f"    Font: {prefs['font_family']} {prefs['font_size']}px")
                    print(f"    Line height: {prefs['line_height']}")
                    print(f"    Max width: {prefs['max_width']}px")
                    print(f"    Theme: {prefs['theme']}")
                    print(f"    Contrast: {prefs['contrast']}")
                    print(f"    Dyslexia mode: {bool(prefs['dyslexia_mode'])}")
                    print(f"    CSS lines: {len(css.strip().split(chr(10)))}")

            print("\nPaso 4: Validacion...")
            prefs_count = int(conn.execute("SELECT COUNT(*) FROM user_reading_preferences").fetchone()[0])
            tokens_count = int(conn.execute("SELECT COUNT(*) FROM design_tokens").fetchone()[0])
            presets_count = int(conn.execute("SELECT COUNT(*) FROM reading_presets").fetchone()[0])

            print(f"  [OK] user_reading_preferences: {prefs_count} filas")
            print(f"  [OK] design_tokens: {tokens_count} filas")
            print(f"  [OK] reading_presets: {presets_count} presets")

            conn.commit()
            print("\n[OK] Migracion completada")
            return 0

    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
