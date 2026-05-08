from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import List, Optional
from decimal import Decimal
from datetime import datetime
from database import get_db
from models.inventory import InventoryItem, InventoryUsage
from auth import require_auth, require_admin

router = APIRouter(prefix="/inventory", tags=["inventory"])


class ItemCreate(BaseModel):
    name: str
    category: Optional[str] = None
    unit: str = "個"
    quantity: Decimal = Decimal("0")
    low_stock_threshold: Decimal = Decimal("10")
    cost_per_unit: Decimal = Decimal("0")


class ItemUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    unit: Optional[str] = None
    quantity: Optional[Decimal] = None
    low_stock_threshold: Optional[Decimal] = None
    cost_per_unit: Optional[Decimal] = None


class ItemOut(BaseModel):
    id: int
    name: str
    category: Optional[str]
    unit: str
    quantity: Decimal
    low_stock_threshold: Decimal
    cost_per_unit: Decimal
    is_low: bool = False
    model_config = {"from_attributes": True}


class UseRequest(BaseModel):
    quantity_used: Decimal
    staff_id: Optional[int] = None
    booking_id: Optional[int] = None
    note: Optional[str] = None


class UsageOut(BaseModel):
    id: int
    item_id: int
    quantity_used: Decimal
    used_at: datetime
    note: Optional[str]
    model_config = {"from_attributes": True}


def _to_item_out(item: InventoryItem) -> ItemOut:
    out = ItemOut.model_validate(item)
    out.is_low = float(item.quantity) <= float(item.low_stock_threshold)
    return out


@router.get("/", response_model=List[ItemOut])
def list_items(db: Session = Depends(get_db), _=Depends(require_auth)):
    items = db.query(InventoryItem).all()
    return [_to_item_out(i) for i in items]


@router.post("/", response_model=ItemOut, status_code=201)
def create_item(payload: ItemCreate, db: Session = Depends(get_db), _=Depends(require_admin)):
    item = InventoryItem(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return _to_item_out(item)


@router.patch("/{item_id}", response_model=ItemOut)
def update_item(item_id: int, payload: ItemUpdate, db: Session = Depends(get_db), _=Depends(require_admin)):
    item = db.get(InventoryItem, item_id)
    if not item:
        raise HTTPException(404, "Item not found")
    for k, v in payload.model_dump(exclude_none=True).items():
        setattr(item, k, v)
    db.commit()
    db.refresh(item)
    return _to_item_out(item)


@router.delete("/{item_id}", status_code=204)
def delete_item(item_id: int, db: Session = Depends(get_db), _=Depends(require_admin)):
    item = db.get(InventoryItem, item_id)
    if not item:
        raise HTTPException(404, "Item not found")
    db.delete(item)
    db.commit()


@router.post("/{item_id}/use", response_model=ItemOut)
def use_item(item_id: int, payload: UseRequest, db: Session = Depends(get_db), _=Depends(require_auth)):
    item = db.get(InventoryItem, item_id)
    if not item:
        raise HTTPException(404, "Item not found")
    if float(item.quantity) < float(payload.quantity_used):
        raise HTTPException(400, "庫存不足")
    item.quantity -= payload.quantity_used
    usage = InventoryUsage(
        item_id=item_id,
        quantity_used=payload.quantity_used,
        staff_id=payload.staff_id,
        booking_id=payload.booking_id,
        note=payload.note,
    )
    db.add(usage)
    db.commit()
    db.refresh(item)
    return _to_item_out(item)


@router.get("/{item_id}/usage", response_model=List[UsageOut])
def get_usage(item_id: int, db: Session = Depends(get_db), _=Depends(require_auth)):
    return db.query(InventoryUsage).filter(InventoryUsage.item_id == item_id).order_by(InventoryUsage.used_at.desc()).limit(50).all()
