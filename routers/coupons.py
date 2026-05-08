from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from decimal import Decimal
from datetime import datetime
from database import get_db
from models.coupon import Coupon
from auth import require_auth, require_admin

router = APIRouter(prefix="/coupons", tags=["coupons"])


class CouponCreate(BaseModel):
    code: str
    name: str
    type: str
    value: Decimal
    min_amount: Decimal = Decimal("0")
    max_uses: int = 0
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None


class CouponOut(BaseModel):
    id: int
    code: str
    name: str
    type: str
    value: Decimal
    min_amount: Decimal
    max_uses: int
    used_count: int
    valid_until: Optional[datetime]
    is_active: int
    model_config = {"from_attributes": True}


class ValidateResponse(BaseModel):
    valid: bool
    coupon: Optional[CouponOut] = None
    discount: float = 0
    message: str = ""


@router.get("/", response_model=List[CouponOut])
def list_coupons(db: Session = Depends(get_db), _=Depends(require_auth)):
    return db.query(Coupon).all()


@router.post("/", response_model=CouponOut, status_code=201)
def create_coupon(payload: CouponCreate, db: Session = Depends(get_db), _=Depends(require_admin)):
    if db.query(Coupon).filter(Coupon.code == payload.code).first():
        raise HTTPException(400, "Coupon code already exists")
    c = Coupon(**payload.model_dump())
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


@router.post("/validate", response_model=ValidateResponse)
def validate_coupon(code: str, amount: float, db: Session = Depends(get_db), _=Depends(require_auth)):
    c = db.query(Coupon).filter(Coupon.code == code.upper(), Coupon.is_active == 1).first()
    if not c:
        return ValidateResponse(valid=False, message="優惠券不存在或已停用")

    now = datetime.utcnow()
    if c.valid_until and c.valid_until < now:
        return ValidateResponse(valid=False, message="優惠券已過期")
    if c.max_uses > 0 and c.used_count >= c.max_uses:
        return ValidateResponse(valid=False, message="優惠券使用次數已達上限")
    if amount < float(c.min_amount):
        return ValidateResponse(valid=False, message=f"消費需滿 ${c.min_amount:.0f} 才可使用")

    if c.type == "percent":
        discount = round(amount * float(c.value), 0)
    elif c.type == "fixed":
        discount = float(c.value)
    else:  # free_service
        discount = float(c.value)

    return ValidateResponse(valid=True, coupon=CouponOut.model_validate(c), discount=discount, message=c.name)


@router.patch("/{coupon_id}/toggle")
def toggle_coupon(coupon_id: int, db: Session = Depends(get_db), _=Depends(require_admin)):
    c = db.get(Coupon, coupon_id)
    if not c:
        raise HTTPException(404)
    c.is_active = 0 if c.is_active else 1
    db.commit()
    return {"is_active": c.is_active}
