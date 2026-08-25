from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, generate_uuid


class Project(Base, TimestampMixin):
    __tablename__ = "projects"
    __table_args__ = (
        # A given org shouldn't have two projects with the same name.
        UniqueConstraint("organization_id", "name", name="uq_project_org_name"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    organization_id: Mapped[str] = mapped_column(
        String, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    organization: Mapped["Organization"] = relationship(back_populates="projects")  # noqa: F821
    # Cascade note: deleting a Project deletes its Queues -- queues are
    # meaningless without a parent project.
    queues: Mapped[list["Queue"]] = relationship(  # noqa: F821
        back_populates="project", cascade="all, delete-orphan"
    )
