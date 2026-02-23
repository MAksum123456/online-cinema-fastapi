from fastapi import APIRouter, HTTPException
from fastapi.params import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database import get_db
from schemas.carts import CartListSchema
from services.users import check_admin, get_current_user
from src.models.carts import CartItems, Carts
from src.models.movies import Movies
from src.models.users import User

router = APIRouter()


@router.post("/add/{movie_id}")
async def add_movie_to_cart(
    movie_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cart = await db.scalar(select(Carts).where(Carts.user_id == current_user.id))
    if not cart:
        cart = Carts(user_id=current_user.id)
        db.add(cart)
        await db.flush()

    existing_item = await db.scalar(
        select(CartItems).where(
            CartItems.cart_id == cart.id, CartItems.movie_id == movie_id
        )
    )
    if existing_item:
        raise HTTPException(status_code=400, detail="Movie already in cart.")

    item = CartItems(cart_id=cart.id, movie_id=movie_id)
    db.add(item)
    await db.commit()
    return {"message": "Movie added to cart."}


@router.delete("/remove/{movie_id}")
async def remove_movie_from_cart(
    movie_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cart = await db.scalar(select(Carts).where(Carts.user_id == current_user.id))
    if not cart:
        raise HTTPException(status_code=400, detail="Cart not found.")

    movie = await db.scalar(select(Movies).where(Movies.id == movie_id))

    if not movie:
        raise HTTPException(status_code=400, detail="Movie not found")

    cart_item = await db.scalar(
        select(CartItems).where(
            CartItems.cart_id == cart.id, CartItems.movie_id == movie_id
        )
    )

    if not cart_item:
        raise HTTPException(status_code=400, detail="Movie not in cart")

    await db.delete(cart_item)
    await db.commit()
    return {"message": "Movie removed from cart."}


@router.get("/carts", response_model=list[CartListSchema])
async def get_carts(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    cart = await db.scalar(
        select(Carts)
        .where(Carts.user_id == current_user.id)
        .options(
            selectinload(Carts.items)
            .selectinload(CartItems.movie)
            .selectinload(Movies.genres)
        )
    )

    if not cart:
        raise HTTPException(status_code=400, detail="Cart not found.")

    result = []
    for cart_item in cart.items:
        movie = cart_item.movie

        genres = (
            [genre.name for genre in movie.genres] if movie.genres else ["Not genre."]
        )

        result.append(
            CartListSchema(
                id=movie.id,
                name=movie.name,
                price=movie.price,
                genre=genres,
                year=movie.year,
            )
        )

    return result


@router.delete("/clear_cart")
async def clear_cart(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cart = await db.scalar(select(Carts).where(Carts.user_id == current_user.id))
    if not cart:
        raise HTTPException(status_code=400, detail="Cart not found")

    cart_items_request = await db.execute(
        select(CartItems).where(CartItems.cart_id == cart.id)
    )
    cart_items_response = cart_items_request.scalars()

    for cart_item in cart_items_response:
        await db.delete(cart_item)

    await db.delete(cart)
    await db.commit()

    return {"message": "Cart deleted."}


@router.get("/all_carts")
async def get_all_carts(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    check_group = check_admin(email=user.email, db=db)

    if not check_group:
        raise HTTPException(
            status_code=403, detail="User does not have permission to view all carts."
        )

    all_carts_request = await db.execute(
        select(Carts).options(selectinload(Carts.items))
    )
    all_carts_response = all_carts_request.scalars().all()

    return all_carts_response
