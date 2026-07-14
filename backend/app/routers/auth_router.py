from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..auth import hash_password, verify_password, create_access_token, get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/bootstrap-org", response_model=schemas.Token)
def bootstrap_org(payload: schemas.OrgCreate, db: Session = Depends(get_db)):
    """Creates a new Broker or Carrier org along with its first Admin user.
    This is how a Broker/Carrier Admin account is created (vs. staff, who
    are invited by an existing admin)."""
    if payload.org_type not in (models.ORG_TYPE_BROKER, models.ORG_TYPE_CARRIER):
        raise HTTPException(400, "org_type must be 'broker' or 'carrier'")

    if db.query(models.User).filter(models.User.email == payload.admin_email).first():
        raise HTTPException(400, "Email already registered")

    org = models.Org(name=payload.org_name, type=payload.org_type)
    db.add(org)
    db.flush()

    admin = models.User(
        email=payload.admin_email,
        hashed_password=hash_password(payload.admin_password),
        full_name=payload.admin_full_name,
        account_type=payload.org_type,
        org_id=org.id,
        is_org_admin=True,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)

    token = create_access_token(admin.id)
    return schemas.Token(access_token=token)


@router.post("/signup-shipper", response_model=schemas.Token)
def signup_shipper(payload: schemas.ShipperCreate, db: Session = Depends(get_db)):
    if db.query(models.User).filter(models.User.email == payload.email).first():
        raise HTTPException(400, "Email already registered")

    user = models.User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        account_type="shipper",
        org_id=None,
        is_org_admin=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user.id)
    return schemas.Token(access_token=token)


@router.post("/login", response_model=schemas.Token)
def login(payload: schemas.LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(401, "Invalid email or password")
    token = create_access_token(user.id)
    return schemas.Token(access_token=token)


@router.get("/me", response_model=schemas.UserOut)
def me(user: models.User = Depends(get_current_user)):
    return user
