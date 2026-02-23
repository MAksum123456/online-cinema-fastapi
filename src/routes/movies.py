from typing import List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.params import Depends
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from crud.movies import (
    SortOrder,
    create_movie,
    destroy_movie,
    get_movie,
    get_movies,
    put_genre,
    update_movie,
)
from database import get_db
from schemas.auth import MessageSchema
from schemas.movies import (
    CreateCommentSchema,
    CreateGenreSchema,
    CreateMovieSchema,
    GenreAndCountMovieSchema,
    GenreDetailSchema,
    MovieDetailsResponseSchema,
    MovieListResponseSchema,
    UpdateGenreSchema,
    UpdateMovieSchema,
)
from services.auth import oauth2_scheme
from services.users import get_current_user
from src.models.base import user_favorites
from src.models.movies import (
    Directors,
    Genres,
    MovieComment,
    MovieLike,
    MovieRating,
    Movies,
    Stars,
)
from src.models.orders import OrderItems, Orders
from src.models.payments import Payments, StatusEnum
from src.models.users import User

router = APIRouter()


@router.get("/movies", response_model=List[MovieListResponseSchema])
async def list_movies(
    min_year: Optional[int] = None,
    max_year: Optional[int] = None,
    min_imdb: Optional[float] = None,
    max_imdb: Optional[float] = None,
    movie_name: Optional[str] = None,
    year_sort: Optional[SortOrder] = None,
    price_sort: Optional[SortOrder] = None,
    meta_score_sort: Optional[SortOrder] = None,
    description_search: Optional[str] = None,
    actor_name_search: Optional[str] = None,
    director_name_search: Optional[str] = None,
    limit: int = 10,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    movies = await get_movies(
        min_year=min_year,
        max_year=max_year,
        min_imdb=min_imdb,
        max_imdb=max_imdb,
        year_sort=year_sort,
        price_sort=price_sort,
        meta_score_sort=meta_score_sort,
        movie_name=movie_name,
        description_search=description_search,
        actor_name_search=actor_name_search,
        director_name_search=director_name_search,
        limit=limit,
        offset=offset,
        db=db,
    )

    return movies


@router.get("/movie/{movie_id}", response_model=MovieDetailsResponseSchema)
async def detail_movie(movie_id: int, db: AsyncSession = Depends(get_db)):
    movies = await get_movie(movie_id=movie_id, db=db)

    return movies


@router.post("/movie", response_model=MovieListResponseSchema)
async def add_movie(movie_data: CreateMovieSchema, db: AsyncSession = Depends(get_db)):
    return await create_movie(movie_data=movie_data, db=db)


@router.put("/movie/{movie_id}", response_model=MovieDetailsResponseSchema)
async def put_movie(
    movie_id: int, new_movie: UpdateMovieSchema, db: AsyncSession = Depends(get_db)
):
    return await update_movie(movie_id=movie_id, new_movie=new_movie, db=db)


@router.delete("/movie/{movie_id}", response_model=MessageSchema)
async def delete_movie(movie_id: int, db: AsyncSession = Depends(get_db)):
    await destroy_movie(movie_id=movie_id, db=db)
    return MessageSchema(message="Movie deleted")


@router.get("/genres", response_model=List[GenreAndCountMovieSchema])
async def list_genres(db: AsyncSession = Depends(get_db)):
    query = (
        select(Genres.id, Genres.name, func.count(Movies.id).label("movies_count"))
        .join(Movies.genres)
        .group_by(Genres.id)
    )
    result = await db.execute(query)
    genres = result.all()

    if not genres:
        raise HTTPException(status_code=404, detail="Stars not found")

    return [GenreAndCountMovieSchema(id=g[0], name=g[1], movies=g[2]) for g in genres]


@router.get("/genre/{genre_id}", response_model=GenreDetailSchema)
async def detail_genre(genre_id: int, db: AsyncSession = Depends(get_db)):
    request = await db.execute(
        select(Genres).where(Genres.id == genre_id).options(joinedload(Genres.movies))
    )
    result = request.unique().scalar_one_or_none()

    return result


@router.post("/genre", response_model=GenreDetailSchema)
async def add_genre(genre_data: CreateGenreSchema, db: AsyncSession = Depends(get_db)):
    new_genre = Genres(name=genre_data.name)
    db.add(new_genre)
    await db.commit()
    await db.refresh(new_genre)
    return await detail_genre(genre_id=new_genre.id, db=db)


@router.put("/genre/{genre_id}", response_model=GenreDetailSchema)
async def update_genre(
    genre_data: UpdateGenreSchema, db: AsyncSession = Depends(get_db)
):
    updated_genre = await put_genre(genre_data=genre_data, db=db)
    return await detail_genre(genre_id=updated_genre.id, db=db)


@router.delete("/genre/{genre_id}", response_model=MessageSchema)
async def delete_genre(genre_id: int, db: AsyncSession = Depends(get_db)):
    genre_request = await db.execute(select(Genres).where(Genres.id == genre_id))
    result = genre_request.scalar_one_or_none()

    if not result:
        raise HTTPException(status_code=404, detail="Genre not found")

    await db.delete(result)
    await db.commit()

    return MessageSchema(message="Genre deleted")


@router.post("/like_movie", response_model=MessageSchema)
async def like_movie(
    movie_id: int,
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
):
    user = await get_current_user(token=token, db=db)
    result = await db.execute(select(Movies).where(Movies.id == movie_id))
    movie = result.scalars().first()

    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")

    like = MovieLike(user_id=user.id, movie_id=movie.id)

    try:
        db.add(like)
        await db.commit()

    except IntegrityError:
        raise HTTPException(status_code=409, detail="User has already liked this movie")

    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Database error")

    return MessageSchema(message="Movie liked")


@router.post("/add_comment", response_model=MessageSchema)
async def add_comment(
    movie_data: CreateCommentSchema,
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
):
    user = await get_current_user(token=token, db=db)
    result = await db.execute(select(Movies).where(Movies.id == movie_data.movie_id))
    movie = result.scalars().first()

    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")

    comment = MovieComment(
        user_id=user.id, movie_id=movie.id, content=movie_data.content
    )

    db.add(comment)
    await db.commit()
    return MessageSchema(message="Comment added")


@router.post("/favorite_movie", response_model=MessageSchema)
async def add_favourite_movie(
    movie_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User)
        .options(selectinload(User.favorite_movies))
        .where(User.id == current_user.id)
    )
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    result = await db.execute(select(Movies).where(Movies.id == movie_id))
    movie = result.scalars().first()
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")

    if movie in user.favorite_movies:
        return {"detail": "Movie already in favorites"}

    user.favorite_movies.append(movie)
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return MessageSchema(message="Movie add to favorites")


