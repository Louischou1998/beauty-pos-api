from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Date
from pydantic import BaseModel
from typing import List, Optional
from decimal import Decimal
from datetime import datetime, date
from database import get_db
from models.payment import Payment
from auth import require_admin

router = APIRouter(prefix="/payments", tags=["payments"])


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
        target = datetime.fromisoformat(date_str)
        from datetime import timedelta
        q = q.filter(Payment.created_at >= target, Payment.created_at < target + timedelta(days=1))
    return q.order_by(Payment.created_at.desc()).all()


@router.get("/daily-summary")
def daily_summary(date_str: Optional[str] = None, db: Session = Depends(get_db), _=Depends(require_admin)):
    target_date = date.fromisoformat(date_str) if date_str else date.today()
    start = datetime(target_date.year, target_date.month, target_date.day)
    from datetime import timedelta
    end = start + timedelta(days=1)

    rows = (
        db.query(Payment.method, func.sum(Payment.amount).label("total"), func.count().label("count"))
        .filter(Payment.created_at >= start, Payment.created_at < end)
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
