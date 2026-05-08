from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey
from datetime import datetime
from database import Base


class InventoryItem(Base):
    __tablename__ = "inventory_items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    category = Column(String(50))
    unit = Column(String(20), default="個")
    quantity = Column(Numeric(10, 2), default=0)
    low_stock_threshold = Column(Numeric(10, 2), default=10)
    cost_per_unit = Column(Numeric(10, 2), default=0)


class InventoryUsage(Base):
    __tablename__ = "inventory_usage"

    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(Integer, ForeignKey("inventory_items.id"), nullable=False)
    booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=True)
    staff_id = Column(Integer, ForeignKey("staff.id"), nullable=True)
    quantity_used = Column(Numeric(10, 2), nullable=False)
    used_at = Column(DateTime, default=datetime.utcnow)
    note = Column(String(200))
