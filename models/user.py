from sqlalchemy import Column, Integer, String
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    hashed_password = Column(String(200), nullable=False)
    role = Column(String(20), default="staff")   # admin | staff
    staff_id = Column(Integer, nullable=True)    # 關聯到 staff 表（技師帳號用）
    is_active = Column(Integer, default=1)
