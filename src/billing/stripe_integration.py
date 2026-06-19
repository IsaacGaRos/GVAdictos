"""Stripe billing integration for F5.

Plans:
  - Free: No payment (local storage only)
  - Pro: $9.99/month (1 oposición)
  - Premium: $19.99/month (unlimited oposiciones)

Features:
  - Checkout session creation
  - Webhook event handling
  - Subscription status management
  - Entitlement granting/revocation
"""

import os
import stripe
from datetime import datetime
from typing import Optional, Dict, Any

# Initialize Stripe
stripe.api_key = os.getenv("STRIPE_API_KEY", "")

# Stripe Product & Price IDs (from Stripe Dashboard)
STRIPE_PRICES = {
    "pro": os.getenv("STRIPE_PRICE_PRO", "price_1234567890"),
    "premium": os.getenv("STRIPE_PRICE_PREMIUM", "price_0987654321"),
}

# Plan features mapping
PLAN_FEATURES = {
    "free": ["study", "srs"],
    "pro": ["study", "srs", "ai_insights", "tts", "exams"],
    "premium": ["study", "srs", "ai_insights", "tts", "exams", "drive_backup"],
}

# Plan pricing (cents)
PLAN_PRICING = {
    "free": 0,
    "pro": 999,
    "premium": 1999,
}


def create_checkout_session(
    user_id: int,
    email: str,
    plan: str,
    success_url: str,
    cancel_url: str,
) -> str:
    """Create Stripe checkout session for subscription.

    Args:
        user_id: User ID in database
        email: User email for Stripe customer
        plan: 'pro' or 'premium'
        success_url: Redirect URL after successful payment
        cancel_url: Redirect URL if user cancels

    Returns:
        Stripe session ID for checkout
    """
    if plan not in STRIPE_PRICES:
        raise ValueError(f"Invalid plan: {plan}")

    if not stripe.api_key or stripe.api_key.startswith("sk_test_"):
        raise RuntimeError("STRIPE_API_KEY not configured")

    try:
        session = stripe.checkout.Session.create(
            customer_email=email,
            client_reference_id=str(user_id),
            line_items=[
                {
                    "price": STRIPE_PRICES[plan],
                    "quantity": 1,
                }
            ],
            mode="subscription",
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={"plan": plan, "user_id": user_id},
        )
        return session.id
    except stripe.error.StripeError as e:
        raise RuntimeError(f"Stripe error: {e}")


def handle_webhook_event(event: Dict[str, Any], db_session) -> bool:
    """Handle Stripe webhook event.

    Events:
      - checkout.session.completed: New subscription created
      - invoice.payment_succeeded: Payment successful
      - invoice.payment_failed: Payment failed
      - customer.subscription.deleted: Subscription cancelled
      - customer.subscription.updated: Subscription updated

    Args:
        event: Stripe webhook event
        db_session: SQLAlchemy session

    Returns:
        True if handled successfully, False otherwise
    """
    from src.db.models import Subscription, Entitlement, User

    event_type = event.get("type", "")
    data = event.get("data", {}).get("object", {})

    try:
        if event_type == "checkout.session.completed":
            return _handle_checkout_complete(data, db_session)

        elif event_type == "invoice.payment_succeeded":
            return _handle_payment_succeeded(data, db_session)

        elif event_type == "invoice.payment_failed":
            return _handle_payment_failed(data, db_session)

        elif event_type == "customer.subscription.deleted":
            return _handle_subscription_deleted(data, db_session)

        elif event_type == "customer.subscription.updated":
            return _handle_subscription_updated(data, db_session)

        return False

    except Exception as e:
        print(f"[Webhook Error] {event_type}: {e}")
        return False


def _handle_checkout_complete(data: Dict[str, Any], db_session) -> bool:
    """Handle checkout.session.completed event."""
    from src.db.models import Subscription, User

    user_id = int(data.get("client_reference_id", 0))
    customer_id = data.get("customer", "")
    subscription_id = data.get("subscription", "")
    plan = data.get("metadata", {}).get("plan", "free")

    if not user_id or not customer_id:
        return False

    try:
        user = db_session.query(User).filter_by(id=user_id).first()
        if not user:
            return False

        # Create or update subscription
        sub = db_session.query(Subscription).filter_by(user_id=user_id).first()
        if not sub:
            sub = Subscription(
                user_id=user_id,
                stripe_customer_id=customer_id,
                stripe_subscription_id=subscription_id,
                plan=plan,
                status="active",
            )
            db_session.add(sub)
        else:
            sub.stripe_customer_id = customer_id
            sub.stripe_subscription_id = subscription_id
            sub.plan = plan
            sub.status = "active"

        db_session.commit()
        _grant_entitlements(user_id, plan, db_session)
        return True

    except Exception as e:
        print(f"[Webhook] Checkout error: {e}")
        db_session.rollback()
        return False


