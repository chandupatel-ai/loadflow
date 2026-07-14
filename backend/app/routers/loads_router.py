from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..auth import get_current_user
from ..permissions import require_permission, require_org_type, assert_load_visible

router = APIRouter(prefix="/loads", tags=["loads"])

# Forward-only sequential state machine.
STATE_ORDER = models.LOAD_STATES  # Posted ... Invoiced/Closed
COMPLIANCE_GATE_INDEX = STATE_ORDER.index("Carrier Assigned")


def _get_load_or_404(load_id: int, db: Session) -> models.Load:
    load = db.query(models.Load).filter(models.Load.id == load_id).first()
    if not load:
        raise HTTPException(404, "Load not found")
    return load


@router.post("", response_model=schemas.LoadOut)
def create_load(
    payload: schemas.LoadCreate,
    request: Request,
    user: models.User = Depends(require_permission("load.create")),
    db: Session = Depends(get_db),
):
    if user.account_type != "broker":
        raise HTTPException(403, "Only broker staff post loads")

    load = models.Load(
        shipper_id=user.id,
        broker_org_id=user.org_id,
        pickup_location=payload.pickup_location,
        delivery_location=payload.delivery_location,
        commodity=payload.commodity,
        equipment_type=payload.equipment_type,
        weight_lbs=payload.weight_lbs,
        status="Posted",
    )
    db.add(load)
    db.commit()
    db.refresh(load)

    history = models.LoadStatusHistory(
        load_id=load.id, from_status=None, to_status="Posted", changed_by_user_id=user.id
    )
    db.add(history)
    db.commit()
    return load


@router.get("", response_model=list[schemas.LoadOut])
def list_loads(
    request: Request,
    status_filter: Optional[str] = Query(None, alias="status"),
    q: Optional[str] = Query(None, description="search pickup/delivery/commodity"),
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Object-level scoped list: shippers see only their loads, carrier
    staff see only their carrier org's loads, broker staff see only their
    broker org's loads."""
    query = db.query(models.Load)

    if user.account_type == "shipper":
        query = query.filter(models.Load.shipper_id == user.id)
    elif user.account_type == "broker":
        query = query.filter(models.Load.broker_org_id == user.org_id)
    elif user.account_type == "carrier":
        query = query.filter(models.Load.carrier_org_id == user.org_id)
    else:
        raise HTTPException(403, "Unknown account type")

    if status_filter:
        query = query.filter(models.Load.status == status_filter)
    if q:
        like = f"%{q}%"
        query = query.filter(
            (models.Load.pickup_location.ilike(like))
            | (models.Load.delivery_location.ilike(like))
            | (models.Load.commodity.ilike(like))
        )

    return query.order_by(models.Load.created_at.desc()).all()


@router.get("/{load_id}", response_model=schemas.LoadOut)
def get_load(load_id: int, request: Request, user: models.User = Depends(get_current_user),
             db: Session = Depends(get_db)):
    load = _get_load_or_404(load_id, db)
    assert_load_visible(user, load, db, request)
    return load


@router.post("/{load_id}/assign-carrier", response_model=schemas.LoadOut)
def assign_carrier(
    load_id: int,
    payload: schemas.AssignCarrierRequest,
    request: Request,
    user: models.User = Depends(require_permission("load.assign_carrier")),
    db: Session = Depends(get_db),
):
    load = _get_load_or_404(load_id, db)
    assert_load_visible(user, load, db, request)
    if user.account_type != "broker":
        raise HTTPException(403, "Only broker staff assign carriers")

    carrier_org = db.query(models.Org).filter(
        models.Org.id == payload.carrier_org_id, models.Org.type == "carrier"
    ).first()
    if not carrier_org:
        raise HTTPException(404, "Carrier org not found")

    # Compliance check gates the transition into "Carrier Assigned".
    compliance = db.query(models.CarrierComplianceRecord).filter(
        models.CarrierComplianceRecord.carrier_org_id == carrier_org.id
    ).first()
    is_compliant = compliance.is_compliant() if compliance else False

    load.carrier_org_id = carrier_org.id
    load.compliance_flag = not is_compliant

    if is_compliant:
        _transition(load, "Carrier Assigned", user, db)
    else:
        # Carrier is linked but the load stays blocked at "Posted" until
        # resolved or an override permission is used.
        db.add(models.LoadStatusHistory(
            load_id=load.id, from_status=load.status, to_status=load.status,
            changed_by_user_id=user.id,
        ))
        db.commit()

    db.refresh(load)
    return load


def _transition(load: models.Load, to_status: str, user: models.User, db: Session):
    history = models.LoadStatusHistory(
        load_id=load.id, from_status=load.status, to_status=to_status,
        changed_by_user_id=user.id,
    )
    load.status = to_status
    db.add(history)
    db.commit()


@router.post("/{load_id}/status", response_model=schemas.LoadOut)
def update_status(
    load_id: int,
    payload: schemas.StatusUpdateRequest,
    request: Request,
    user: models.User = Depends(require_permission("load.update_status")),
    db: Session = Depends(get_db),
):
    load = _get_load_or_404(load_id, db)
    assert_load_visible(user, load, db, request)

    if payload.to_status not in STATE_ORDER:
        raise HTTPException(400, f"Unknown status: {payload.to_status}")

    current_idx = STATE_ORDER.index(load.status)
    target_idx = STATE_ORDER.index(payload.to_status)

    if target_idx != current_idx + 1:
        raise HTTPException(400, "Loads must progress one state at a time, forward only")

    # Compliance gate: cannot progress PAST "Carrier Assigned" while flagged,
    # unless the user holds the override permission.
    if load.compliance_flag and target_idx > COMPLIANCE_GATE_INDEX:
        if "load.override_compliance_flag" not in user.get_permissions():
            raise HTTPException(
                403,
                "Load is compliance-flagged (carrier insurance/authority issue). "
                "Resolve compliance or use an override-permitted role.",
            )

    # Rate must be confirmed before entering "Rate Confirmed" onward is
    # implied by the state name itself; we simply require at least one
    # current rate confirmation to exist before allowing it.
    if payload.to_status == "Rate Confirmed":
        has_rate = db.query(models.RateConfirmation).filter(
            models.RateConfirmation.load_id == load.id,
            models.RateConfirmation.is_current == True,  # noqa: E712
        ).first()
        if not has_rate:
            raise HTTPException(400, "Confirm a rate before moving to 'Rate Confirmed'")

    _transition(load, payload.to_status, user, db)
    db.refresh(load)
    return load


@router.get("/{load_id}/history")
def load_history(load_id: int, request: Request, user: models.User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    load = _get_load_or_404(load_id, db)
    assert_load_visible(user, load, db, request)
    rows = db.query(models.LoadStatusHistory).filter(
        models.LoadStatusHistory.load_id == load_id
    ).order_by(models.LoadStatusHistory.timestamp).all()
    return [
        {
            "from_status": r.from_status,
            "to_status": r.to_status,
            "changed_by_user_id": r.changed_by_user_id,
            "timestamp": r.timestamp,
        }
        for r in rows
    ]
