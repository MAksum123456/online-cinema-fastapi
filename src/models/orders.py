import enum
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import DECIMAL, Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base


class OrderStatusEnum(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    CANCELED = "canceled"


class Orders(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc), nullable=False
    )
    status: Mapped[OrderStatusEnum] = mapped_column(
        Enum(OrderStatusEnum, name="order_status_enum"),
        default=OrderStatusEnum.PENDING,
        nullable=False,
    )
    total_amount: Mapped[Decimal] = mapped_column(DECIMAL(10, 2), nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="orders")
    items: Mapped[list["OrderItems"]] = relationship(
        "OrderItems", back_populates="order"
    )
    payments: Mapped[list["Payments"]] = relationship(
        "Payments", back_populates="order", cascade="all, delete-orphan"
    )


class OrderItems(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id"), nullable=False)
    price_at_order: Mapped[Decimal] = mapped_column(DECIMAL(10, 2), nullable=False)

    order: Mapped["Orders"] = relationship("Orders", back_populates="items")
    movie: Mapped["Movies"] = relationship("Movies", back_populates="order_items")

    payment_items: Mapped["PaymentItems"] = relationship(
        "PaymentItems", back_populates="order_items"
    )
