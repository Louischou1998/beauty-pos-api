from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from decimal import Decimal
from database import get_db
from models.product import Product
from auth import require_auth, require_admin

router = APIRouter(prefix="/products", tags=["products"])


class ProductCreate(BaseModel):
    name: str
    category: Optional[str] = None
    price: Decimal
    cost: Decimal = Decimal("0")
    stock: int = 0
    barcode: Optional[str] = None


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    price: Optional[Decimal] = None
    cost: Optional[Decimal] = None
    stock: Optional[int] = None
    barcode: Optional[str] = None


class ProductOut(BaseModel):
    id: int
    name: str
    category: Optional[str]
    price: Decimal
    cost: Decimal
    stock: int
    barcode: Optional[str]
    is_active: int
    model_config = {"from_attributes": True}


@router.get("/", response_model=List[ProductOut])
def list_products(db: Session = Depends(get_db), _=Depends(require_auth)):
    return db.query(Product).filter(Product.is_active == 1).all()


@router.post("/", response_model=ProductOut, status_code=201)
def create_product(payload: ProductCreate, db: Session = Depends(get_db), _=Depends(require_admin)):
    p = Product(**payload.model_dump())
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


@router.patch("/{product_id}", response_model=ProductOut)
def update_product(product_id: int, payload: ProductUpdate, db: Session = Depends(get_db), _=Depends(require_admin)):
    p = db.get(Product, product_id)
    if not p:
        raise HTTPException(404, "Product not found")
    for k, v in payload.model_dump(exclude_none=True).items():
        setattr(p, k, v)
    db.commit()
    db.refresh(p)
    return p


@router.delete("/{product_id}", status_code=204)
def delete_product(product_id: int, db: Session = Depends(get_db), _=Depends(require_admin)):
    p = db.get(Product, product_id)
    if not p:
        raise HTTPException(404, "Product not found")
    p.is_active = 0
    db.commit()
