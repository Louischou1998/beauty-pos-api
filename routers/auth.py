from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from database import get_db
from models.user import User
from auth import hash_password, verify_password, create_access_token, require_auth, require_admin

router = APIRouter(prefix="/auth", tags=["auth"])


class UserCreate(BaseModel):
    name: str
    email: str
    password: str
    role: str = "staff"
    staff_id: Optional[int] = None


class UserOut(BaseModel):
    id: int
    name: str
    email: str
    role: str
    staff_id: Optional[int]
    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


@router.post("/login", response_model=TokenResponse)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form.username, User.is_active == 1).first()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="帳號或密碼錯誤")
    token = create_access_token({"sub": str(user.id), "role": user.role})
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def me(user=Depends(require_auth)):
    if user is None:
        raise HTTPException(401, "Not authenticated")
    return user


@router.post("/users", response_model=UserOut, status_code=201)
def create_user(payload: UserCreate, db: Session = Depends(get_db), _=Depends(require_admin)):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(400, "Email already exists")
    user = User(
        name=payload.name,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        role=payload.role,
        staff_id=payload.staff_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
