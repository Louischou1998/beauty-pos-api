from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from decimal import Decimal
from database import get_db
from models.service import Service, ServiceCategory
from auth import require_auth, require_admin

router = APIRouter(prefix="/services", tags=["services"])


class ServiceCategoryOut(BaseModel):
    id: int
    name: str
    model_config = {"from_attributes": True}


class ServiceOut(BaseModel):
    id: int
    name: str
    category_id: Optional[int]
    category_name: Optional[str] = None
    duration: int
    price: Decimal
    is_active: int
    model_config = {"from_attributes": True}


class ServiceCreate(BaseModel):
    name: str
    category_id: Optional[int] = None
    duration: int
    price: Decimal


class ServiceUpdate(BaseModel):
    name: Optional[str] = None
    category_id: Optional[int] = None
    duration: Optional[int] = None
    price: Optional[Decimal] = None


def _service_to_out(svc: Service, category_name: Optional[str] = None) -> ServiceOut:
    return ServiceOut(
        id=svc.id,
        name=svc.name,
        category_id=svc.category_id,
        category_name=category_name,
        duration=svc.duration,
        price=svc.price,
        is_active=svc.is_active,
    )


@router.get("/categories", response_model=List[ServiceCategoryOut])
def list_service_categories(db: Session = Depends(get_db), _=Depends(require_auth)):
    return db.query(ServiceCategory).order_by(ServiceCategory.id).all()


@router.get("/", response_model=List[ServiceOut])
def list_services(db: Session = Depends(get_db), _=Depends(require_auth)):
    rows = (
        db.query(Service, ServiceCategory.name)
        .outerjoin(ServiceCategory, Service.category_id == ServiceCategory.id)
        .filter(Service.is_active == 1)
        .order_by(Service.id)
        .all()
    )
    return [_service_to_out(svc, cat_name) for svc, cat_name in rows]


@router.post("/", response_model=ServiceOut, status_code=201)
def create_service(payload: ServiceCreate, db: Session = Depends(get_db), _=Depends(require_admin)):
    service = Service(**payload.model_dump())
    db.add(service)
    db.commit()
    db.refresh(service)
    cat_name = None
    if service.category_id is not None:
        c = db.get(ServiceCategory, service.category_id)
        cat_name = c.name if c else None
    return _service_to_out(service, cat_name)


@router.patch("/{service_id}", response_model=ServiceOut)
def update_service(
    service_id: int, payload: ServiceUpdate, db: Session = Depends(get_db), _=Depends(require_admin)
):
    service = db.get(Service, service_id)
    if not service:
        raise HTTPException(404, "Service not found")
    for k, v in payload.model_dump(exclude_none=True).items():
        setattr(service, k, v)
    db.commit()
    db.refresh(service)
    cat_name = None
    if service.category_id is not None:
        c = db.get(ServiceCategory, service.category_id)
        cat_name = c.name if c else None
    return _service_to_out(service, cat_name)


@router.delete("/{service_id}", status_code=204)
def delete_service(service_id: int, db: Session = Depends(get_db), _=Depends(require_admin)):
    service = db.get(Service, service_id)
    if not service:
        raise HTTPException(404, "Service not found")
    service.is_active = 0
    db.commit()
