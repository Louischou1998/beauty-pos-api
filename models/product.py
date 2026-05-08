from sqlalchemy import Column, Integer, String, Numeric
from database import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    category = Column(String(50))
    price = Column(Numeric(10, 2), nullable=False)
    cost = Column(Numeric(10, 2), default=0)
    stock = Column(Integer, default=0)
    barcode = Column(String(50))
    is_active = Column(Integer, default=1)
