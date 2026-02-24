from enum import Enum
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from schemas.movies import CreateMovieSchema, UpdateGenreSchema, UpdateMovieSchema
from src.models.movies import Directors, Genres, Movies, Stars


class SortOrder(str, Enum):
    asc = "asc"
    desc = "desc"


async def get_movies(
    limit: int,
    offset: int,
    db: AsyncSession,
    min_year: Optional[int] = None,
    max_year: Optional[int] = None,
    min_imdb: Optional[float] = None,
    max_imdb: Optional[float] = None,
    year_sort: Optional[SortOrder] = None,
    price_sort: Optional[SortOrder] = None,
    meta_score_sort: Optional[SortOrder] = None,
    movie_name: Optional[str] = None,
    description_search: Optional[str] = None,
    actor_name_search: Optional[str] = None,
    director_name_search: Optional[str] = None,
):
    query = select(Movies).limit(limit).offset(offset)

    if min_year is not None:
        query = query.where(Movies.year >= min_year)

    if max_year is not None:
        query = query.where(Movies.year <= max_year)

    if min_imdb is not None:
        query = query.where(Movies.imdb >= min_imdb)

    if max_imdb is not None:
        query = query.where(Movies.imdb <= max_imdb)

    order_clauses = []
    if year_sort:
        order_clauses.append(
            Movies.year.desc() if year_sort == SortOrder.desc else Movies.year
        )
    if price_sort:
        order_clauses.append(
            Movies.price.desc() if price_sort == SortOrder.desc else Movies.price.asc()
        )
    if meta_score_sort:
        order_clauses.append(
            Movies.meta_score.desc()
            if meta_score_sort == SortOrder.desc
            else Movies.meta_score.asc()
        )

    if order_clauses:
        query = query.order_by(*order_clauses)

    if movie_name is not None:
        query = query.where(Movies.name.ilike(f"%{movie_name}%"))

    if description_search is not None:
        query = query.where(Movies.description.ilike(f"%{description_search}%"))

    if actor_name_search is not None:
        query = query.join(Movies.stars).where(
            Stars.name.ilike(f"%{actor_name_search}%")
        )

    if director_name_search is not None:
        query = query.join(Movies.directors).where(
            Directors.name.ilike(f"%{director_name_search}%")
        )

    result = await db.execute(
        query.options(joinedload(Movies.directors), joinedload(Movies.stars))
    )
    movies = result.unique().scalars().all()
    return movies


async def get_movie(movie_id: int, db: AsyncSession):
    request = await db.execute(
        select(Movies)
        .options(
            joinedload(Movies.certification),
            joinedload(Movies.genres),
            joinedload(Movies.directors),
            joinedload(Movies.stars),
        )
        .where(Movies.id == movie_id)
    )

    movie = request.unique().scalar_one_or_none()
    return movie


async def create_movie(movie_data: CreateMovieSchema, db: AsyncSession):
    new_movie = Movies(
        uuid=movie_data.uuid,
        name=movie_data.name,
        year=movie_data.year,
        time=movie_data.time,
        imdb=movie_data.imdb,
        votes=movie_data.votes,
        meta_score=movie_data.meta_score,
        gross=movie_data.gross,
        description=movie_data.description,
        price=movie_data.price,
        certification_id=movie_data.certification_id,
    )

    stars_list = []
    if movie_data.star_ids:
        result = await db.execute(
            select(Stars).where(Stars.id.in_(movie_data.star_ids))
        )
        stars_list = result.scalars().all()
        new_movie.stars = stars_list

    genres_list = []
    if movie_data.genre_ids:
        result = await db.execute(
            select(Genres).where(Genres.id.in_(movie_data.genre_ids))
        )
        genres_list = result.scalars().all()
        new_movie.genres = genres_list

    directors_list = []
    if movie_data.director_ids:
        result = await db.execute(
            select(Directors).where(Directors.id.in_(movie_data.director_ids))
        )
        directors_list = result.scalars().all()
        new_movie.directors = directors_list

    db.add(new_movie)
    await db.commit()
    await db.refresh(new_movie)

    return new_movie


async def update_movie(movie_id: int, new_movie: UpdateMovieSchema, db: AsyncSession):
    result = await db.execute(
        select(Movies)
        .options(
            selectinload(Movies.certification),
            selectinload(Movies.stars),
            selectinload(Movies.genres),
            selectinload(Movies.directors),
        )
        .where(Movies.id == movie_id)
    )
    movie_to_update = result.scalar_one_or_none()

    if not movie_to_update:
        raise HTTPException(status_code=404, detail="Movie not found")

    if new_movie.uuid:
        movie_to_update.uuid = new_movie.uuid
    if new_movie.name:
        movie_to_update.name = new_movie.name
    if new_movie.year:
        movie_to_update.year = new_movie.year
    if new_movie.time:
        movie_to_update.time = new_movie.time
    if new_movie.imdb:
        movie_to_update.imdb = new_movie.imdb
    if new_movie.votes:
        movie_to_update.votes = new_movie.votes
    if new_movie.meta_score:
        movie_to_update.meta_score = new_movie.meta_score
    if new_movie.gross:
        movie_to_update.gross = new_movie.gross
    if new_movie.description:
        movie_to_update.description = new_movie.description
    if new_movie.price:
        movie_to_update.price = new_movie.price
    if new_movie.certification_id:
        movie_to_update.certification_id = new_movie.certification_id

    if new_movie.star_ids:
        result = await db.execute(select(Stars).where(Stars.id.in_(new_movie.star_ids)))
        movie_to_update.stars = result.scalars().all()

    if new_movie.genre_ids:
        result = await db.execute(
            select(Genres).where(Genres.id.in_(new_movie.genre_ids))
        )
        movie_to_update.genres = result.scalars().all()

    if new_movie.director_ids:
        result = await db.execute(
            select(Directors).where(Directors.id.in_(new_movie.director_ids))
        )
        movie_to_update.directors = result.scalars().all()

    db.add(movie_to_update)
    await db.commit()
    await db.refresh(movie_to_update)

    return movie_to_update


async def destroy_movie(movie_id: int, db: AsyncSession):
    movie = await get_movie(movie_id, db)
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")
    await db.delete(movie)
    await db.commit()
    return True


async def put_genre(genre_data: UpdateGenreSchema, db: AsyncSession):
    result = await db.execute(select(Genres).where(Genres.id == genre_data.id))
    genre = result.scalar_one_or_none()

    if not genre:
        raise HTTPException(status_code=404, detail="Genre not found")

    genre.name = genre_data.name

    db.add(genre)
    await db.commit()
    await db.refresh(genre)

    return genre