@router.get("/favorites", response_model=List[MovieListResponseSchema])
async def get_favorites(
    limit: int = 10,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
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
    query = (
        select(Movies)
        .join(user_favorites, Movies.id == user_favorites.c.movie_id)
        .where(user_favorites.c.user_id == current_user.id)
        .options(
            selectinload(Movies.stars),
            selectinload(Movies.genres),
            selectinload(Movies.directors),
        )
        .offset(offset)
        .limit(limit)
    )

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

    result = await db.execute(query)
    movies = result.scalars().all()

    return movies


@router.delete("/delete_favorite/{movie_id}", response_model=MessageSchema)
async def delete_movie(
    movie_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User)
        .options(selectinload(User.favorite_movies))
        .where(User.id == current_user.id)
    )
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    result = await db.execute(select(Movies).where(Movies.id == movie_id))
    movie = result.scalars().first()

    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")

    if movie not in user.favorite_movies:
        raise HTTPException(status_code=404, detail="Movie not in favorites")

    user.favorite_movies.remove(movie)
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return MessageSchema(message="Movie deleted")


@router.post("/film_review", response_model=MessageSchema)
async def film_review(
    movie_id: int,
    rating: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    request = await db.execute(select(Movies).where(Movies.id == movie_id))
    movie = request.scalar_one_or_none()

    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")

    rating = MovieRating(user_id=current_user.id, movie_id=movie.id, rating=rating)

    db.add(rating)
    await db.commit()

    return MessageSchema(message="Movie reviewed")


@router.get("/my")
async def my_movies(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    query = await db.execute(
        select(Movies)
        .join(OrderItems, OrderItems.movie_id == Movies.id)
        .join(Orders, Orders.id == OrderItems.order_id)
        .join(Payments, Payments.order_id == Orders.id)
        .where(Orders.user_id == user.id, Payments.status == StatusEnum.SUCCESSFUL)
    )
    result = query.scalars().all()

    return result
