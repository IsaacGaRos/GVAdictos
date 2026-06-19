"""Billing and subscription endpoints (F5)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Header, status, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
import stripe
import json

from src.api.dependencies import get_db, get_current_user
from src.billing.subscriptions import SubscriptionService
from src.billing import stripe_integration
from src.db.models import User

router = APIRouter()


# Pydantic models
class CheckoutRequest(BaseModel):
    """Request to create checkout session."""

    plan: str  # 'pro' or 'premium'
    success_url: str
    cancel_url: str


class CheckoutResponse(BaseModel):
    """Checkout session response."""

    session_id: str
    redirect_url: str


class SubscriptionResponse(BaseModel):
    """User subscription response."""

    plan: str
    status: str
    created_at: str


@router.post(
    "/checkout",
    response_model=CheckoutResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_checkout(
    request: CheckoutRequest,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create Stripe checkout session for subscription upgrade."""
    try:
        user_id = user.get("id")
        email = user.get("email")

        if not user_id or not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid user data",
            )

        # Create Stripe checkout session
        session_id = stripe_integration.create_checkout_session(
            user_id=user_id,
            email=email,
            plan=request.plan,
            success_url=request.success_url,
            cancel_url=request.cancel_url,
        )

        # Build redirect URL
        redirect_url = f"https://checkout.stripe.com/pay/{session_id}"

        return CheckoutResponse(session_id=session_id, redirect_url=redirect_url)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Checkout error: {e}",
        )


@router.get("/subscription", response_model=SubscriptionResponse)
async def get_subscription(
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get user's current subscription."""
    user_id = user.get("id")
    service = SubscriptionService(db)

    sub = service.get_subscription(user_id)

    if not sub:
        return SubscriptionResponse(
            plan="free",
            status="active",
            created_at="",
        )

    return SubscriptionResponse(
        plan=sub.plan,
        status=sub.status,
        created_at=sub.created_at.isoformat() if sub.created_at else "",
    )


@router.post("/cancel-subscription", status_code=status.HTTP_200_OK)
async def cancel_subscription(
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Cancel user's subscription."""
    user_id = user.get("id")
    service = SubscriptionService(db)

    sub = service.cancel_subscription(user_id)

    return {
        "message": "Subscription cancelled",
        "plan": sub.plan if sub else "free",
    }


@router.post("/webhook", status_code=status.HTTP_200_OK)
async def webhook(
    request: Request,
    db: Session = Depends(get_db),
    stripe_signature: str = Header(None),
):
    """Handle Stripe webhook events.

    Endpoint for Stripe to send webhook events.
    Verify signature and process event.
    """
    from src.core.paths import PROJECT_ROOT
    import os

    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")

    if not webhook_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook secret not configured",
        )

    try:
        payload = await request.body()
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, webhook_secret
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid payload",
        )
    except stripe.error.SignatureVerificationError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid signature",
        )

    # Process event
    success = stripe_integration.handle_webhook_event(event, db)

    if not success:
        print(f"[Webhook] Unhandled event: {event.get('type')}")

    return {"received": True}
