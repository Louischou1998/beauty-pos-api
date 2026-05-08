from sqlalchemy import Column, Integer, String, Date, ForeignKey, UniqueConstraint
from database import Base


class StaffSchedule(Base):
    __tablename__ = "staff_schedules"
    __table_args__ = (UniqueConstraint("staff_id", "work_date", name="uq_staff_schedule_date"),)

    id = Column(Integer, primary_key=True, index=True)
    staff_id = Column(Integer, ForeignKey("staff.id"), nullable=False, index=True)
    work_date = Column(Date, nullable=False, index=True)
    shift_type = Column(String(20), nullable=False)  # morning | afternoon | full | off

