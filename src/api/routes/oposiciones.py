"""Multi-oposición endpoints (F7)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.api.dependencies import get_db, get_current_user
from src.oposiciones.service import OposicionService

router = APIRouter()


class OposicionResponse(BaseModel):
    """Oposición response."""

    id: int
    code: str
    nombre: str
    administracion: str
    activa: bool = True


class EnrollmentRequest(BaseModel):
    """Enrollment request."""

    oposicion_id: int


@router.get(
    "/",
    response_model=list[OposicionResponse],
    status_code=status.HTTP_200_OK,
)
async def list_oposiciones(
    db: Session = Depends(get_db),
):
    """List all available oposiciones."""
    service = OposicionService(db)
    opos = service.list_oposiciones(activa_only=True)

    return [OposicionResponse(**o) for o in opos]


@router.get(
    "/user",
    response_model=list[OposicionResponse],
    status_code=status.HTTP_200_OK,
)
async def get_user_oposiciones(
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get oposiciones enrolled by user."""
    user_id = user.get("id")
    service = OposicionService(db)
    opos = service.get_user_oposiciones(user_id)

    return [OposicionResponse(**o) for o in opos]


@router.post(
    "/enroll",
    status_code=status.HTTP_200_OK,
)
async def enroll_in_oposicion(
    request: EnrollmentRequest,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Enroll user in oposición."""
    user_id = user.get("id")
    service = OposicionService(db)

    success = service.enroll_user(user_id, request.oposicion_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already enrolled or invalid oposición",
        )

    opo = service.get_oposicion(request.oposicion_id)

    return {
        "message": f"Enrolled in {opo['nombre']}",
        "oposicion": opo,
    }


@router.post(
    "/unenroll",
    status_code=status.HTTP_200_OK,
)
async def unenroll_from_oposicion(
    request: EnrollmentRequest,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Unenroll user from oposición."""
    user_id = user.get("id")
    service = OposicionService(db)

    success = service.unenroll_user(user_id, request.oposicion_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Not enrolled",
        )

    return {"message": "Unenrolled successfully"}


@router.get(
    "/{oposicion_id}/topics",
    status_code=status.HTTP_200_OK,
)
async def get_oposicion_topics(
    oposicion_id: int,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get topics for oposición (if enrolled)."""
    user_id = user.get("id")
    service = OposicionService(db)

    # Check if user is enrolled
    if not service.is_user_enrolled(user_id, oposicion_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enrolled in this oposición",
        )

    topics = service.get_oposicion_topics(oposicion_id)

    return {
        "oposicion_id": oposicion_id,
        "topics_count": len(topics),
        "topics": topics,
    }
