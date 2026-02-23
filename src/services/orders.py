from decimal import Decimal

from fastapi import HTTPException
from fastapi.params import Depends
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database import get_db
from models import CartItems, Carts, OrderItems, Orders
from services.users import get_current_user


async def create_order(
    db: AsyncSession = Depends(get_db), user=Depends(get_current_user)
):
    cart_result = await db.execute(select(Carts).where(Carts.user_id == user.id))
    cart = cart_result.scalar_one_or_none()

    if not cart:
        raise HTTPException(status_code=404, detail="Cart not found")

    cart_items_result = await db.execute(
        select(CartItems)
        .where(CartItems.cart_id == cart.id)
        .options(selectinload(CartItems.movie))
    )
    cart_items = cart_items_result.scalars().all()

    if not cart_items:
        raise HTTPException(status_code=400, detail="Cart is empty")

    total = Decimal("0.0")
    not_available_movies = []

    for item in cart_items:
        if item.movie.is_available == 0:
            not_available_movies.append(item.movie.name)
            continue
        total += item.movie.price

    try:
        order = Orders(user_id=user.id, total_amount=total)
        db.add(order)
        await db.commit()
        await db.refresh(order)
    except Exception as e:
        print(e)

    for cart_item in cart_items:
        if cart_item.movie and cart_item.movie.price:
            order_item = OrderItems(
                order_id=order.id,
                movie_id=cart_item.movie.id,
                price_at_order=cart_item.movie.price,
            )
            db.add(order_item)

    await db.execute(delete(CartItems).where(CartItems.cart_id == cart.id))

    await db.commit()

    return order
