from datetime import date, datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database import get_db
from models.hair_record import HairRecord
from models.customer import Customer
from models.staff import Staff
from auth import require_auth

router = APIRouter(prefix="/customers", tags=["hair-records"])


class HairRecordCreate(BaseModel):
    record_date: date
    staff_id: Optional[int] = None
    service_names: Optional[str] = ""
    color_formula: Optional[str] = ""
    hair_condition: Optional[str] = ""
    notes: Optional[str] = ""


class HairRecordUpdate(BaseModel):
    record_date: Optional[date] = None
    staff_id: Optional[int] = None
    service_names: Optional[str] = None
    color_formula: Optional[str] = None
    hair_condition: Optional[str] = None
    notes: Optional[str] = None


class HairRecordOut(BaseModel):
    id: int
    customer_id: int
    staff_id: Optional[int] = None
    staff_name: Optional[str] = None
    record_date: date
    service_names: Optional[str] = ""
    color_formula: Optional[str] = ""
    hair_condition: Optional[str] = ""
    notes: Optional[str] = ""
    created_at: datetime

    model_config = {"from_attributes": True}


def _to_out(record: HairRecord, db: Session) -> HairRecordOut:
    staff = db.get(Staff, record.staff_id) if record.staff_id else None
    return HairRecordOut(
        id=record.id,
        customer_id=record.customer_id,
        staff_id=record.staff_id,
        staff_name=staff.name if staff else None,
        record_date=record.record_date,
        service_names=record.service_names or "",
        color_formula=record.color_formula or "",
        hair_condition=record.hair_condition or "",
        notes=record.notes or "",
        created_at=record.created_at,
    )


@router.get("/{customer_id}/hair-records", response_model=List[HairRecordOut])
def list_hair_records(customer_id: int, db: Session = Depends(get_db), _=Depends(require_auth)):
    if not db.get(Customer, customer_id):
        raise HTTPException(404, "Customer not found")
    rows = (
        db.query(HairRecord, Staff.name.label("staff_name"))
        .outerjoin(Staff, HairRecord.staff_id == Staff.id)
        .filter(HairRecord.customer_id == customer_id)
        .order_by(HairRecord.record_date.desc())
        .all()
    )
    return [
        HairRecordOut(
            id=r.HairRecord.id,
            customer_id=r.HairRecord.customer_id,
            staff_id=r.HairRecord.staff_id,
            staff_name=r.staff_name,
            record_date=r.HairRecord.record_date,
            service_names=r.HairRecord.service_names or "",
            color_formula=r.HairRecord.color_formula or "",
            hair_condition=r.HairRecord.hair_condition or "",
            notes=r.HairRecord.notes or "",
            created_at=r.HairRecord.created_at,
        )
        for r in rows
    ]


@router.post("/{customer_id}/hair-records", response_model=HairRecordOut, status_code=201)
def create_hair_record(
    customer_id: int, payload: HairRecordCreate,
    db: Session = Depends(get_db), _=Depends(require_auth),
):
    if not db.get(Customer, customer_id):
        raise HTTPException(404, "Customer not found")
    record = HairRecord(customer_id=customer_id, **payload.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return _to_out(record, db)


@router.patch("/{customer_id}/hair-records/{record_id}", response_model=HairRecordOut)
def update_hair_record(
    customer_id: int, record_id: int, payload: HairRecordUpdate,
    db: Session = Depends(get_db), _=Depends(require_auth),
):
    record = db.query(HairRecord).filter(
        HairRecord.id == record_id, HairRecord.customer_id == customer_id
    ).first()
    if not record:
        raise HTTPException(404, "Record not found")
    for k, v in payload.model_dump(exclude_none=True).items():
        setattr(record, k, v)
    db.commit()
    db.refresh(record)
    return _to_out(record, db)


@router.delete("/{customer_id}/hair-records/{record_id}", status_code=204)
def delete_hair_record(
    customer_id: int, record_id: int,
    db: Session = Depends(get_db), _=Depends(require_auth),
):
    record = db.query(HairRecord).filter(
        HairRecord.id == record_id, HairRecord.customer_id == customer_id
    ).first()
    if not record:
        raise HTTPException(404, "Record not found")
    db.delete(record)
    db.commit()
