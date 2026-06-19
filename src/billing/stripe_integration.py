"""
Stripe billing integration for Ola F5.

MVP: Placeholder specification for payment integration.

Implementation requires:
    pip install stripe
"""

STRIPE_INTEGRATION_SPEC = """
F5 — Stripe Integration (Suscripciones + Pagos)

Plans:
  1. Free (localStorage only)
  2. Pro ($9.99/month - single oposición)
  3. Premium ($19.99/month - unlimited oposiciones)
  4. Admin (internal)

Feature Gating:
  - Entitlements table: (user_id, plan, feature_flag)
  - API checks permission before serving expensive features (IA, TTS)
  - Downgrade: suspend features, keep data

Webhook Handling:
  - invoice.payment_succeeded → update subscription status
  - invoice.payment_failed → notify user, downgrade
  - customer.subscription.deleted → cleanup

Database Schema:
  CREATE TABLE subscriptions (
    id INTEGER PRIMARY KEY,
    user_id INTEGER REFERENCES users,
    stripe_customer_id TEXT,
    stripe_subscription_id TEXT,
    plan TEXT,
    status TEXT,
    current_period_end TEXT,
    cancel_at_period_end BOOLEAN
  );

  CREATE TABLE entitlements (
    id INTEGER PRIMARY KEY,
    plan TEXT,
    feature TEXT,
    enabled BOOLEAN
  );
"""

def create_checkout_session(user_id: int, plan: str) -> str:
    """Create Stripe checkout session.

    Implementation:
        import stripe
        stripe.api_key = os.environ['STRIPE_API_KEY']
        session = stripe.checkout.Session.create(
            customer_email=user.email,
            line_items=[...],
            mode='subscription',
            success_url='...',
            cancel_url='...'
        )
        return session.id
    """
    raise NotImplementedError("F5: Stripe integration pending")


def handle_webhook(event_type: str, data: dict) -> None:
    """Handle Stripe webhook events."""
    raise NotImplementedError("F5: Webhook handling pending")
