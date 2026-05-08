from sqlalchemy import Column, Integer, String, Numeric, DateTime, Boolean, ForeignKey
from datetime import datetime
from database import Base


class Commission(Base):
    __tablename__ = "commissions"

    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=False)
    staff_id = Column(Integer, ForeignKey("staff.id"), nullable=False)
    type = Column(String(20), nullable=False)        # service | product
    item_name = Column(String(100))
    is_designated = Column(Boolean, default=False)   # 指定技師加成
    base_amount = Column(Numeric(10, 2), nullable=False)
    commission_rate = Column(Numeric(5, 2), nullable=False)
    commission_amount = Column(Numeric(10, 2), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
