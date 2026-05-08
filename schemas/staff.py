from pydantic import BaseModel
from typing import List, Optional


class StaffBase(BaseModel):
    name: str
    phone: Optional[str] = None
    color: str = "#1677ff"
    skills: List[str] = []
    commission_rate: float = 35.0


class StaffCreate(StaffBase):
    pass


class StaffUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    color: Optional[str] = None
    skills: Optional[List[str]] = None
    commission_rate: Optional[float] = None


class StaffOut(StaffBase):
    id: int
    is_active: int

    model_config = {"from_attributes": True}
