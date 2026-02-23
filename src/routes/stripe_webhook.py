import os

import stripe
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from database import get_db
from src.models.orders import OrderStatusEnum
from src.models.payments import Payments, StatusEnum

load_dotenv()

router = APIRouter(prefix="/stripe", tags=["Stripe"])
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET")


@router.post("/webhook")
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]

        result = await db.execute(
            select(Payments)
            .where(Payments.external_payment_id == session["id"])
            .options(selectinload(Payments.order))
        )
        payment = result.scalar_one_or_none()
        if payment and payment.order:
            payment.status = StatusEnum.SUCCESSFUL
            payment.order.status = OrderStatusEnum.PAID
            await db.commit()

    return {"status": "success"}
