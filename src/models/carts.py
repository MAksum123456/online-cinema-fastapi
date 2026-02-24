from datetime import UTC, datetime
from typing import List

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base

__table_args__ = (UniqueConstraint("cart_id", "movie_id", name="uix_cart_movie"),)


class Carts(Base):
    __tablename__ = "carts"

    id: Mapped[int] = mapped_column(primary_key=True, nullable=False)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("user.id"), nullable=False, unique=True
    )

    user: Mapped["User"] = relationship("User", back_populates="carts")
    items: Mapped[List["CartItems"]] = relationship("CartItems", back_populates="cart")


class CartItems(Base):
    __tablename__ = "cart_items"

    id: Mapped[int] = mapped_column(primary_key=True, nullable=False)

    cart_id: Mapped[int] = mapped_column(ForeignKey("carts.id"), nullable=False)
    cart: Mapped["Carts"] = relationship("Carts", back_populates="items")

    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id"), nullable=False)
    movie: Mapped["Movies"] = relationship("Movies", back_populates="items")

    added_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
