from datetime import datetime, date
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import get_db
from models.customer import Customer
from models.booking import Booking, BookingItem, BookingStatus
from models.service import Service
from models.staff import Staff
from schemas.customer import CustomerCreate, CustomerUpdate, CustomerOut, CustomerTopUp
from typing import List, Optional
from auth import require_auth, require_admin
from pydantic import BaseModel

router = APIRouter(prefix="/customers", tags=["customers"])


class CustomerHistoryOut(BaseModel):
    booking_id: int
    date: datetime
    service_name: str
    staff_name: str
    amount: float
    status: str


class UpcomingBirthdayOut(BaseModel):
    customer: CustomerOut
    days_until: int
    birthday_date: date


def _level_by_spent(total_spent: Decimal) -> str:
    if total_spent >= Decimal("50000"):
        return "VIP"
    if total_spent >= Decimal("15000"):
        return "黃金"
    return "一般"


def _customer_metrics(db: Session, customer_ids: List[int]):
    if not customer_ids:
        return {}
    rows = (
        db.query(
            Booking.customer_id.label("customer_id"),
            func.count(func.distinct(Booking.id)).label("visits"),
            func.coalesce(func.sum(BookingItem.price), 0).label("total_spent"),
        )
        .join(BookingItem, BookingItem.booking_id == Booking.id)
        .filter(
            Booking.customer_id.in_(customer_ids),
            Booking.status == BookingStatus.done,
        )
        .group_by(Booking.customer_id)
        .all()
    )
    return {r.customer_id: r for r in rows}


def _to_customer_out(customer: Customer, metric_row=None):
    spent = metric_row.total_spent if metric_row else Decimal("0")
    return CustomerOut(
        id=customer.id,
        name=customer.name,
        phone=customer.phone,
        email=customer.email,
        level=_level_by_spent(spent),
        points=customer.points,
        balance=customer.balance,
        total_spent=spent,
        visits=int(metric_row.visits) if metric_row else 0,
        allergy_info=customer.allergy_info or "",
        preferred_staff_id=customer.preferred_staff_id,
        revisit_days=customer.revisit_days,
        last_visit_at=customer.last_visit_at,
        birthday=customer.birthday,
    )


@router.get("/", response_model=List[CustomerOut])
def list_customers(db: Session = Depends(get_db), _=Depends(require_auth)):
    customers = db.query(Customer).all()
    metrics = _customer_metrics(db, [c.id for c in customers])
    return [_to_customer_out(c, metrics.get(c.id)) for c in customers]


@router.post("/", response_model=CustomerOut, status_code=201)
def create_customer(payload: CustomerCreate, db: Session = Depends(get_db), _=Depends(require_auth)):
    customer = Customer(**payload.model_dump())
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


# Must be defined before /{customer_id} to avoid path conflict
@router.get("/birthdays", response_model=List[UpcomingBirthdayOut])
def upcoming_birthdays(days: int = 30, db: Session = Depends(get_db), _=Depends(require_auth)):
    today = date.today()
    customers_with_bd = db.query(Customer).filter(Customer.birthday.isnot(None)).all()
    metrics = _customer_metrics(db, [c.id for c in customers_with_bd])
    result = []
    for c in customers_with_bd:
        bd = c.birthday
        try:
            this_year_bd = bd.replace(year=today.year)
        except ValueError:
            this_year_bd = bd.replace(year=today.year, day=28)
        delta = (this_year_bd - today).days
        if delta < 0:
            try:
                this_year_bd = bd.replace(year=today.year + 1)
            except ValueError:
                this_year_bd = bd.replace(year=today.year + 1, day=28)
            delta = (this_year_bd - today).days
        if 0 <= delta <= days:
            result.append(UpcomingBirthdayOut(
                customer=_to_customer_out(c, metrics.get(c.id)),
                days_until=delta,
                birthday_date=this_year_bd,
            ))
    return sorted(result, key=lambda x: x.days_until)


@router.get("/{customer_id}", response_model=CustomerOut)
def get_customer(customer_id: int, db: Session = Depends(get_db), _=Depends(require_auth)):
    customer = db.get(Customer, customer_id)
    if not customer:
        raise HTTPException(404, "Customer not found")
    metrics = _customer_metrics(db, [customer_id])
    return _to_customer_out(customer, metrics.get(customer_id))


@router.patch("/{customer_id}", response_model=CustomerOut)
def update_customer(customer_id: int, payload: CustomerUpdate, db: Session = Depends(get_db), _=Depends(require_auth)):
    customer = db.get(Customer, customer_id)
    if not customer:
        raise HTTPException(404, "Customer not found")
    for k, v in payload.model_dump(exclude_none=True).items():
        setattr(customer, k, v)
    db.commit()
    db.refresh(customer)
    metrics = _customer_metrics(db, [customer_id])
    return _to_customer_out(customer, metrics.get(customer_id))


@router.post("/{customer_id}/topup", response_model=CustomerOut)
def topup(customer_id: int, payload: CustomerTopUp, db: Session = Depends(get_db), _=Depends(require_admin)):
    customer = db.get(Customer, customer_id)
    if not customer:
        raise HTTPException(404, "Customer not found")
    amount = Decimal(str(payload.amount))
    if payload.type == "balance":
        customer.balance += amount
    elif payload.type == "points":
        customer.points += int(amount)
    else:
        raise HTTPException(400, "type must be 'balance' or 'points'")
    db.commit()
    db.refresh(customer)
    metrics = _customer_metrics(db, [customer_id])
    return _to_customer_out(customer, metrics.get(customer_id))


@router.get("/{customer_id}/history", response_model=List[CustomerHistoryOut])
def customer_history(customer_id: int, db: Session = Depends(get_db), _=Depends(require_auth)):
    customer = db.get(Customer, customer_id)
    if not customer:
        raise HTTPException(404, "Customer not found")

    rows = (
        db.query(
            Booking.id.label("booking_id"),
            BookingItem.start_at.label("date"),
            Service.name.label("service_name"),
            Staff.name.label("staff_name"),
            BookingItem.price.label("amount"),
            Booking.status.label("status"),
        )
        .join(BookingItem, BookingItem.booking_id == Booking.id)
        .join(Service, Service.id == BookingItem.service_id)
        .join(Staff, Staff.id == BookingItem.staff_id)
        .filter(
            Booking.customer_id == customer_id,
            Booking.status == BookingStatus.done,
        )
        .order_by(BookingItem.start_at.desc())
        .limit(100)
        .all()
    )

    return [
        CustomerHistoryOut(
            booking_id=r.booking_id,
            date=r.date,
            service_name=r.service_name,
            staff_name=r.staff_name,
            amount=float(r.amount),
            status=str(r.status),
        )
        for r in rows
    ]
