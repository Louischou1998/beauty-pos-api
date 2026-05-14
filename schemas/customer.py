from pydantic import BaseModel
from typing import Optional
from decimal import Decimal
from datetime import date, datetime


class CustomerBase(BaseModel):
    name: str
    phone: str
    email: Optional[str] = None
    level: str = "一般"


class CustomerCreate(CustomerBase):
    allergy_info: Optional[str] = ""
    preferred_staff_id: Optional[int] = None
    revisit_days: Optional[int] = 30
    birthday: Optional[date] = None


class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    level: Optional[str] = None
    allergy_info: Optional[str] = None
    preferred_staff_id: Optional[int] = None
    revisit_days: Optional[int] = None
    birthday: Optional[date] = None


class CustomerTopUp(BaseModel):
    type: str        # "balance" | "points"
    amount: Decimal


class CustomerOut(CustomerBase):
    id: int
    points: int
    balance: Decimal
    total_spent: Decimal
    visits: int
    allergy_info: Optional[str] = ""
    preferred_staff_id: Optional[int] = None
    revisit_days: Optional[int] = 30
    last_visit_at: Optional[datetime] = None
    birthday: Optional[date] = None

    model_config = {"from_attributes": True}
