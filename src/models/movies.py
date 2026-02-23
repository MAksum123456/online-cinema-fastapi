import decimal
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import DECIMAL, CheckConstraint, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base
from src.models.base import (
    movies_directors,
    movies_genres,
    movies_stars,
    user_favorites,
)


class Movies(Base):
    __tablename__ = "movies"

    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[UUID] = mapped_column(nullable=False)
    name: Mapped[str] = mapped_column(String(250), nullable=False)
    year: Mapped[int] = mapped_column(nullable=False)
    time: Mapped[int] = mapped_column(nullable=False)
    imdb: Mapped[float] = mapped_column(nullable=False)
    votes: Mapped[int] = mapped_column(nullable=False)
    meta_score: Mapped[float] = mapped_column(nullable=True)
    gross: Mapped[float] = mapped_column(nullable=True)
    description: Mapped[str] = mapped_column(nullable=False)
    price: Mapped[decimal.Decimal] = mapped_column(DECIMAL(10, 2), nullable=True)
    certification_id: Mapped[int] = mapped_column(
        ForeignKey("certifications.id"), nullable=False
    )
    certification: Mapped["Certifications"] = relationship(back_populates="movies")

    stars: Mapped[list["Stars"]] = relationship(
        secondary=movies_stars, back_populates="movies"
    )
    genres: Mapped[list["Genres"]] = relationship(
        secondary=movies_genres, back_populates="movies"
    )
    directors: Mapped[list["Directors"]] = relationship(
        secondary=movies_directors, back_populates="movies"
    )
    likes: Mapped[list["MovieLike"]] = relationship(back_populates="movie")
    comments: Mapped[list["MovieComment"]] = relationship(back_populates="movie")
    favorited_by: Mapped[list["User"]] = relationship(
        "User", secondary=user_favorites, back_populates="favorite_movies"
    )
    ratings: Mapped[list["MovieRating"]] = relationship(
        "MovieRating", back_populates="movie"
    )
    items: Mapped[list["CartItems"]] = relationship("CartItems", back_populates="movie")
    order_items: Mapped[list["OrderItems"]] = relationship(
        "OrderItems", back_populates="movie"
    )
    is_available: Mapped[bool] = mapped_column(nullable=False, default=True)


class Certifications(Base):
    __tablename__ = "certifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(nullable=False)

    movies: Mapped[list["Movies"]] = relationship(back_populates="certification")


class Stars(Base):
    __tablename__ = "stars"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    movies: Mapped[list["Movies"]] = relationship(
        secondary=movies_stars, back_populates="stars"
    )


class Genres(Base):
    __tablename__ = "genres"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    movies: Mapped[list["Movies"]] = relationship(
        secondary=movies_genres, back_populates="genres"
    )


class Directors(Base):
    __tablename__ = "directors"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    movies: Mapped[list["Movies"]] = relationship(
        secondary=movies_directors, back_populates="directors"
    )


class MovieLike(Base):
    __tablename__ = "movie_likes"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id"), nullable=False)

    user: Mapped["User"] = relationship("User")
    movie: Mapped["Movies"] = relationship("Movies", back_populates="likes")


class MovieComment(Base):
    __tablename__ = "movie_comments"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))
    user: Mapped["User"] = relationship("User", back_populates="comments")
    movie: Mapped["Movies"] = relationship("Movies", back_populates="comments")


class MovieRating(Base):
    __tablename__ = "movie_ratings"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id"), nullable=False)
    rating: Mapped[int] = mapped_column(nullable=False)

    __table_args__ = (
        CheckConstraint("rating >= 1 AND rating <= 10", name="rating_range"),
    )

    user: Mapped["User"] = relationship("User")
    movie: Mapped["Movies"] = relationship("Movies")
