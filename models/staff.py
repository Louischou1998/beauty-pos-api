from sqlalchemy import Column, Integer, String, Numeric, ARRAY
from database import Base


class Staff(Base):
    __tablename__ = "staff"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)
    phone = Column(String(20))
    color = Column(String(10), default="#1677ff")
    skills = Column(ARRAY(String), default=[])
    commission_rate = Column(Numeric(5, 2), default=35)
    is_active = Column(Integer, default=1)
