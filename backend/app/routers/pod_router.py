from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..auth import get_current_user
from ..permissions import require_permission, assert_load_visible

router = APIRouter(prefix="/loads/{load_id}/pods", tags=["pods"])


@router.post("", response_model=schemas.PODOut)
def upload_pod(
    load_id: int,
    payload: schemas.PODCreate,
    request: Request,
    user: models.User = Depends(require_permission("pod.upload")),
    db: Session = Depends(get_db),
):
    load = db.query(models.Load).filter(models.Load.id == load_id).first()
    if not load:
        raise HTTPException(404, "Load not found")
    assert_load_visible(user, load, db, request)

    pod = models.POD(load_id=load_id, file_url=payload.file_url, uploaded_by_user_id=user.id)
    db.add(pod)
    db.commit()
    db.refresh(pod)
    return pod


@router.get("", response_model=list[schemas.PODOut])
def list_pods(load_id: int, request: Request, user: models.User = Depends(get_current_user),
              db: Session = Depends(get_db)):
    load = db.query(models.Load).filter(models.Load.id == load_id).first()
    if not load:
        raise HTTPException(404, "Load not found")
    assert_load_visible(user, load, db, request)
    return db.query(models.POD).filter(models.POD.load_id == load_id).all()
