"""Simulacros (mock exams) module for practice tests and analysis.

Provides exam simulation, question selection, scoring, and statistics.
"""

from src.simulacros.service import ExamService, ExamServiceError
from src.simulacros.repository import SimulacrpsRepository, SimulacrospError, SimulacroseemaMissingError
from src.simulacros.schema import ensure_simulacros_tables, missing_simulacros_tables

__all__ = [
    "ExamService",
    "ExamServiceError",
    "SimulacrpsRepository",
    "SimulacrospError",
    "SimulacroseemaMissingError",
    "ensure_simulacros_tables",
    "missing_simulacros_tables",
]
