from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import date
from database import get_db
from models.staff import Staff
from models.staff_schedule import StaffSchedule
from schemas.staff import StaffCreate, StaffUpdate, StaffOut
from typing import List
from auth import require_auth, require_admin

router = APIRouter(prefix="/staff", tags=["staff"])

SHIFT_TYPES = {"morning", "afternoon", "full", "off"}


class StaffScheduleEntry(BaseModel):
    work_date: date
    shift_type: str


class StaffScheduleOut(BaseModel):
    id: int
    staff_id: int
    work_date: date
    shift_type: str

    model_config = {"from_attributes": True}


@router.get("/", response_model=List[StaffOut])
def list_staff(db: Session = Depends(get_db), _=Depends(require_auth)):
    return db.query(Staff).filter(Staff.is_active == 1).all()


@router.post("/", response_model=StaffOut, status_code=201)
def create_staff(payload: StaffCreate, db: Session = Depends(get_db), _=Depends(require_admin)):
    staff = Staff(**payload.model_dump())
    db.add(staff)
    db.commit()
    db.refresh(staff)
    return staff


@router.patch("/{staff_id}", response_model=StaffOut)
def update_staff(staff_id: int, payload: StaffUpdate, db: Session = Depends(get_db), _=Depends(require_admin)):
    staff = db.get(Staff, staff_id)
    if not staff:
        raise HTTPException(404, "Staff not found")
    for k, v in payload.model_dump(exclude_none=True).items():
        setattr(staff, k, v)
    db.commit()
    db.refresh(staff)
    return staff


@router.delete("/{staff_id}", status_code=204)
def delete_staff(staff_id: int, db: Session = Depends(get_db), _=Depends(require_admin)):
    staff = db.get(Staff, staff_id)
    if not staff:
        raise HTTPException(404, "Staff not found")
    staff.is_active = 0
    db.commit()


@router.get("/{staff_id}/schedules", response_model=List[StaffScheduleOut])
def list_schedules(
    staff_id: int,
    start_date: date,
    end_date: date,
    db: Session = Depends(get_db),
    _=Depends(require_auth),
):
    staff = db.get(Staff, staff_id)
    if not staff:
        raise HTTPException(404, "Staff not found")
    return (
        db.query(StaffSchedule)
        .filter(
            StaffSchedule.staff_id == staff_id,
            StaffSchedule.work_date >= start_date,
            StaffSchedule.work_date <= end_date,
        )
        .order_by(StaffSchedule.work_date.asc())
        .all()
    )


@router.put("/{staff_id}/schedules", response_model=List[StaffScheduleOut])
def upsert_schedules(
    staff_id: int,
    payload: List[StaffScheduleEntry],
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    staff = db.get(Staff, staff_id)
    if not staff:
        raise HTTPException(404, "Staff not found")

    for entry in payload:
        if entry.shift_type not in SHIFT_TYPES:
            raise HTTPException(400, "Invalid shift_type")

        row = (
            db.query(StaffSchedule)
            .filter(
                StaffSchedule.staff_id == staff_id,
                StaffSchedule.work_date == entry.work_date,
            )
            .first()
        )
        if row:
            row.shift_type = entry.shift_type
        else:
            db.add(StaffSchedule(staff_id=staff_id, work_date=entry.work_date, shift_type=entry.shift_type))

    db.commit()
    dates = [p.work_date for p in payload]
    if not dates:
        return []
    return (
        db.query(StaffSchedule)
        .filter(
            StaffSchedule.staff_id == staff_id,
            StaffSchedule.work_date >= min(dates),
            StaffSchedule.work_date <= max(dates),
        )
        .order_by(StaffSchedule.work_date.asc())
        .all()
    )
