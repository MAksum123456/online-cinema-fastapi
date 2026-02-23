from sqlalchemy import Column, ForeignKey, Table

from src.db.base import Base

user_favorites = Table(
    "user_favorites",
    Base.metadata,
    Column("user_id", ForeignKey("user.id"), primary_key=True),
    Column("movie_id", ForeignKey("movies.id"), primary_key=True),
)

movies_stars = Table(
    "movies_stars",
    Base.metadata,
    Column("movie_id", ForeignKey("movies.id"), primary_key=True),
    Column("star_id", ForeignKey("stars.id"), primary_key=True),
)

movies_genres = Table(
    "movies_genres",
    Base.metadata,
    Column("movie_id", ForeignKey("movies.id"), primary_key=True),
    Column("genre_id", ForeignKey("genres.id"), primary_key=True),
)

movies_directors = Table(
    "movies_directors",
    Base.metadata,
    Column("movie_id", ForeignKey("movies.id"), primary_key=True),
    Column("director_id", ForeignKey("directors.id"), primary_key=True),
)
