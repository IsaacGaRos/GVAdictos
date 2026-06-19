"""Multi-oposición service for F7.

Allows users to:
  - Browse available oposiciones (GVA + others)
  - Enroll in multiple oposiciones
  - Switch between oposiciones when studying
  - See progress per oposición
"""

from __future__ import annotations

from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session

from src.db.models import (
    Oposicion,
    UserOposicionEnrollment,
    Topic,
    User,
)


class OposicionService:
    """Service for managing multiple oposiciones."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create_oposicion(
        self,
        code: str,
        nombre: str,
        administracion: str = "GVA",
    ) -> Oposicion:
        """Create a new oposición."""
        opo = Oposicion(code=code, nombre=nombre, administracion=administracion, activa=True)
        self.db.add(opo)
        self.db.commit()
        return opo

    def list_oposiciones(self, activa_only: bool = True) -> List[Dict[str, Any]]:
        """List available oposiciones."""
        query = self.db.query(Oposicion)

        if activa_only:
            query = query.filter_by(activa=True)

        opos = query.order_by(Oposicion.administracion, Oposicion.code).all()

        return [
            {
                "id": o.id,
                "code": o.code,
                "nombre": o.nombre,
                "administracion": o.administracion,
                "activa": o.activa,
            }
            for o in opos
        ]

    def get_oposicion(self, opo_id: int) -> Optional[Dict[str, Any]]:
        """Get oposición by ID."""
        opo = self.db.query(Oposicion).filter_by(id=opo_id).first()

        if not opo:
            return None

        return {
            "id": opo.id,
            "code": opo.code,
            "nombre": opo.nombre,
            "administracion": opo.administracion,
            "activa": opo.activa,
        }

    def enroll_user(self, user_id: int, opo_id: int) -> bool:
        """Enroll user in an oposición."""
        try:
            # Check if already enrolled
            existing = (
                self.db.query(UserOposicionEnrollment)
                .filter_by(user_id=user_id, oposicion_id=opo_id)
                .first()
            )

            if existing:
                return False  # Already enrolled

            enrollment = UserOposicionEnrollment(
                user_id=user_id,
                oposicion_id=opo_id,
            )
            self.db.add(enrollment)
            self.db.commit()
            return True

        except Exception:
            self.db.rollback()
            return False

    def unenroll_user(self, user_id: int, opo_id: int) -> bool:
        """Unenroll user from oposición."""
        try:
            enrollment = (
                self.db.query(UserOposicionEnrollment)
                .filter_by(user_id=user_id, oposicion_id=opo_id)
                .first()
            )

            if enrollment:
                self.db.delete(enrollment)
                self.db.commit()
                return True

            return False

        except Exception:
            self.db.rollback()
            return False

    def get_user_oposiciones(self, user_id: int) -> List[Dict[str, Any]]:
        """Get oposiciones enrolled by user."""
        enrollments = (
            self.db.query(Oposicion)
            .join(UserOposicionEnrollment)
            .filter(UserOposicionEnrollment.user_id == user_id)
            .order_by(Oposicion.administracion, Oposicion.code)
            .all()
        )

        return [
            {
                "id": o.id,
                "code": o.code,
                "nombre": o.nombre,
                "administracion": o.administracion,
            }
            for o in enrollments
        ]

    def get_oposicion_topics(self, opo_id: int) -> List[Dict[str, Any]]:
        """Get topics for an oposición (all A1-01 topics for now)."""
        # TODO: In future, associate topics with oposiciones
        topics = (
            self.db.query(Topic)
            .order_by(Topic.topic_number)
            .limit(75)
            .all()
        )

        return [
            {
                "id": t.id,
                "topic_number": t.topic_number,
                "part": t.part,
                "official_text": t.official_text[:100] if t.official_text else "",
                "section": t.section,
            }
            for t in topics
        ]

    def is_user_enrolled(self, user_id: int, opo_id: int) -> bool:
        """Check if user is enrolled in oposición."""
        enrollment = (
            self.db.query(UserOposicionEnrollment)
            .filter_by(user_id=user_id, oposicion_id=opo_id)
            .first()
        )
        return enrollment is not None
