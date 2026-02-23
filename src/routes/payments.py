from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from starlette.responses import HTMLResponse

from database import get_db
from services.users import check_admin
from src.models.payments import Payments
from src.models.users import User
from src.schemas.payments import PaymentSchema, PaymentStatusEnum
from src.services.payments import create_checkout_session, get_payments_history
from src.services.users import get_current_user

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.post("/checkout/{order_id}", response_model=dict)
async def checkout_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        success_url = "http://localhost:8099/payments/success"
        cancel_url = "http://localhost:8099/payments/cancel"

        session_info = await create_checkout_session(
            current_user, order_id, db, success_url, cancel_url
        )
        return session_info
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/history", response_model=List[PaymentSchema])
async def payments_history(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    payments = await get_payments_history(current_user.id, db)
    return payments


@router.get("/success", response_class=HTMLResponse)
async def payment_success():
    return "<h2>Payment Successful! ✅</h2>"


@router.get("/cancel", response_class=HTMLResponse)
async def payment_cancel():
    return "<h2>Payment Cancelled ❌</h2>"


@router.get("/all_payments_history")
async def payments_history(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    user_email: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    status: Optional[PaymentStatusEnum] = None,
):
    is_admin = await check_admin(email=user.email, db=db)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admins only")

    query = select(Payments).join(Payments.user)

    conditions = []

    if user_email:
        conditions.append(User.email == user_email)
    if start_date:
        conditions.append(Payments.created_at >= start_date)
    if end_date:
        conditions.append(Payments.created_at <= end_date)
    if status:
        conditions.append(Payments.status == status)

    if conditions:
        query = query.where(and_(*conditions))

    result = await db.execute(query.options(joinedload(Payments.user)))
    payments = result.unique().scalars().all()
    return payments
