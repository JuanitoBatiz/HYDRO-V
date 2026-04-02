from sqlalchemy import Integer, String, Text, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class ValveType(Base):
    __tablename__ = "valve_types"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    default_state: Mapped[str] = mapped_column(String(10), CheckConstraint("default_state IN ('open', 'closed')", name="chk_valve_type_3d5456"), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
