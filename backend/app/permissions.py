"""
Core RBAC enforcement.

IMPORTANT DESIGN RULE: every check here operates on PERMISSION STRINGS
(from models.PERMISSION_CATALOG), never on role names. Role names are just
a human label an org admin puts on a bundle of permissions.

Enforcement happens at the API layer (FastAPI dependencies), not just in
the UI, so a lower-privileged account hitting a restricted endpoint
directly is blocked here regardless of what the frontend shows.
"""
from fastapi import Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from . import models
from .auth import get_current_user
from .database import get_db


def _log_denied(db: Session, user: models.User, endpoint: str, permission: str, reason: str):
    entry = models.PermissionDeniedLog(
        user_id=user.id if user else None,
        endpoint=endpoint,
        required_permission=permission,
        reason=reason,
    )
    db.add(entry)
    db.commit()
    # Also mirror to console/log file per spec ("console/log file is fine")
    print(f"[PERMISSION DENIED] user={user.id if user else None} "
          f"endpoint={endpoint} required={permission} reason={reason}")


def require_permission(permission: str):
    """FastAPI dependency factory: blocks the request unless the current
    user holds `permission` (via org-admin blanket access or an assigned
    custom role)."""

    def dependency(
        request: Request,
        db: Session = Depends(get_db),
        user: models.User = Depends(get_current_user),
    ) -> models.User:
        if permission not in user.get_permissions():
            _log_denied(db, user, str(request.url.path), permission, "missing permission")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required permission: {permission}",
            )
        return user

    return dependency


def require_org_type(*allowed_types: str):
    """Restrict an endpoint to specific account types (e.g. broker-only)."""

    def dependency(
        request: Request,
        db: Session = Depends(get_db),
        user: models.User = Depends(get_current_user),
    ) -> models.User:
        if user.account_type not in allowed_types:
            _log_denied(db, user, str(request.url.path), None,
                        f"account_type {user.account_type} not in {allowed_types}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your account type cannot access this endpoint",
            )
        return user

    return dependency


def assert_load_visible(user: models.User, load: models.Load, db: Session, request: Request):
    """Object-level scoping: shippers see only their own loads; carrier
    staff see only their own carrier org's loads; broker staff see only
    their own broker org's loads."""
    visible = False
    if user.account_type == "shipper" and load.shipper_id == user.id:
        visible = True
    elif user.account_type == "broker" and user.org_id == load.broker_org_id:
        visible = True
    elif user.account_type == "carrier" and load.carrier_org_id is not None \
            and user.org_id == load.carrier_org_id:
        visible = True

    if not visible:
        _log_denied(db, user, str(request.url.path), None, "object-level scope violation")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your load")
