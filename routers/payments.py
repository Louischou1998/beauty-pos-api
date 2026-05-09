from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import List, Optional, Tuple
from decimal import Decimal
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
from database import get_db
from models.payment import Payment
from auth import require_admin

router = APIRouter(prefix="/payments", tags=["payments"])

# 與前端日結「選定日期」一致：以台灣日曆日換算成 UTC 區間（created_at 為 UTC naive）
_APP_TZ = ZoneInfo("Asia/Taipei")


def _today_in_app_tz() -> date:
    return datetime.now(_APP_TZ).date()


def _utc_range_for_local_calendar_day(d: date) -> Tuple[datetime, datetime]:
    start_local = datetime(d.year, d.month, d.day, 0, 0, 0, tzinfo=_APP_TZ)
    end_local = start_local + timedelta(days=1)
    start_utc = start_local.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
    end_utc = end_local.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
    return start_utc, end_utc


class PaymentOut(BaseModel):
    id: int
    booking_id: int
    method: str
    amount: Decimal
    created_at: datetime
    note: Optional[str]
    model_config = {"from_attributes": True}


@router.get("/", response_model=List[PaymentOut])
def list_payments(date_str: Optional[str] = None, db: Session = Depends(get_db), _=Depends(require_admin)):
    q = db.query(Payment)
    if date_str:
        d = date.fromisoformat(date_str)
        start_utc, end_utc = _utc_range_for_local_calendar_day(d)
        q = q.filter(Payment.created_at >= start_utc, Payment.created_at < end_utc)
    return q.order_by(Payment.created_at.desc()).all()


@router.get("/daily-summary")
def daily_summary(date_str: Optional[str] = None, db: Session = Depends(get_db), _=Depends(require_admin)):
    target_date = date.fromisoformat(date_str) if date_str else _today_in_app_tz()
    start_utc, end_utc = _utc_range_for_local_calendar_day(target_date)

    rows = (
        db.query(Payment.method, func.sum(Payment.amount).label("total"), func.count().label("count"))
        .filter(Payment.created_at >= start_utc, Payment.created_at < end_utc)
        .group_by(Payment.method)
        .all()
    )

    total = sum(float(r.total) for r in rows)
    return {
        "date": str(target_date),
        "total": total,
        "by_method": [{"method": r.method, "total": float(r.total), "count": r.count} for r in rows],
        "transaction_count": sum(r.count for r in rows),
    }
