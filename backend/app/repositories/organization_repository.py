from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.base import OrgRole
from app.models.user import Organization, OrganizationMember


def get_by_id(db: Session, org_id: str) -> Organization | None:
    return db.get(Organization, org_id)


def get_by_slug(db: Session, slug: str) -> Organization | None:
    return db.execute(
        select(Organization).where(Organization.slug == slug)
    ).scalar_one_or_none()


def create(db: Session, *, name: str, slug: str) -> Organization:
    org = Organization(name=name, slug=slug)
    db.add(org)
    db.flush()
    return org


def add_member(db: Session, *, user_id: str, organization_id: str, role: OrgRole) -> OrganizationMember:
    member = OrganizationMember(user_id=user_id, organization_id=organization_id, role=role)
    db.add(member)
    db.flush()
    return member


def get_membership(db: Session, *, user_id: str, organization_id: str) -> OrganizationMember | None:
    return db.execute(
        select(OrganizationMember).where(
            OrganizationMember.user_id == user_id,
            OrganizationMember.organization_id == organization_id,
        )
    ).scalar_one_or_none()


def list_for_user(db: Session, *, user_id: str) -> list[OrganizationMember]:
    return list(
        db.execute(
            select(OrganizationMember).where(OrganizationMember.user_id == user_id)
        ).scalars()
    )
