"""Public booking portal — no auth required."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta, date as date_type, timezone as dt_timezone
from zoneinfo import ZoneInfo
from database import get_db, settings
from models.booking import Booking, BookingItem, BookingStatus
from models.service import Service, ServiceCategory
from models.staff import Staff
from models.staff_schedule import StaffSchedule
from models.customer import Customer
from ws_manager import manager
import asyncio
import redis as redis_client
from api_errors import api_error
from audit import audit_event

router = APIRouter(prefix="/portal", tags=["portal"])
_redis = redis_client.from_url(settings.redis_url, decode_responses=True)

_APP_TZ = ZoneInfo("Asia/Taipei")
_UTC = ZoneInfo("UTC")


def _utc_naive_to_taipei(dt: datetime) -> datetime:
    return dt.replace(tzinfo=dt_timezone.utc).astimezone(_APP_TZ)


def _taipei_wall_to_utc_naive(dt: datetime) -> datetime:
    """前端傳入的 naive 時間視為 Asia/Taipei 牆鐘，存成 UTC naive。"""
    if dt.tzinfo is not None:
        return dt.astimezone(_UTC).replace(tzinfo=None)
    return dt.replace(tzinfo=_APP_TZ).astimezone(_UTC).replace(tzinfo=None)


def _utc_naive_to_taipei_iso_for_display(dt: datetime) -> str:
    return _utc_naive_to_taipei(dt).isoformat()


def _has_booking_conflict(db: Session, staff_id: int, start_at: datetime, end_at: datetime) -> bool:
    conflict = (
        db.query(BookingItem)
        .join(Booking, BookingItem.booking_id == Booking.id)
        .filter(
            Booking.status != BookingStatus.cancelled,
            BookingItem.staff_id == staff_id,
            BookingItem.start_at < end_at,
            BookingItem.end_at > start_at,
        )
        .first()
    )
    return conflict is not None


def _is_staff_on_shift(db: Session, staff_id: int, start_at: datetime, end_at: datetime) -> bool:
    local_start = _utc_naive_to_taipei(start_at)
    local_end = _utc_naive_to_taipei(end_at)
    work_date = local_start.date()
    row = (
        db.query(StaffSchedule)
        .filter(
            StaffSchedule.staff_id == staff_id,
            StaffSchedule.work_date == work_date,
        )
        .first()
    )
    if not row:
        return True
    start_minutes = local_start.hour * 60 + local_start.minute
    end_minutes = local_end.hour * 60 + local_end.minute
    if row.shift_type == "off":
        return False
    if row.shift_type == "full":
        return 9 * 60 <= start_minutes and end_minutes <= 22 * 60
    if row.shift_type == "morning":
        return 9 * 60 <= start_minutes and end_minutes <= 13 * 60
    if row.shift_type == "afternoon":
        return 13 * 60 <= start_minutes and end_minutes <= 18 * 60
    return True


class PortalBookingRequest(BaseModel):
    customer_name: str
    customer_phone: str
    service_id: int
    staff_id: Optional[int] = None
    start_at: datetime


class PortalBookingResponse(BaseModel):
    booking_id: int
    customer_name: str
    service_name: str
    staff_name: str
    start_at: datetime
    end_at: datetime
    price: float


@router.get("/services")
def list_portal_services(db: Session = Depends(get_db)):
    rows = (
        db.query(Service, ServiceCategory.name)
        .outerjoin(ServiceCategory, Service.category_id == ServiceCategory.id)
        .filter(Service.is_active == 1)
        .order_by(Service.id)
        .all()
    )
    return [
        {
            "id": svc.id,
            "name": svc.name,
            "category_id": svc.category_id,
            "category": cat_name or "未分類",
            "duration": svc.duration,
            "price": svc.price,
        }
        for svc, cat_name in rows
    ]


@router.get("/staff")
def list_staff(db: Session = Depends(get_db)):
    return db.query(Staff).filter(Staff.is_active == 1).all()


@router.get("/available-slots")
def available_slots(service_id: int, staff_id: Optional[int] = None, date: str = None, db: Session = Depends(get_db)):
    service = db.get(Service, service_id)
    if not service:
        raise api_error(404, "SERVICE_NOT_FOUND", "Service not found", {"service_id": service_id})

    if date:
        d = date_type.fromisoformat(date)
    else:
        d = datetime.now(_APP_TZ).date()

    day_start_local = datetime(d.year, d.month, d.day, 9, 0, 0, tzinfo=_APP_TZ)
    day_end_local = datetime(d.year, d.month, d.day, 21, 0, 0, tzinfo=_APP_TZ)
    start_utc_naive = day_start_local.astimezone(_UTC).replace(tzinfo=None)
    end_utc_naive = day_end_local.astimezone(_UTC).replace(tzinfo=None)

    slots_utc = []
    current = start_utc_naive
    duration = int(service.duration)
    while current + timedelta(minutes=duration) <= end_utc_naive:
        slots_utc.append(current)
        current += timedelta(minutes=30)

    if staff_id:
        target_staff_ids = [staff_id]
    else:
        target_staff_ids = [s.id for s in db.query(Staff).filter(Staff.is_active == 1).all()]

    def is_free(slot: datetime) -> bool:
        end = slot + timedelta(minutes=duration)
        if not target_staff_ids:
            return False
        return any(_is_staff_on_shift(db, sid, slot, end) and not _has_booking_conflict(db, sid, slot, end) for sid in target_staff_ids)

    return [{"time": _utc_naive_to_taipei_iso_for_display(s), "available": is_free(s)} for s in slots_utc]


@router.post("/book", response_model=PortalBookingResponse)
async def portal_book(payload: PortalBookingRequest, db: Session = Depends(get_db)):
    service = db.get(Service, payload.service_id)
    if not service:
        raise api_error(404, "SERVICE_NOT_FOUND", "Service not found", {"service_id": payload.service_id})

    # 自動選技師（若未指定）
    staff_id = payload.staff_id
    if not staff_id:
        staff = db.query(Staff).filter(Staff.is_active == 1).first()
        if staff:
            staff_id = staff.id

    if not staff_id:
        raise api_error(400, "NO_AVAILABLE_STAFF", "No available staff")
    staff = db.get(Staff, staff_id)
    if not staff or staff.is_active != 1:
        raise api_error(400, "STAFF_NOT_AVAILABLE", "Staff not available", {"staff_id": staff_id})
    start_at = _taipei_wall_to_utc_naive(payload.start_at)
    end_at = start_at + timedelta(minutes=int(service.duration))
    if not _is_staff_on_shift(db, staff_id, start_at, end_at):
        raise api_error(
            409,
            "STAFF_OFF_SHIFT",
            "Staff is off-shift for selected time",
            {"staff_id": staff_id, "start_at": start_at.isoformat()},
        )

    # 找或建立顧客
    customer = db.query(Customer).filter(Customer.phone == payload.customer_phone).first()
    if not customer:
        customer = Customer(name=payload.customer_name, phone=payload.customer_phone)
        db.add(customer)
        db.flush()

    lock_key = f"portal-slot:{staff_id}:{start_at.isoformat()}"
    with _redis.lock(lock_key, timeout=10):
        if _has_booking_conflict(db, staff_id, start_at, end_at):
            raise api_error(
                409,
                "BOOKING_CONFLICT",
                "Selected time slot is no longer available",
                {"staff_id": staff_id, "start_at": start_at.isoformat()},
            )

        booking = Booking(customer_id=customer.id, status=BookingStatus.confirmed)
        db.add(booking)
        db.flush()

        item = BookingItem(
            booking_id=booking.id,
            service_id=service.id,
            staff_id=staff_id,
            start_at=start_at,
            end_at=end_at,
            price=service.price,
        )
        db.add(item)
    db.commit()

    asyncio.create_task(manager.broadcast("booking_created", {"booking_id": booking.id, "source": "portal"}))
    audit_event(
        "portal.book",
        actor_id="public",
        booking_id=booking.id,
        customer_phone=payload.customer_phone,
        service_id=service.id,
        staff_id=staff_id,
        start_at=start_at.isoformat(),
    )

    return PortalBookingResponse(
        booking_id=booking.id,
        customer_name=payload.customer_name,
        service_name=service.name,
        staff_name=staff.name if staff else "待指派",
        start_at=start_at,
        end_at=end_at,
        price=float(service.price),
    )
