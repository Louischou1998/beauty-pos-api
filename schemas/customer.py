from pydantic import BaseModel
from typing import Optional
from decimal import Decimal


class CustomerBase(BaseModel):
    name: str
    phone: str
    email: Optional[str] = None
    level: str = "一般"


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    level: Optional[str] = None


class CustomerTopUp(BaseModel):
    type: str        # "balance" | "points"
    amount: Decimal


class CustomerOut(CustomerBase):
    id: int
    points: int
    balance: Decimal
    total_spent: Decimal
    visits: int

    model_config = {"from_attributes": True}
