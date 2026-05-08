from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from decimal import Decimal
from models.booking import BookingStatus


class BookingItemCreate(BaseModel):
    service_id: int
    staff_id: int
    start_at: datetime
    price: Decimal


class BookingCreate(BaseModel):
    customer_id: int
    note: Optional[str] = None
    items: List[BookingItemCreate]


class BookingItemOut(BaseModel):
    id: int
    service_id: int
    staff_id: int
    start_at: datetime
    end_at: datetime
    price: Decimal

    model_config = {"from_attributes": True}


class BookingOut(BaseModel):
    id: int
    customer_id: int
    status: BookingStatus
    created_at: datetime
    note: Optional[str]
    items: List[BookingItemOut]

    model_config = {"from_attributes": True}


class BookingStatusUpdate(BaseModel):
    status: BookingStatus
