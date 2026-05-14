from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import exists as sa_exists
from sqlalchemy import and_
from datetime import datetime, date as DateType, timedelta, timezone as dt_timezone
from zoneinfo import ZoneInfo
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

_APP_TZ = ZoneInfo("Asia/Taipei")
_UTC = ZoneInfo("UTC")


def _utc_range_for_local_calendar_day(d: DateType):
    start_local = datetime(d.year, d.month, d.day, 0, 0, 0, tzinfo=_APP_TZ)
    end_local = start_local + timedelta(days=1)
    return (
        start_local.astimezone(_UTC).replace(tzinfo=None),
        end_local.astimezone(_UTC).replace(tzinfo=None),
    )


def _to_taipei(dt: datetime) -> datetime:
    """後台行事曆傳 ISO(Z)；DB 內可能為 UTC naive。"""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=dt_timezone.utc).astimezone(_APP_TZ)
    return dt.astimezone(_APP_TZ)


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
    local_start = _to_taipei(item.start_at)
    local_end = _to_taipei(end_at)
    start_minutes = local_start.hour * 60 + local_start.minute
    end_minutes = local_end.hour * 60 + local_end.minute
    if local_start.minute not in (0, 30) or local_start.second != 0:
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
    local_start = _to_taipei(start_at)
    local_end = _to_taipei(end_at)
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


@router.get("/", response_model=List[BookingOut])
def list_bookings(
    date: str = None,
    start_date: str = None,
    end_date: str = None,
    db: Session = Depends(get_db),
    _=Depends(require_auth),
):
    q = db.query(Booking).options(selectinload(Booking.items))
    if date:
        d = DateType.fromisoformat(date)
        start, end = _utc_range_for_local_calendar_day(d)
        q = q.filter(sa_exists().where(
            (BookingItem.booking_id == Booking.id) &
            (BookingItem.start_at >= start) &
            (BookingItem.start_at < end),
        ))
    elif start_date and end_date:
        sd = DateType.fromisoformat(start_date)
        ed = DateType.fromisoformat(end_date)
        start, _ = _utc_range_for_local_calendar_day(sd)
        _, end = _utc_range_for_local_calendar_day(ed)
        q = q.filter(sa_exists().where(
            (BookingItem.booking_id == Booking.id) &
            (BookingItem.start_at >= start) &
            (BookingItem.start_at < end),
        ))
    return q.all()


@router.post("/", response_model=BookingOut, status_code=201)
def create_booking(payload: BookingCreate, db: Session = Depends(get_db), user=Depends(require_auth)):
    service_ids = {item.service_id for item in payload.items}
    services_map = {s.id: s for s in db.query(Service).filter(Service.id.in_(service_ids)).all()}

    booking = None
    with db.begin_nested():
        booking = Booking(customer_id=payload.customer_id, note=payload.note)
        db.add(booking)
        db.flush()

        for item in payload.items:
            service = services_map.get(item.service_id)
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
