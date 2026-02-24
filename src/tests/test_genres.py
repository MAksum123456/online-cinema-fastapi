import pytest
import pytest_asyncio
from httpx import AsyncClient
from httpx._transports.asgi import ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from database import get_db
from main import app
from src.db.base import Base

DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="session")
async def engine():
    engine = create_async_engine(DATABASE_URL, future=True, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def test_db_session(engine):
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with async_session() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def async_client(test_db_session):
    async def override_get_db():
        yield test_db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        yield client


@pytest.mark.asyncio
async def test_create_genre(async_client: AsyncClient):
    payload = {"name": "Action"}
    response = await async_client.post("/genre", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == payload["name"]
    assert "id" in data


@pytest.mark.asyncio
async def test_update_genre(async_client: AsyncClient):
    payload = {"name": "Comedy"}
    res = await async_client.post("/genre", json=payload)
    genre_id = res.json()["id"]

    update_payload = {"id": genre_id, "name": "Romantic Comedy"}
    response = await async_client.put(f"/genre/{genre_id}", json=update_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == update_payload["name"]


@pytest.mark.asyncio
async def test_delete_genre(async_client: AsyncClient):
    payload = {"name": "Horror"}
    res = await async_client.post("/genre", json=payload)
    genre_id = res.json()["id"]

    response = await async_client.delete(f"/genre/{genre_id}")
    assert response.status_code == 200 or response.status_code == 204
