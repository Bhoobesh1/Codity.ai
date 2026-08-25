from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError, NotFoundError
from app.models.project import Project
from app.repositories import organization_repository, project_repository


def _require_org_membership(db: Session, *, user_id: str, organization_id: str) -> None:
    if organization_repository.get_membership(
        db, user_id=user_id, organization_id=organization_id
    ) is None:
        raise ForbiddenError("You are not a member of this organization.")


def create_project(
    db: Session, *, user_id: str, organization_id: str, name: str, description: str | None
) -> Project:
    _require_org_membership(db, user_id=user_id, organization_id=organization_id)
    project = project_repository.create(
        db, organization_id=organization_id, name=name, description=description
    )
    db.commit()
    db.refresh(project)
    return project


def get_project_for_user(db: Session, *, user_id: str, project_id: str) -> Project:
    project = project_repository.get_by_id(db, project_id)
    # Return the same 404 whether the project doesn't exist or the user
    # just isn't authorized to see it -- this avoids leaking which
    # project IDs exist to users who don't have access to them.
    if project is None:
        raise NotFoundError("Project not found.")
    if organization_repository.get_membership(
        db, user_id=user_id, organization_id=project.organization_id
    ) is None:
        raise NotFoundError("Project not found.")
    return project


def list_projects_for_user(
    db: Session, *, user_id: str, page: int, page_size: int
) -> tuple[list[Project], int]:
    return project_repository.list_for_user(db, user_id=user_id, page=page, page_size=page_size)


def update_project(
    db: Session,
    *,
    user_id: str,
    project_id: str,
    name: str | None,
    description: str | None,
) -> Project:
    project = get_project_for_user(db, user_id=user_id, project_id=project_id)
    if name is not None:
        project.name = name
    if description is not None:
        project.description = description
    db.commit()
    db.refresh(project)
    return project


def delete_project(db: Session, *, user_id: str, project_id: str) -> None:
    project = get_project_for_user(db, user_id=user_id, project_id=project_id)
    project_repository.delete(db, project)
    db.commit()
