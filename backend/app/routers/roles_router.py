from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..auth import get_current_user, hash_password
from ..permissions import require_org_type

router = APIRouter(prefix="/roles", tags=["roles"])


def _require_admin(user: models.User = Depends(get_current_user)) -> models.User:
    # Only org admins manage roles/staff (bootstrap constraint, separate
    # from the general permission catalog since role-creation itself
    # controls the permission catalog).
    if user.account_type not in ("broker", "carrier") or not user.is_org_admin:
        raise HTTPException(403, "Only an org admin can manage roles/staff")
    return user


@router.get("/permission-catalog")
def permission_catalog():
    return {"permissions": models.PERMISSION_CATALOG}


@router.post("", response_model=schemas.RoleOut)
def create_role(payload: schemas.RoleCreate, admin: models.User = Depends(_require_admin),
                 db: Session = Depends(get_db)):
    invalid = [p for p in payload.permissions if p not in models.PERMISSION_CATALOG]
    if invalid:
        raise HTTPException(400, f"Unknown permissions: {invalid}")

    role = models.Role(org_id=admin.org_id, name=payload.name)
    role.permissions = payload.permissions
    db.add(role)
    db.commit()
    db.refresh(role)
    return role


@router.get("", response_model=list[schemas.RoleOut])
def list_roles(admin: models.User = Depends(_require_admin), db: Session = Depends(get_db)):
    return db.query(models.Role).filter(models.Role.org_id == admin.org_id).all()


@router.post("/staff", response_model=schemas.UserOut)
def invite_staff(payload: schemas.StaffInvite, admin: models.User = Depends(_require_admin),
                  db: Session = Depends(get_db)):
    role = db.query(models.Role).filter(
        models.Role.id == payload.role_id, models.Role.org_id == admin.org_id
    ).first()
    if not role:
        raise HTTPException(404, "Role not found in your org")

    if db.query(models.User).filter(models.User.email == payload.email).first():
        raise HTTPException(400, "Email already registered")

    staff = models.User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        account_type=admin.account_type,
        org_id=admin.org_id,
        is_org_admin=False,
        role_id=role.id,
    )
    db.add(staff)
    db.commit()
    db.refresh(staff)
    return staff


@router.get("/staff", response_model=list[schemas.UserOut])
def list_staff(admin: models.User = Depends(_require_admin), db: Session = Depends(get_db)):
    return db.query(models.User).filter(models.User.org_id == admin.org_id).all()
