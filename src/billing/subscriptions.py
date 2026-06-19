"""Subscription service for managing user billing and feature access.

Uses SQLAlchemy ORM and Stripe for payment processing.
"""

from __future__ import annotations

from typing import Optional
from datetime import datetime
from enum import Enum
from sqlalchemy.orm import Session

from src.db.models import Subscription, User, Entitlement
from src.billing import stripe_integration


class Plan(str, Enum):
    """Subscription plans."""
    FREE = "free"
    PRO = "pro"
    PREMIUM = "premium"


class SubscriptionService:
    """Service for subscription management."""

    PLANS = {
        "free": {
            "price": 0,
            "features": ["study", "srs"],
            "description": "Estudio básico",
        },
        "pro": {
            "price": 9.99,
            "features": ["study", "srs", "ai_insights", "tts", "exams"],
            "description": "Una oposición",
        },
        "premium": {
            "price": 19.99,
            "features": [
                "study",
                "srs",
                "ai_insights",
                "tts",
                "exams",
                "drive_backup",
            ],
            "description": "Oposiciones ilimitadas",
        },
    }

    def __init__(self, db: Session) -> None:
        self.db = db

    def create_subscription(
        self,
        user_id: int,
        plan: str = "free",
        stripe_customer_id: Optional[str] = None,
        stripe_subscription_id: Optional[str] = None,
    ) -> Subscription:
        """Create a subscription for user."""
        if plan not in self.PLANS:
            raise ValueError(f"Invalid plan: {plan}")

        sub = Subscription(
            user_id=user_id,
            plan=plan,
            status="active",
            stripe_customer_id=stripe_customer_id,
            stripe_subscription_id=stripe_subscription_id,
        )
        self.db.add(sub)
        self.db.commit()

        # Grant entitlements
        stripe_integration._grant_entitlements(user_id, plan, self.db)

        return sub

    def get_subscription(self, user_id: int) -> Optional[Subscription]:
        """Get user's active subscription."""
        return (
            self.db.query(Subscription)
            .filter_by(user_id=user_id)
            .order_by(Subscription.created_at.desc())
            .first()
        )

    def upgrade_plan(self, user_id: int, new_plan: str) -> Subscription:
        """Upgrade user to new plan."""
        if new_plan not in self.PLANS:
            raise ValueError(f"Invalid plan: {new_plan}")

        sub = self.get_subscription(user_id)
        if not sub:
            return self.create_subscription(user_id, new_plan)

        sub.plan = new_plan
        sub.status = "active"
        self.db.commit()

        # Grant new entitlements
        stripe_integration._grant_entitlements(user_id, new_plan, self.db)

        return sub

    def downgrade_plan(self, user_id: int, new_plan: str = "free") -> Subscription:
        """Downgrade user to lower plan."""
        sub = self.upgrade_plan(user_id, new_plan)

        # Revoke paid features if downgrading from paid plan
        if new_plan == "free":
            stripe_integration._revoke_entitlements(user_id, self.db)

        return sub

    def get_user_plan(self, user_id: int) -> str:
        """Get user's current plan."""
        sub = self.get_subscription(user_id)
        return sub.plan if sub else "free"

    def has_feature(self, user_id: int, feature: str) -> bool:
        """Check if user has access to feature."""
        return stripe_integration.has_entitlement(user_id, feature, self.db)

    def cancel_subscription(self, user_id: int) -> Optional[Subscription]:
        """Cancel user's subscription (downgrade to free)."""
        sub = self.get_subscription(user_id)
        if not sub:
            return None

        sub.status = "canceled"
        sub.canceled_at = datetime.utcnow()
        self.db.commit()

        # Revoke paid features
        stripe_integration._revoke_entitlements(user_id, self.db)

        return sub

    def get_plan_info(self, plan: str) -> dict:
        """Get plan information."""
        return self.PLANS.get(plan, {})
