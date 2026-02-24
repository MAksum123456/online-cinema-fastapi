from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.params import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from services.orders import create_order
from services.users import check_admin, get_current_user
from src.models.orders import Orders, OrderStatusEnum
from src.models.users import User

router = APIRouter()


@router.post("/order")
async def create_orders(
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
):
    order = await create_order(db, user)
    return order


@router.patch("/order/{order_id}")
async def cancel_order(
    order_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    order_request = await db.execute(
        select(Orders).where(Orders.id == order_id, Orders.user_id == user.id)
    )
    result = order_request.scalar_one_or_none()

    if result is None:
        raise HTTPException(status_code=404, detail="Order not found")
    if result.status == "paid":
        raise HTTPException(status_code=409, detail="Order paid")

    if result.status == "canceled":
        raise HTTPException(status_code=409, detail="Order canceled")

    if result.status == "pending":
        result.status = "canceled"
        db.add(result)
        await db.commit()
        await db.refresh(result)

    return result.status


@router.get("/all_orders")
async def get_all_orders(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    user_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    status: Optional[OrderStatusEnum] = None,
):
    check = await check_admin(email=user.email, db=db)
    if not check:
        raise HTTPException(
            status_code=403, detail="User does not have permission to view all orders."
        )

    query = select(Orders)
    filters = []

    if user_id is not None:
        filters.append(Orders.user_id == user_id)

    if start_date is not None:
        filters.append(Orders.created_at >= start_date)

    if end_date is not None:
        filters.append(Orders.created_at <= end_date)

    if status is not None:
        filters.append(Orders.status == status)

    if filters:
        query = query.where(*filters)

    all_orders_request = await db.execute(query)
    all_orders = all_orders_request.scalars().all()

    return all_orders
