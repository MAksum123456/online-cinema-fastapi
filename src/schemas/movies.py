import decimal
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel


class MovieCertificationSchema(BaseModel):
    id: int
    name: str


class GenreSchema(BaseModel):
    id: int
    name: str


class DirectorSchema(BaseModel):
    id: int
    name: str


class StarResponseSchema(BaseModel):
    id: int
    name: str


class MovieListResponseSchema(BaseModel):
    id: int
    name: str
    imdb: float
    description: str
    time: int


class GenreAndCountMovieSchema(BaseModel):
    id: int
    name: str
    movies: int


class GenreDetailSchema(BaseModel):
    id: int
    name: str
    movies: List[MovieListResponseSchema]


class CreateGenreSchema(BaseModel):
    name: str


class UpdateGenreSchema(BaseModel):
    id: int
    name: str


class MovieDetailsResponseSchema(BaseModel):
    id: int
    uuid: UUID
    name: str
    year: int
    time: int
    imdb: float
    votes: int
    meta_score: Optional[float]
    gross: Optional[float]
    description: str
    price: decimal.Decimal

    certification: MovieCertificationSchema
    genres: List["GenreSchema"]
    directors: List["DirectorSchema"]
    stars: List["StarResponseSchema"]


class CreateCommentSchema(BaseModel):
    movie_id: int
    content: str


class CreateMovieSchema(BaseModel):
    name: str
    uuid: UUID
    year: int
    time: int
    imdb: float
    votes: int
    meta_score: Optional[float]
    gross: Optional[float]
    description: str
    price: decimal.Decimal
    certification_id: int
    genre_ids: List[int] = []
    director_ids: List[int] = []
    star_ids: List[int] = []


class UpdateMovieSchema(BaseModel):
    name: Optional[str] = None
    uuid: Optional[UUID] = None
    year: Optional[int] = None
    time: Optional[int] = None
    imdb: Optional[float] = None
    votes: Optional[int] = None
    meta_score: Optional[float] = None
    gross: Optional[float] = None
    description: Optional[str] = None
    price: Optional[decimal.Decimal] = None
    certification_id: Optional[int] = None
    genre_ids: Optional[List[int]] = None
    director_ids: Optional[List[int]] = None
    star_ids: Optional[List[int]] = None
