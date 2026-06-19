"""Convocatoria (announcement) monitor for tracking exam announcements.

MVP: Simple notification service placeholder.
Full: Would integrate with BOE/DOGV/GVA feeds.
"""

from __future__ import annotations

from typing import Any
from datetime import datetime


class ConvocatoriaMonitor:
    """Service for monitoring exam convocatoria changes."""

    def __init__(self):
        self.events = []

    def check_for_convocatoria_updates(self) -> dict[str, Any]:
        """Check for new convocatoria updates.

        MVP: Returns empty (no actual feeds integrated yet).
        """
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "events_detected": 0,
            "details": [],
            "note": "MVP: Awaiting integration with official sources (BOE/DOGV/GVA)",
        }

    def notify_on_event(
        self,
        event_type: str,
        title: str,
        description: str,
    ) -> dict[str, Any]:
        """Send notification for a convocatoria event.

        event_type: 'bases', 'listas', 'tribunal', 'fecha', 'sede', 'resultados'
        """
        notification = {
            "timestamp": datetime.utcnow().isoformat(),
            "type": event_type,
            "title": title,
            "description": description,
            "channels": ["local"],  # Would add email, push, calendar in future
        }
        self.events.append(notification)
        return notification

    def get_recent_events(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get recent convocatoria events."""
        return self.events[-limit:]
