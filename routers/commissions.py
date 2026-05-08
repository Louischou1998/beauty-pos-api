from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from pydantic import BaseModel
from typing import List, Optional
from decimal import Decimal
from datetime import datetime, date
from database import get_db
from models.commission import Commission
from models.staff import Staff
from auth import require_admin

router = APIRouter(prefix="/commissions", tags=["commissions"])


class CommissionOut(BaseModel):
    id: int
    booking_id: int
    staff_id: int
    type: str
    item_name: Optional[str]
    is_designated: bool
    base_amount: Decimal
    commission_rate: Decimal
    commission_amount: Decimal
    created_at: datetime
    model_config = {"from_attributes": True}


@router.get("/", response_model=List[CommissionOut])
def list_commissions(staff_id: Optional[int] = None, month: Optional[str] = None, db: Session = Depends(get_db), _=Depends(require_admin)):
    q = db.query(Commission)
    if staff_id:
        q = q.filter(Commission.staff_id == staff_id)
    if month:
        y, m = map(int, month.split("-"))
        from datetime import timedelta
        start = datetime(y, m, 1)
        end = datetime(y, m + 1, 1) if m < 12 else datetime(y + 1, 1, 1)
        q = q.filter(Commission.created_at >= start, Commission.created_at < end)
    return q.order_by(Commission.created_at.desc()).all()


def _payroll_impl(month: str, db: Session):
    y, m = map(int, month.split("-"))
    start = datetime(y, m, 1)
    end = datetime(y, m + 1, 1) if m < 12 else datetime(y + 1, 1, 1)

    rows = (
        db.query(
            Commission.staff_id,
            Staff.name.label("staff_name"),
            Staff.color,
            Staff.commission_rate,
            func.count(Commission.id).label("transactions"),
            func.sum(Commission.base_amount).label("revenue"),
            func.sum(Commission.commission_amount).label("commission"),
            func.sum(
                case((Commission.is_designated.is_(True), Commission.commission_amount), else_=0)
            ).label("designated_commission"),
        )
        .join(Staff, Commission.staff_id == Staff.id)
        .filter(Commission.created_at >= start, Commission.created_at < end)
        .group_by(Commission.staff_id, Staff.name, Staff.color, Staff.commission_rate)
        .order_by(func.sum(Commission.commission_amount).desc())
        .all()
    )

    return [
        {
            "staff_id": r.staff_id,
            "staff_name": r.staff_name,
            "color": r.color,
            "transactions": r.transactions,
            "revenue": float(r.revenue or 0),
            "commission": float(r.commission or 0),
            "designated_commission": float(r.designated_commission or 0),
        }
        for r in rows
    ]


@router.get("/payroll")
@router.get("/payroll/")
def payroll(month: str = Query(...), db: Session = Depends(get_db), _=Depends(require_admin)):
    return _payroll_impl(month, db)
