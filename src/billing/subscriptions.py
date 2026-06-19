"""Subscription management for Stripe integration (F5)."""

from __future__ import annotations

import sqlite3
from typing import Any
from datetime import datetime
from enum import Enum


class Plan(str, Enum):
    """Subscription plans."""
    FREE = "free"
    PRO = "pro"
    PREMIUM = "premium"


class Subscription:
    """Subscription model for billing."""

    PLANS = {
        "free": {"price": 0, "features": ["1_oposicion", "basic_ai"]},
        "pro": {"price": 9.99, "features": ["unlimited_oposiciones", "full_ai", "tts"]},
        "premium": {"price": 19.99, "features": ["unlimited_oposiciones", "full_ai", "tts", "srs", "admin"]},
    }

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def create_subscription(
        self,
        user_id: int,
        plan: str = "free",
        stripe_customer_id: str | None = None,
    ) -> int:
        """Create a subscription for user."""
        cursor = self.conn.execute(
            """
            INSERT INTO subscriptions(user_id, plan, stripe_customer_id, status)
            VALUES (?, ?, ?, 'active')
            """,
            (user_id, plan, stripe_customer_id),
        )
        self.conn.commit()
        return int(cursor.lastrowid)

    def get_user_subscription(self, user_id: int) -> dict[str, Any] | None:
        """Get user's current subscription."""
        row = self.conn.execute(
            "SELECT * FROM subscriptions WHERE user_id = ? ORDER BY created_at DESC LIMIT 1",
            (user_id,),
        ).fetchone()
        return dict(row) if row else None

    def upgrade_plan(self, user_id: int, new_plan: str) -> bool:
        """Upgrade user to a new plan."""
        if new_plan not in self.PLANS:
            return False

        self.conn.execute(
            "UPDATE subscriptions SET plan = ?, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?",
            (new_plan, user_id),
        )
        self.conn.commit()
        return True

    def check_feature_access(self, user_id: int, feature: str) -> bool:
        """Check if user has access to a feature."""
        sub = self.get_user_subscription(user_id)
        if not sub:
            return feature in self.PLANS["free"]["features"]

        plan = sub["plan"]
        return feature in self.PLANS.get(plan, {}).get("features", [])

    def create_checkout_session(self, user_id: int, plan: str) -> str:
        """Create Stripe checkout session (mock for MVP)."""
        # MVP: Return mock session ID
        # Real implementation: stripe.checkout.Session.create(...)
        return f"session_{user_id}_{plan}_{datetime.utcnow().timestamp()}"

    def handle_webhook(self, event_type: str, data: dict) -> None:
        """Handle Stripe webhook events."""
        if event_type == "invoice.payment_succeeded":
            user_id = data.get("user_id")
            plan = data.get("plan")
            if user_id and plan:
                self.upgrade_plan(user_id, plan)
        elif event_type == "invoice.payment_failed":
            user_id = data.get("user_id")
            if user_id:
                self.upgrade_plan(user_id, "free")
