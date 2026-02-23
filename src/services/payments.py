import os
from datetime import datetime, timezone
from decimal import Decimal

import stripe
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from src.models.orders import Orders, OrderStatusEnum
from src.models.payments import PaymentItems, Payments, StatusEnum
from src.models.users import User

load_dotenv()

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")


async def create_checkout_session(
    user: User, order_id: int, db: AsyncSession, success_url: str, cancel_url: str
) -> dict:
    result = await db.execute(
        select(Orders)
        .options(selectinload(Orders.items))
        .where(Orders.id == order_id, Orders.user_id == user.id)
    )
    order = result.scalar_one_or_none()

    if not order:
        raise ValueError("Order not found")

    if order.status == OrderStatusEnum.PAID:
        raise ValueError("Order already paid")

    total_amount = sum(item.price_at_order for item in order.items)

    if total_amount <= 0:
        raise ValueError("Invalid order amount")

    line_items = [
        {
            "price_data": {
                "currency": "usd",
                "product_data": {"name": f"Order #{order.id} - Item {item.id}"},
                "unit_amount": int(item.price_at_order * 100),
            },
            "quantity": 1,
        }
        for item in order.items
    ]

    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=line_items,
        mode="payment",
        success_url=success_url + "?session_id={CHECKOUT_SESSION_ID}",
        cancel_url=cancel_url,
        metadata={"order_id": str(order.id), "user_id": str(user.id)},
    )

    payment = Payments(
        user_id=user.id,
        order_id=order.id,
        amount=Decimal(total_amount),
        status=StatusEnum.PENDING,
        external_payment_id=session.id,
        created_at=datetime.now(timezone.utc),
    )
    db.add(payment)
    await db.commit()
    await db.refresh(payment)

    for item in order.items:
        pi = PaymentItems(
            payment_id=payment.id,
            order_item_id=item.id,
            price_at_payment=item.price_at_order,
        )
        db.add(pi)
    await db.commit()

    return {"checkout_url": session.url, "payment_id": payment.id}


async def get_payments_history(user_id: int, db: AsyncSession):
    result = await db.execute(
        select(Payments)
        .where(Payments.user_id == user_id)
        .options(selectinload(Payments.payment_items))
        .order_by(Payments.created_at.desc())
    )
    payments = result.scalars().all()
    return payments
