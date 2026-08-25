from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.project import Project
from app.models.user import OrganizationMember


def get_by_id(db: Session, project_id: str) -> Project | None:
    return db.get(Project, project_id)


def create(db: Session, *, organization_id: str, name: str, description: str | None) -> Project:
    project = Project(organization_id=organization_id, name=name, description=description)
    db.add(project)
    db.flush()
    return project


def list_for_user(
    db: Session, *, user_id: str, page: int, page_size: int
) -> tuple[list[Project], int]:
    """Projects belonging to any organization the user is a member of."""
    org_ids_subquery = (
        select(OrganizationMember.organization_id)
        .where(OrganizationMember.user_id == user_id)
        .subquery()
    )
    base_query = select(Project).where(Project.organization_id.in_(select(org_ids_subquery)))

    total = db.execute(
        select(func.count()).select_from(base_query.subquery())
    ).scalar_one()

    items = list(
        db.execute(
            base_query.order_by(Project.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).scalars()
    )
    return items, total


def delete(db: Session, project: Project) -> None:
    db.delete(project)
