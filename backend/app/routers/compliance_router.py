from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..auth import get_current_user

router = APIRouter(prefix="/compliance", tags=["compliance"])


def _to_out(rec: models.CarrierComplianceRecord) -> schemas.ComplianceOut:
    return schemas.ComplianceOut(
        id=rec.id,
        carrier_org_id=rec.carrier_org_id,
        insurance_expiry=rec.insurance_expiry,
        mc_dot_authority_status=rec.mc_dot_authority_status,
        approved_equipment_types=rec.approved_equipment_types,
        approved_commodity_types=rec.approved_commodity_types,
        is_compliant=rec.is_compliant(),
    )


@router.put("/me", response_model=schemas.ComplianceOut)
def upsert_my_compliance(payload: schemas.ComplianceUpsert,
                          user: models.User = Depends(get_current_user),
                          db: Session = Depends(get_db)):
    """Carrier org admin (or staff with staff.manage) updates their own
    org's compliance record."""
    if user.account_type != "carrier":
        raise HTTPException(403, "Only carrier accounts have compliance records")
    if not (user.is_org_admin or "staff.manage" in user.get_permissions()):
        raise HTTPException(403, "Missing permission to edit compliance record")

    rec = db.query(models.CarrierComplianceRecord).filter(
        models.CarrierComplianceRecord.carrier_org_id == user.org_id
    ).first()
    if not rec:
        rec = models.CarrierComplianceRecord(carrier_org_id=user.org_id)
        db.add(rec)

    rec.insurance_expiry = payload.insurance_expiry
    rec.mc_dot_authority_status = payload.mc_dot_authority_status
    rec.approved_equipment_types = payload.approved_equipment_types
    rec.approved_commodity_types = payload.approved_commodity_types
    db.commit()
    db.refresh(rec)
    return _to_out(rec)


@router.get("/me", response_model=schemas.ComplianceOut)
def get_my_compliance(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.account_type != "carrier":
        raise HTTPException(403, "Only carrier accounts have compliance records")
    rec = db.query(models.CarrierComplianceRecord).filter(
        models.CarrierComplianceRecord.carrier_org_id == user.org_id
    ).first()
    if not rec:
        raise HTTPException(404, "No compliance record yet")
    return _to_out(rec)


@router.get("/{carrier_org_id}", response_model=schemas.ComplianceOut)
def get_carrier_compliance(carrier_org_id: int, user: models.User = Depends(get_current_user),
                            db: Session = Depends(get_db)):
    """Brokers look up a carrier's compliance before/while assigning them."""
    if user.account_type != "broker":
        raise HTTPException(403, "Only broker accounts can view other carriers' compliance")
    rec = db.query(models.CarrierComplianceRecord).filter(
        models.CarrierComplianceRecord.carrier_org_id == carrier_org_id
    ).first()
    if not rec:
        raise HTTPException(404, "No compliance record for this carrier")
    return _to_out(rec)
