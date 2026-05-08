from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Date
from datetime import datetime, timedelta
from database import get_db
from models.booking import Booking, BookingItem, BookingStatus
from models.staff import Staff
from models.service import Service
from auth import require_admin

router = APIRouter(prefix="/reports", tags=["reports"])


def _date_range(period: str):
    today = datetime.utcnow().date()
    if period == "week":
        start = today - timedelta(days=6)
    elif period == "month":
        start = today.replace(day=1)
    elif period == "quarter":
        month = ((today.month - 1) // 3) * 3 + 1
        start = today.replace(month=month, day=1)
    else:
        start = today - timedelta(days=6)
    return datetime(start.year, start.month, start.day), datetime(today.year, today.month, today.day, 23, 59, 59)


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

    rows = (
        db.query(
            cast(BookingItem.start_at, Date).label("date"),
            func.sum(BookingItem.price).label("revenue"),
            func.count(func.distinct(Booking.id)).label("bookings"),
        )
        .join(Booking, BookingItem.booking_id == Booking.id)
        .filter(
            Booking.status != BookingStatus.cancelled,
            BookingItem.start_at.between(start, end),
        )
        .group_by(cast(BookingItem.start_at, Date))
        .order_by(cast(BookingItem.start_at, Date))
        .all()
    )

    return [
        {"date": str(r.date), "revenue": float(r.revenue), "bookings": r.bookings}
        for r in rows
    ]


@router.get("/daily-staff")
def daily_staff_breakdown(period: str = Query("week"), db: Session = Depends(get_db), _=Depends(require_admin)):
    start, end = _date_range(period)

    rows = (
        db.query(
            cast(BookingItem.start_at, Date).label("date"),
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
        .group_by(cast(BookingItem.start_at, Date), Staff.id, Staff.name, Staff.color)
        .order_by(cast(BookingItem.start_at, Date), func.coalesce(func.sum(BookingItem.price), 0).desc())
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
        .outerjoin(BookingItem, BookingItem.staff_id == Staff.id)
        .outerjoin(Booking, (BookingItem.booking_id == Booking.id) & (Booking.status != BookingStatus.cancelled) & BookingItem.start_at.between(start, end))
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
