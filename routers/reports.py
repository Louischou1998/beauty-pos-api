from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Date
from datetime import datetime, timedelta, date
from typing import Tuple
from zoneinfo import ZoneInfo
from database import get_db
from models.booking import Booking, BookingItem, BookingStatus
from models.staff import Staff
from models.service import Service
from auth import require_admin

router = APIRouter(prefix="/reports", tags=["reports"])

_APP_TZ = ZoneInfo("Asia/Taipei")
_UTC = ZoneInfo("UTC")


def _today_app() -> date:
    return datetime.now(_APP_TZ).date()


def _local_day_bounds_utc_naive(d: date) -> Tuple[datetime, datetime]:
    """該日在 Asia/Taipei 的 00:00:00 與 23:59:59.999999，轉成 UTC naive（與 DB 存儲一致）。"""
    start_local = datetime(d.year, d.month, d.day, 0, 0, 0, tzinfo=_APP_TZ)
    end_local = datetime(d.year, d.month, d.day, 23, 59, 59, 999999, tzinfo=_APP_TZ)
    start_utc = start_local.astimezone(_UTC).replace(tzinfo=None)
    end_utc = end_local.astimezone(_UTC).replace(tzinfo=None)
    return start_utc, end_utc


def _date_range(period: str):
    today = _today_app()
    if period == "week":
        start_date = today - timedelta(days=6)
    elif period == "month":
        start_date = today.replace(day=1)
    elif period == "quarter":
        month = ((today.month - 1) // 3) * 3 + 1
        start_date = today.replace(month=month, day=1)
    else:
        start_date = today - timedelta(days=6)
    range_start, _ = _local_day_bounds_utc_naive(start_date)
    _, range_end = _local_day_bounds_utc_naive(today)
    return range_start, range_end


def _booking_item_taipei_date(db: Session):
    """BookingItem.start_at 以 UTC naive 儲存時，依 Asia/Taipei 切日（PostgreSQL 精確；SQLite 用 +8h）。"""
    if db.get_bind().dialect.name == "postgresql":
        return cast(func.timezone("Asia/Taipei", func.timezone("UTC", BookingItem.start_at)), Date)
    return cast(func.date(BookingItem.start_at, "+8 hours"), Date)


@router.get("/summary")
def summary(period: str = Query("week"), db: Session = Depends(get_db), _=Depends(require_admin)):
    start, end = _date_range(period)

    base = (
        db.query(func.sum(BookingItem.price), func.count(func.distinct(Booking.id)))
        .join(Booking, BookingItem.booking_id == Booking.id)
        .filter(
            Booking.status != BookingStatus.cancelled,
            BookingItem.start_at.between(start, end),
        )
    )
    total_revenue, total_bookings = base.first()
    total_revenue = float(total_revenue or 0)
    total_bookings = total_bookings or 0

    return {
        "total_revenue": total_revenue,
        "total_bookings": total_bookings,
        "avg_per_booking": round(total_revenue / total_bookings, 0) if total_bookings else 0,
    }


@router.get("/daily")
def daily(period: str = Query("week"), db: Session = Depends(get_db), _=Depends(require_admin)):
    start, end = _date_range(period)
    day_col = _booking_item_taipei_date(db)

    rows = (
        db.query(
            day_col.label("date"),
            func.sum(BookingItem.price).label("revenue"),
            func.count(func.distinct(Booking.id)).label("bookings"),
        )
        .join(Booking, BookingItem.booking_id == Booking.id)
        .filter(
            Booking.status != BookingStatus.cancelled,
            BookingItem.start_at.between(start, end),
        )
        .group_by(day_col)
        .order_by(day_col)
        .all()
    )

    return [
        {"date": str(r.date), "revenue": float(r.revenue), "bookings": r.bookings}
        for r in rows
    ]


@router.get("/daily-staff")
def daily_staff_breakdown(period: str = Query("week"), db: Session = Depends(get_db), _=Depends(require_admin)):
    start, end = _date_range(period)
    day_col = _booking_item_taipei_date(db)

    rows = (
        db.query(
            day_col.label("date"),
            Staff.id.label("staff_id"),
            Staff.name.label("staff_name"),
            Staff.color.label("staff_color"),
            func.coalesce(func.sum(BookingItem.price), 0).label("revenue"),
        )
        .join(Booking, BookingItem.booking_id == Booking.id)
        .join(Staff, BookingItem.staff_id == Staff.id)
        .filter(
            Booking.status != BookingStatus.cancelled,
            BookingItem.start_at.between(start, end),
        )
        .group_by(day_col, Staff.id, Staff.name, Staff.color)
        .order_by(day_col, func.coalesce(func.sum(BookingItem.price), 0).desc())
        .all()
    )

    return [
        {
            "date": str(r.date),
            "staff_id": r.staff_id,
            "staff_name": r.staff_name,
            "staff_color": r.staff_color,
            "revenue": float(r.revenue),
        }
        for r in rows
    ]


@router.get("/staff")
def staff_performance(period: str = Query("week"), db: Session = Depends(get_db), _=Depends(require_admin)):
    start, end = _date_range(period)

    rows = (
        db.query(
            Staff.id,
            Staff.name,
            Staff.color,
            Staff.commission_rate,
            func.count(BookingItem.id).label("bookings"),
            func.coalesce(func.sum(BookingItem.price), 0).label("revenue"),
        )
        .outerjoin(BookingItem, (BookingItem.staff_id == Staff.id) & BookingItem.start_at.between(start, end))
        .outerjoin(Booking, (BookingItem.booking_id == Booking.id) & (Booking.status != BookingStatus.cancelled))
        .filter(Staff.is_active == 1)
        .group_by(Staff.id, Staff.name, Staff.color, Staff.commission_rate)
        .order_by(func.coalesce(func.sum(BookingItem.price), 0).desc())
        .all()
    )

    return [
        {
            "id": r.id,
            "name": r.name,
            "color": r.color,
            "commission_rate": float(r.commission_rate),
            "bookings": r.bookings,
            "revenue": float(r.revenue),
            "commission": round(float(r.revenue) * float(r.commission_rate) / 100, 0),
        }
        for r in rows
    ]


@router.get("/categories")
def category_breakdown(period: str = Query("week"), db: Session = Depends(get_db), _=Depends(require_admin)):
    start, end = _date_range(period)

    rows = (
        db.query(
            Service.name,
            func.coalesce(func.sum(BookingItem.price), 0).label("revenue"),
        )
        .join(BookingItem, BookingItem.service_id == Service.id)
        .join(Booking, BookingItem.booking_id == Booking.id)
        .filter(
            Booking.status != BookingStatus.cancelled,
            BookingItem.start_at.between(start, end),
            Service.is_active == 1,
        )
        .group_by(Service.name)
        .order_by(func.coalesce(func.sum(BookingItem.price), 0).desc())
        .all()
    )

    return [{"name": r.name, "value": float(r.revenue)} for r in rows]
