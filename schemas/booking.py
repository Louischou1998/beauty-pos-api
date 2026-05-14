from pydantic import BaseModel, field_validator
from typing import List, Optional
from datetime import datetime, timezone
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

    # DB 存 UTC naive，加上時區後綴讓前端 dayjs 正確解析
    @field_validator('start_at', 'end_at', mode='before')
    @classmethod
    def ensure_utc(cls, v):
        if isinstance(v, datetime) and v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v

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
