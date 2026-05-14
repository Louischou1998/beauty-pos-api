from sqlalchemy import Column, Integer, String, Numeric, Text, DateTime, ForeignKey, Date
from database import Base


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)
    phone = Column(String(20), unique=True)
    email = Column(String(100))
    level = Column(String(20), default="一般")
    points = Column(Integer, default=0)
    balance = Column(Numeric(10, 2), default=0)
    total_spent = Column(Numeric(10, 2), default=0)
    visits = Column(Integer, default=0)
    # CRM 擴充
    allergy_info = Column(Text, default="")
    preferred_staff_id = Column(Integer, ForeignKey("staff.id"), nullable=True)
    revisit_days = Column(Integer, default=30)
    last_visit_at = Column(DateTime, nullable=True)
    birthday = Column(Date, nullable=True)
