from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field


class PaymentStatusEnum(str, Enum):
    PENDING = "PENDING"
    SUCCESSFUL = "successful"
    CANCELED = "canceled"
    REFUNDED = "refunded"


class PaymentConfirmRequest(BaseModel):
    payment_id: int
    client_secret: str


class PaymentItemSchema(BaseModel):
    order_item_id: int
    price_at_payment: Decimal

    class Config:
        from_attributes = True


class PaymentSchema(BaseModel):
    id: int
    order_id: int
    amount: Decimal
    status: PaymentStatusEnum
    created_at: datetime
    external_payment_id: str | None
    payment_items: list[PaymentItemSchema] = Field(default_factory=list)

    class Config:
        from_attributes = True
