from typing import List

from pydantic import BaseModel


class CartListSchema(BaseModel):
    id: int
    name: str
    price: float
    genre: List[str]
    year: int
