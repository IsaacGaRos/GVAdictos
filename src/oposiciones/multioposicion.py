"""
Multi-oposición support for Ola F7.

Allows managing multiple simultaneous opositions (GVA A1-01, A1-02, etc.).
"""

MULTIOPOSICION_SPEC = """
F7 — Multi-Oposición Architecture

Database Design (data sharing):
  - laws, articles: GLOBAL (shared across all oposiciones)
  - topics: per oposición (each oposición has its own curriculum)
  - topic_sources: per oposición (links topics to laws/articles)
  - user_oposicion_enrollment: tracks user progress per oposición

Schema additions:
  CREATE TABLE oposiciones (
    id INTEGER PRIMARY KEY,
    code TEXT UNIQUE,  -- "A1-01-GVA", "A2-02-GVA", etc.
    nombre TEXT,
    administracion TEXT,
    activa BOOLEAN DEFAULT 1
  );

  CREATE TABLE user_oposicion_enrollment (
    id INTEGER PRIMARY KEY,
    user_id INTEGER REFERENCES users,
    oposicion_id INTEGER REFERENCES oposiciones,
    enrolled_at TEXT,
    PRIMARY KEY (user_id, oposicion_id)
  );

Workflow:
  1. User registers
  2. User selects oposición(es) to study
  3. Each oposición has independent:
     - Study progress (study_last_reviews, study_progress)
     - Exams (mock_exams)
     - Dashboard (metrics per oposición)
  4. User can switch between oposiciones in UI

Implementation:
  - Add oposicion_id filter to all user-specific queries
  - Store current_oposicion_id in user session
  - Update all services to respect oposicion_id
  - API endpoints: /api/oposiciones, /api/oposiciones/{id}/topics, etc.

Adding a new oposición:
  1. INSERT into oposiciones (code, nombre, administracion)
  2. Import or create topics for that oposición
  3. Create topic_sources linking to existing laws/articles
  4. Enable in UI

Example migrations:
  - GVA A1-01 2025 (actual Convocatoria 1/2025)
  - GVA A1-02 2025 (Convocatoria 2/2025)
  - GVA A2 future
  - Other administraciones (CCAA, estatal, etc.)
"""

def get_user_oposiciones(user_id: int) -> list[dict]:
    """Get oposiciones enrolled by user.

    Implementation:
        SELECT o.* FROM oposiciones o
        JOIN user_oposicion_enrollment uoe ON o.id = uoe.oposicion_id
        WHERE uoe.user_id = ?
    """
    raise NotImplementedError("F7: Multi-oposición pending")


def enroll_user_in_oposicion(user_id: int, oposicion_id: int) -> bool:
    """Enroll user in an oposición."""
    raise NotImplementedError("F7: Enrollment pending")


def get_oposicion_stats(user_id: int, oposicion_id: int) -> dict:
    """Get user statistics for a specific oposición."""
    raise NotImplementedError("F7: Multi-oposición stats pending")
