import stripe
from fastapi import APIRouter, Header, HTTPException, Request
from sqlalchemy.dialects.postgresql import insert
from app.db import session, StripeEvent
from app.settings import settings

router = APIRouter()

@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request, stripe_signature: str = Header(None)):
    payload = await request.body()
    try:
        event = stripe.Webhook.construct_event(payload, stripe_signature, settings.stripe_endpoint_secret)
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400)
    # at-most-once: primary key on the Stripe event id
    stmt = insert(StripeEvent).values(id=event["id"]).on_conflict_do_nothing()
    if session.execute(stmt).rowcount == 0:
        return {"status": "duplicate"}
    return {"status": "ok"}
