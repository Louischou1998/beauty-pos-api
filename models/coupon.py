from sqlalchemy import Column, Integer, String, Numeric, DateTime
from database import Base


class Coupon(Base):
    __tablename__ = "coupons"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    type = Column(String(20), nullable=False)   # percent | fixed | free_service
    value = Column(Numeric(10, 2), nullable=False)   # percent: 0.1=10%, fixed: 200
    min_amount = Column(Numeric(10, 2), default=0)
    max_uses = Column(Integer, default=0)            # 0 = unlimited
    used_count = Column(Integer, default=0)
    valid_from = Column(DateTime, nullable=True)
    valid_until = Column(DateTime, nullable=True)
    is_active = Column(Integer, default=1)


class CouponUsage(Base):
    __tablename__ = "coupon_usages"

    id = Column(Integer, primary_key=True, index=True)
    coupon_id = Column(Integer, nullable=False)
    booking_id = Column(Integer, nullable=False)
    customer_id = Column(Integer, nullable=True)
    discount_amount = Column(Numeric(10, 2), nullable=False)
    used_at = Column(DateTime, default=__import__('datetime').datetime.utcnow)
