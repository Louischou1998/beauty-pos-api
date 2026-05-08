from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from decimal import Decimal
from database import get_db
from models.service import Service
from auth import require_auth, require_admin

router = APIRouter(prefix="/services", tags=["services"])


class ServiceOut(BaseModel):
    id: int
    name: str
    category_id: Optional[int]
    duration: int
    price: Decimal
    is_active: int
    model_config = {"from_attributes": True}


class ServiceCreate(BaseModel):
    name: str
    category_id: Optional[int] = None
    duration: int
    price: Decimal


@router.get("/", response_model=List[ServiceOut])
def list_services(db: Session = Depends(get_db), _=Depends(require_auth)):
    return db.query(Service).filter(Service.is_active == 1).all()


@router.post("/", response_model=ServiceOut, status_code=201)
def create_service(payload: ServiceCreate, db: Session = Depends(get_db), _=Depends(require_admin)):
    service = Service(**payload.model_dump())
    db.add(service)
    db.commit()
    db.refresh(service)
    return service


@router.delete("/{service_id}", status_code=204)
def delete_service(service_id: int, db: Session = Depends(get_db), _=Depends(require_admin)):
    service = db.get(Service, service_id)
    if not service:
        raise HTTPException(404, "Service not found")
    service.is_active = 0
    db.commit()
