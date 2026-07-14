from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..auth import get_current_user
from ..permissions import require_permission, assert_load_visible

router = APIRouter(prefix="/loads/{load_id}/rate-confirmations", tags=["rate-confirmations"])


@router.post("", response_model=schemas.RateConfirmationOut)
def confirm_rate(
    load_id: int,
    payload: schemas.RateConfirmationCreate,
    request: Request,
    user: models.User = Depends(require_permission("rate.confirm")),
    db: Session = Depends(get_db),
):
    load = db.query(models.Load).filter(models.Load.id == load_id).first()
    if not load:
        raise HTTPException(404, "Load not found")
    assert_load_visible(user, load, db, request)

    # Old confirmations are kept for history (versioned agreement); only
    # the latest is "current" and used for invoicing.
    prev = db.query(models.RateConfirmation).filter(
        models.RateConfirmation.load_id == load_id
    ).order_by(models.RateConfirmation.version.desc()).first()
    next_version = (prev.version + 1) if prev else 1

    if prev:
        prev.is_current = False

    rc = models.RateConfirmation(
        load_id=load_id,
        version=next_version,
        base_rate=payload.base_rate,
        accessorials=payload.accessorials,
        is_current=True,
        confirmed_by_user_id=user.id,
    )
    db.add(rc)
    db.commit()
    db.refresh(rc)
    return rc


@router.get("", response_model=list[schemas.RateConfirmationOut])
def list_rate_confirmations(load_id: int, request: Request,
                             user: models.User = Depends(get_current_user),
                             db: Session = Depends(get_db)):
    load = db.query(models.Load).filter(models.Load.id == load_id).first()
    if not load:
        raise HTTPException(404, "Load not found")
    assert_load_visible(user, load, db, request)
    return db.query(models.RateConfirmation).filter(
        models.RateConfirmation.load_id == load_id
    ).order_by(models.RateConfirmation.version).all()
