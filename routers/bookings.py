from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import timedelta
from database import get_db, settings
from models.booking import Booking, BookingItem, BookingStatus
from models.service import Service
from models.staff_schedule import StaffSchedule
from schemas.booking import BookingCreate, BookingOut, BookingStatusUpdate
from typing import List
import redis as redis_client
from redis.exceptions import RedisError
from auth import require_auth
from api_errors import api_error
from audit import audit_event

router = APIRouter(prefix="/bookings", tags=["bookings"])

_redis = redis_client.from_url(settings.redis_url, decode_responses=True)
BUSINESS_OPEN_MINUTES = 9 * 60
BUSINESS_CLOSE_MINUTES = 22 * 60


def _check_conflict(db: Session, staff_id: int, start_at, end_at, exclude_item_id=None):
    q = db.query(BookingItem).filter(
        BookingItem.staff_id == staff_id,
        BookingItem.start_at < end_at,
        BookingItem.end_at > start_at,
    )
    if exclude_item_id:
        q = q.filter(BookingItem.id != exclude_item_id)
    return q.first()


def _add_booking_item_with_conflict_check(db: Session, booking_id: int, item, end_at):
    if _check_conflict(db, item.staff_id, item.start_at, end_at):
        raise api_error(
            409,
            "BOOKING_CONFLICT",
            "Staff has a booking conflict",
            {"staff_id": item.staff_id, "start_at": item.start_at.isoformat()},
        )

    db_item = BookingItem(
        booking_id=booking_id,
        service_id=item.service_id,
        staff_id=item.staff_id,
        start_at=item.start_at,
        end_at=end_at,
        price=item.price,
    )
    db.add(db_item)


def _validate_booking_time(item, end_at):
    start_minutes = item.start_at.hour * 60 + item.start_at.minute
    end_minutes = end_at.hour * 60 + end_at.minute
    if item.start_at.minute not in (0, 30) or item.start_at.second != 0:
        raise api_error(
            400,
            "INVALID_TIME_SLOT",
            "Booking start time must be on half-hour slots",
            {"start_at": item.start_at.isoformat()},
        )
    if not (BUSINESS_OPEN_MINUTES <= start_minutes < end_minutes <= BUSINESS_CLOSE_MINUTES):
        raise api_error(
            400,
            "INVALID_TIME_SLOT",
            "Booking must be within business hours",
            {"start_at": item.start_at.isoformat(), "end_at": end_at.isoformat()},
        )


def _is_staff_on_shift(db: Session, staff_id: int, start_at, end_at):
    row = (
        db.query(StaffSchedule)
        .filter(
            StaffSchedule.staff_id == staff_id,
            StaffSchedule.work_date == start_at.date(),
        )
        .first()
    )
    if not row:
        return True
    start_minutes = start_at.hour * 60 + start_at.minute
    end_minutes = end_at.hour * 60 + end_at.minute
    if row.shift_type == "off":
        return False
    if row.shift_type == "full":
        return 9 * 60 <= start_minutes and end_minutes <= 22 * 60
    if row.shift_type == "morning":
        return 9 * 60 <= start_minutes and end_minutes <= 13 * 60
    if row.shift_type == "afternoon":
        return 13 * 60 <= start_minutes and end_minutes <= 18 * 60
    return True


@router.get("/", response_model=List[BookingOut])
def list_bookings(date: str = None, db: Session = Depends(get_db), _=Depends(require_auth)):
    q = db.query(Booking)
    if date:
        from datetime import datetime
        start = datetime.fromisoformat(date)
        end = start + timedelta(days=1)
        q = q.join(BookingItem).filter(
            BookingItem.start_at >= start,
            BookingItem.start_at < end,
        )
    return q.all()


@router.post("/", response_model=BookingOut, status_code=201)
def create_booking(payload: BookingCreate, db: Session = Depends(get_db), user=Depends(require_auth)):
    booking = None
    with db.begin_nested():
        booking = Booking(customer_id=payload.customer_id, note=payload.note)
        db.add(booking)
        db.flush()

        for item in payload.items:
            service = db.get(Service, item.service_id)
            if not service:
                raise api_error(404, "SERVICE_NOT_FOUND", "Service not found", {"service_id": item.service_id})

            end_at = item.start_at + timedelta(minutes=int(service.duration))
            _validate_booking_time(item, end_at)
            if not _is_staff_on_shift(db, item.staff_id, item.start_at, end_at):
                raise api_error(
                    409,
                    "STAFF_OFF_SHIFT",
                    "Staff is off-shift for selected time",
                    {"staff_id": item.staff_id, "start_at": item.start_at.isoformat()},
                )

            lock_key = f"slot:{item.staff_id}:{item.start_at.isoformat()}"
            try:
                with _redis.lock(lock_key, timeout=10):
                    _add_booking_item_with_conflict_check(db, booking.id, item, end_at)
            except RedisError:
                # Redis unavailable: fallback to DB-level conflict check to avoid 500.
                _add_booking_item_with_conflict_check(db, booking.id, item, end_at)

    db.commit()
    db.refresh(booking)
    audit_event(
        "booking.create",
        actor_id=getattr(user, "id", None),
        actor_role=getattr(user, "role", None),
        booking_id=booking.id,
        customer_id=booking.customer_id,
        item_count=len(payload.items),
    )
    return booking


@router.patch("/{booking_id}/status", response_model=BookingOut)
def update_status(booking_id: int, payload: BookingStatusUpdate, db: Session = Depends(get_db), user=Depends(require_auth)):
    booking = db.get(Booking, booking_id)
    if not booking:
        raise api_error(404, "BOOKING_NOT_FOUND", "Booking not found", {"booking_id": booking_id})
    old_status = booking.status
    booking.status = payload.status
    db.commit()
    db.refresh(booking)
    audit_event(
        "booking.update_status",
        actor_id=getattr(user, "id", None),
        actor_role=getattr(user, "role", None),
        booking_id=booking.id,
        from_status=str(old_status),
        to_status=str(payload.status),
    )
    return booking


@router.get("/{booking_id}", response_model=BookingOut)
def get_booking(booking_id: int, db: Session = Depends(get_db), _=Depends(require_auth)):
    booking = db.get(Booking, booking_id)
    if not booking:
        raise api_error(404, "BOOKING_NOT_FOUND", "Booking not found", {"booking_id": booking_id})
    return booking
