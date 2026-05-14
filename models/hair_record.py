from sqlalchemy import Column, Integer, String, Text, Date, DateTime, ForeignKey, func
from database import Base


class HairRecord(Base):
    __tablename__ = "hair_records"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    staff_id = Column(Integer, ForeignKey("staff.id"), nullable=True)
    record_date = Column(Date, nullable=False)
    service_names = Column(Text, server_default="")
    color_formula = Column(Text, server_default="")
    hair_condition = Column(String(50), server_default="")
    notes = Column(Text, server_default="")
    created_at = Column(DateTime, server_default=func.now())
