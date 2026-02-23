from uuid import uuid4

import pytest
from httpx import AsyncClient

from src.models.movies import Certifications


@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_create_movie(
    async_client_with_db: AsyncClient, test_certification: Certifications
):
    payload = {
        "uuid": str(uuid4()),
        "name": "Test Movie",
        "year": 2025,
        "time": 120,
        "imdb": 8.5,
        "votes": 1000,
        "meta_score": 85.0,
        "gross": 1000000.0,
        "description": "A test movie",
        "price": 9.99,
        "certification_id": test_certification.id,
        "stars_ids": [],
        "genres_ids": [],
        "directors_ids": [],
    }

    response = await async_client_with_db.post("/movie", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert data["name"] == payload["name"]


@pytest.mark.asyncio
async def test_list_movies(async_client_with_db: AsyncClient):
    response = await async_client_with_db.get("/movies")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_get_movie_by_id(
    async_client_with_db: AsyncClient, test_certification: Certifications
):
    payload = {
        "uuid": str(uuid4()),
        "name": "GetByID Movie",
        "year": 2025,
        "time": 100,
        "imdb": 7.0,
        "votes": 500,
        "meta_score": 70.0,
        "gross": 500000.0,
        "description": "Movie for get by id",
        "price": 5.99,
        "certification_id": test_certification.id,
        "stars_ids": [],
        "genres_ids": [],
        "directors_ids": [],
    }
    create_resp = await async_client_with_db.post("/movie", json=payload)
    movie_id = create_resp.json()["id"]

    response = await async_client_with_db.get(f"/movie/{movie_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == movie_id
    assert data["name"] == payload["name"]


@pytest.mark.asyncio
async def test_delete_movie(
    async_client_with_db: AsyncClient, test_certification: Certifications
):
    payload = {
        "uuid": str(uuid4()),
        "name": "Delete Movie",
        "year": 2025,
        "time": 90,
        "imdb": 6.5,
        "votes": 300,
        "meta_score": 60.0,
        "gross": 200000.0,
        "description": "Movie to delete",
        "price": 4.99,
        "certification_id": test_certification.id,
        "stars_ids": [],
        "genres_ids": [],
        "directors_ids": [],
    }
    create_resp = await async_client_with_db.post("/movie", json=payload)
    assert create_resp.status_code == 200
    movie_id = create_resp.json()["id"]

    response = await async_client_with_db.delete(f"/movie/{movie_id}")
    assert response.status_code == 200

    data = response.json()

    assert "message" in data
    assert "deleted" in data["message"].lower()