def _handle_payment_succeeded(data: Dict[str, Any], db_session) -> bool:
    """Handle invoice.payment_succeeded event."""
    from src.db.models import Subscription

    customer_id = data.get("customer", "")
    subscription_id = data.get("subscription", "")

    try:
        sub = (
            db_session.query(Subscription)
            .filter_by(stripe_subscription_id=subscription_id)
            .first()
        )
        if sub:
            sub.status = "active"
            db_session.commit()
        return True
    except Exception as e:
        print(f"[Webhook] Payment succeeded error: {e}")
        db_session.rollback()
        return False


def _handle_payment_failed(data: Dict[str, Any], db_session) -> bool:
    """Handle invoice.payment_failed event."""
    from src.db.models import Subscription

    subscription_id = data.get("subscription", "")

    try:
        sub = (
            db_session.query(Subscription)
            .filter_by(stripe_subscription_id=subscription_id)
            .first()
        )
        if sub:
            sub.status = "past_due"
            db_session.commit()
            # TODO: Send email notification
        return True
    except Exception as e:
        print(f"[Webhook] Payment failed error: {e}")
        db_session.rollback()
        return False


def _handle_subscription_deleted(data: Dict[str, Any], db_session) -> bool:
    """Handle customer.subscription.deleted event."""
    from src.db.models import Subscription

    subscription_id = data.get("id", "")

    try:
        sub = (
            db_session.query(Subscription)
            .filter_by(stripe_subscription_id=subscription_id)
            .first()
        )
        if sub:
            sub.status = "canceled"
            sub.canceled_at = datetime.utcnow()
            db_session.commit()
            _revoke_entitlements(sub.user_id, db_session)
        return True
    except Exception as e:
        print(f"[Webhook] Subscription deleted error: {e}")
        db_session.rollback()
        return False


def _handle_subscription_updated(data: Dict[str, Any], db_session) -> bool:
    """Handle customer.subscription.updated event."""
    from src.db.models import Subscription

    subscription_id = data.get("id", "")
    status = data.get("status", "")

    try:
        sub = (
            db_session.query(Subscription)
            .filter_by(stripe_subscription_id=subscription_id)
            .first()
        )
        if sub:
            sub.status = status
            sub.current_period_start = datetime.fromtimestamp(
                data.get("current_period_start", 0)
            )
            sub.current_period_end = datetime.fromtimestamp(
                data.get("current_period_end", 0)
            )
            db_session.commit()
        return True
    except Exception as e:
        print(f"[Webhook] Subscription updated error: {e}")
        db_session.rollback()
        return False


def _grant_entitlements(user_id: int, plan: str, db_session) -> None:
    """Grant features for a plan to user."""
    from src.db.models import Entitlement

    features = PLAN_FEATURES.get(plan, [])

    for feature in features:
        existing = (
            db_session.query(Entitlement)
            .filter_by(user_id=user_id, feature=feature)
            .first()
        )
        if not existing:
            ent = Entitlement(user_id=user_id, feature=feature)
            db_session.add(ent)

    db_session.commit()


def _revoke_entitlements(user_id: int, db_session) -> None:
    """Revoke all paid features (keep free features)."""
    from src.db.models import Entitlement

    paid_features = [f for f in PLAN_FEATURES["premium"] if f not in PLAN_FEATURES["free"]]
    db_session.query(Entitlement).filter(
        Entitlement.user_id == user_id,
        Entitlement.feature.in_(paid_features),
    ).delete()
    db_session.commit()


def has_entitlement(user_id: int, feature: str, db_session) -> bool:
    """Check if user has entitlement for feature."""
    from src.db.models import Entitlement

    return (
        db_session.query(Entitlement)
        .filter_by(user_id=user_id, feature=feature)
        .first()
        is not None
    )
