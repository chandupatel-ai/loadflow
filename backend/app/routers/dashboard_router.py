from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db
from ..auth import get_current_user

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary")
def dashboard_summary(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.account_type == "broker":
        loads = db.query(models.Load).filter(models.Load.broker_org_id == user.org_id).all()
    elif user.account_type == "carrier":
        loads = db.query(models.Load).filter(models.Load.carrier_org_id == user.org_id).all()
    elif user.account_type == "shipper":
        loads = db.query(models.Load).filter(models.Load.shipper_id == user.id).all()
    else:
        raise HTTPException(403, "Unknown account type")

    by_status = {}
    for l in loads:
        by_status[l.status] = by_status.get(l.status, 0) + 1

    alerts = [l.id for l in loads if l.compliance_flag]

    return {
        "account_type": user.account_type,
        "total_loads": len(loads),
        "by_status": by_status,
        "compliance_alerts": alerts,
    }


@router.get("/carriers")
def list_carriers(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Broker directory of carrier orgs, with compliance status, for the
    assign-carrier flow."""
    if user.account_type != "broker":
        raise HTTPException(403, "Only broker accounts browse the carrier directory")

    carriers = db.query(models.Org).filter(models.Org.type == "carrier").all()
    result = []
    for c in carriers:
        rec = db.query(models.CarrierComplianceRecord).filter(
            models.CarrierComplianceRecord.carrier_org_id == c.id
        ).first()
        result.append({
            "org_id": c.id,
            "name": c.name,
            "is_compliant": rec.is_compliant() if rec else False,
        })
    return result


@router.get("/audit-log")
def audit_log(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Stretch: permission-denied audit log, org admins only."""
    if not user.is_org_admin:
        raise HTTPException(403, "Only org admins can view the audit log")
    rows = db.query(models.PermissionDeniedLog).order_by(
        models.PermissionDeniedLog.timestamp.desc()
    ).limit(200).all()
    return [
        {
            "user_id": r.user_id,
            "endpoint": r.endpoint,
            "required_permission": r.required_permission,
            "reason": r.reason,
            "timestamp": r.timestamp,
        }
        for r in rows
    ]
