from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError
from app.models.base import OrgRole
from app.models.user import Organization
from app.repositories import organization_repository
from app.schemas.organization import slugify


def create_organization(db: Session, *, user_id: str, name: str) -> Organization:
    base_slug = slugify(name)
    slug = base_slug
    suffix = 1
    # Slugs must be unique; if "acme" is taken, try "acme-2", "acme-3", ...
    while organization_repository.get_by_slug(db, slug) is not None:
        suffix += 1
        slug = f"{base_slug}-{suffix}"
        if suffix > 50:  # sanity guard against pathological loops
            raise ConflictError("Could not generate a unique slug for this organization name.")

    org = organization_repository.create(db, name=name, slug=slug)
    organization_repository.add_member(
        db, user_id=user_id, organization_id=org.id, role=OrgRole.OWNER
    )
    db.commit()
    db.refresh(org)
    return org


def list_organizations_for_user(db: Session, *, user_id: str) -> list[tuple[Organization, str]]:
    memberships = organization_repository.list_for_user(db, user_id=user_id)
    return [(m.organization, m.role.value) for m in memberships]
