import decimal
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from database import get_db
from main import app
from security.password import (
    hash_password,
)
from src.db.base import Base
from src.models.carts import CartItems, Carts
from src.models.movies import Certifications, Movies
from src.models.payments import Payments, StatusEnum
from src.models.users import User, UserGroup

DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def engine():
    engine = create_async_engine(DATABASE_URL, future=True, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def test_db_session(engine):
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with async_session() as session:
        yield session


@pytest_asyncio.fixture
async def async_client(test_db_session):
    app.dependency_overrides[get_db] = lambda: test_db_session
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        yield client
    app.dependency_overrides.pop(get_db, None)


@pytest_asyncio.fixture
async def sample_user(test_db_session: AsyncSession):
    result = await test_db_session.execute(
        select(UserGroup).where(UserGroup.name == "USER")
    )
    group = result.scalars().first()
    if not group:
        group = UserGroup(name="USER")
        test_db_session.add(group)
        await test_db_session.commit()
        await test_db_session.refresh(group)

    user = User(
        email="test@example.com",
        hashed_password=hash_password("password123"),
        is_active=True,
        group_id=group.id,
    )
    test_db_session.add(user)
    await test_db_session.commit()
    await test_db_session.refresh(user)
    user._plain_password = "password123"
    return user


@pytest_asyncio.fixture
async def auth_headers(async_client: AsyncClient, sample_user: User):
    response = await async_client.post(
        "/login",
        json={"email": sample_user.email, "password": sample_user._plain_password},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def sample_movie(test_db_session: AsyncSession) -> Movies:
    certification = Certifications(name="Certification")
    test_db_session.add(certification)
    await test_db_session.commit()
    await test_db_session.refresh(certification)

    movie = Movies(
        uuid=uuid.uuid4(),
        name="Test Movie",
        year=2023,
        time=120,
        imdb=8.5,
        votes=1000,
        meta_score=75.0,
        gross=5000000.0,
        description="Test description",
        price=decimal.Decimal("10.00"),
        certification_id=certification.id,
    )
    test_db_session.add(movie)
    await test_db_session.commit()
    await test_db_session.refresh(movie)
    return movie


@pytest.mark.asyncio
async def test_create_order(
    async_client, sample_user, sample_movie, auth_headers, test_db_session
):
    cart = Carts(user_id=sample_user.id)
    test_db_session.add(cart)
    await test_db_session.flush()
    item = CartItems(cart_id=cart.id, movie_id=sample_movie.id)
    test_db_session.add(item)
    await test_db_session.commit()

    response = await async_client.post(
        "/order", json={"movies_ids": [sample_movie.id]}, headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()

    assert "id" in data
    assert data["user_id"] == sample_user.id
    assert data["status"] == "pending"
    assert data["total_amount"] == float(sample_movie.price)


@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_get_my_orders(
    async_client: AsyncClient,
    sample_user,
    sample_movie,
    auth_headers,
    test_db_session: AsyncSession,
):
    cart = Carts(user_id=sample_user.id)
    test_db_session.add(cart)
    await test_db_session.flush()
    item = CartItems(cart_id=cart.id, movie_id=sample_movie.id)
    test_db_session.add(item)
    await test_db_session.commit()

    response = await async_client.post(
        "/order", json={"movies_ids": [sample_movie.id]}, headers=auth_headers
    )
    assert response.status_code == 200
    order_data = response.json()
    order_id = order_data["id"]

    payment = Payments(
        order_id=order_id,
        user_id=sample_user.id,
        amount=float(sample_movie.price),
        status=StatusEnum.SUCCESSFUL,
    )
    test_db_session.add(payment)
    await test_db_session.commit()

    response = await async_client.get("/my", headers=auth_headers)
    assert response.status_code == 200
    movies = response.json()
    assert isinstance(movies, list)
    assert len(movies) >= 1
    assert movies[0]["id"] == sample_movie.id


@pytest.mark.asyncio
async def test_cancel_order(
    async_client, sample_user, sample_movie, auth_headers, test_db_session
):
    cart = Carts(user_id=sample_user.id)
    test_db_session.add(cart)
    await test_db_session.flush()
    item = CartItems(cart_id=cart.id, movie_id=sample_movie.id)
    test_db_session.add(item)
    await test_db_session.commit()

    resp = await async_client.post(
        "/order", json={"movies_ids": [sample_movie.id]}, headers=auth_headers
    )
    assert resp.status_code == 200
    order_id = resp.json()["id"]

    cancel_resp = await async_client.patch(f"/order/{order_id}", headers=auth_headers)
    assert cancel_resp.status_code == 200
    assert cancel_resp.json() == "canceled"

    repeat_resp = await async_client.patch(f"/order/{order_id}", headers=auth_headers)
    assert repeat_resp.status_code == 409
    assert repeat_resp.json()["detail"] == "Order canceled"
