import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.carts import CartItems, Carts
from src.models.movies import Movies
from src.models.users import User


@pytest.mark.asyncio
async def test_add_movie_to_cart(
    async_client: AsyncClient, sample_movie: Movies, auth_headers
):
    response = await async_client.post(f"/add/{sample_movie.id}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["message"] == "Movie added to cart."


@pytest.mark.asyncio
async def test_view_cart(
    async_client: AsyncClient,
    sample_movie: Movies,
    auth_headers,
    test_db_session: AsyncSession,
    sample_user: User,
):
    cart = Carts(user_id=sample_user.id)
    test_db_session.add(cart)
    await test_db_session.flush()
    item = CartItems(cart_id=cart.id, movie_id=sample_movie.id)
    test_db_session.add(item)
    await test_db_session.commit()

    response = await async_client.get("/carts", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert data[0]["name"] == sample_movie.name
    assert data[0]["price"] == sample_movie.price


@pytest.mark.asyncio
async def test_remove_movie_from_cart(
    async_client: AsyncClient,
    sample_movie: Movies,
    auth_headers,
    test_db_session: AsyncSession,
    sample_user: User,
):
    cart = Carts(user_id=sample_user.id)
    test_db_session.add(cart)
    await test_db_session.flush()
    item = CartItems(cart_id=cart.id, movie_id=sample_movie.id)
    test_db_session.add(item)
    await test_db_session.commit()

    response = await async_client.delete(
        f"/remove/{sample_movie.id}", headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Movie removed from cart."


@pytest.mark.asyncio
async def test_clear_cart(
    async_client: AsyncClient,
    sample_movie: Movies,
    auth_headers,
    test_db_session: AsyncSession,
    sample_user: User,
):
    cart = Carts(user_id=sample_user.id)
    test_db_session.add(cart)
    await test_db_session.flush()
    item = CartItems(cart_id=cart.id, movie_id=sample_movie.id)
    test_db_session.add(item)
    await test_db_session.commit()

    response = await async_client.delete("/clear_cart", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["message"] == "Cart deleted."
