"""Orquestador del pipeline de exámenes oficiales (ranking).

Ejecuta en orden:
  1. rebuild_official_exams.py   (exámenes en TEXTO: parseo + ley/art explícito)
  2. ocr_exam_loader.py          (exámenes ESCANEADOS vía OCR)
  3. infer_and_link.py           (inferencia de artículo por ley)
  4. infer_global_fallback.py    (barrida global: toda pregunta -> >=1 artículo)

Uso:  python scripts/run_exam_pipeline.py
"""
import subprocess, sys, os

HERE = os.path.dirname(os.path.abspath(__file__))
STEPS = [
    ("Exámenes en texto", "rebuild_official_exams.py"),
    ("Exámenes OCR (escaneados)", "ocr_exam_loader.py"),
    ("Multi-artículo (preguntas con >1 artículo explícito)", "enrich_multiarticle.py"),
    ("Inferencia de artículo por ley", "infer_and_link.py"),
    ("Barrida global (toda pregunta >=1 artículo)", "infer_global_fallback.py"),
]


def main():
    for title, script in STEPS:
        print("\n" + "=" * 60)
        print("» %s  (%s)" % (title, script))
        print("=" * 60)
        r = subprocess.run([sys.executable, os.path.join(HERE, script)])
        if r.returncode != 0:
            print("FALLO en %s (código %d). Abortando." % (script, r.returncode))
            return r.returncode
    print("\n✓ Pipeline completado.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
