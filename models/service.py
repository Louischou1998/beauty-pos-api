from sqlalchemy import Column, Integer, String, Numeric
from database import Base


class ServiceCategory(Base):
    __tablename__ = "service_categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)


class Service(Base):
    __tablename__ = "services"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    category_id = Column(Integer)
    duration = Column(Integer, nullable=False)   # minutes
    price = Column(Numeric(10, 2), nullable=False)
    is_active = Column(Integer, default=1)
