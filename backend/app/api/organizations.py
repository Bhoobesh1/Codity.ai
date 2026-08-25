from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.organization import OrganizationCreate, OrganizationOut
from app.services import organization_service

router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.post("", response_model=OrganizationOut, status_code=status.HTTP_201_CREATED)
def create_organization(
    payload: OrganizationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OrganizationOut:
    org = organization_service.create_organization(db, user_id=current_user.id, name=payload.name)
    return OrganizationOut(id=org.id, name=org.name, slug=org.slug, role="owner")


@router.get("", response_model=list[OrganizationOut])
def list_organizations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[OrganizationOut]:
    orgs = organization_service.list_organizations_for_user(db, user_id=current_user.id)
    return [
        OrganizationOut(id=org.id, name=org.name, slug=org.slug, role=role) for org, role in orgs
    ]
