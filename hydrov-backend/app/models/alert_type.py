from sqlalchemy import Integer, String, Text, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class AlertType(Base):
    __tablename__ = "alert_types"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    default_severity: Mapped[str] = mapped_column(String(20), CheckConstraint("default_severity IN ('low', 'medium', 'high', 'critical')", name="chk_alert_type_d6793d"), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
