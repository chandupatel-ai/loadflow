import enum
import json
from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Boolean, ForeignKey, DateTime, Text, Float
)
from sqlalchemy.orm import relationship

from .database import Base

# ---------------------------------------------------------------------------
# Fixed permission catalog. Roles are BUNDLES of these. Code must always
# check permission strings, never role names.
# ---------------------------------------------------------------------------
PERMISSION_CATALOG = [
    "load.create",
    "load.assign_carrier",
    "load.override_compliance_flag",
    "rate.confirm",
    "load.update_status",
    "staff.manage",
    "pod.upload",
]

ORG_TYPE_BROKER = "broker"
ORG_TYPE_CARRIER = "carrier"

LOAD_STATES = [
    "Posted",
    "Carrier Assigned",
    "Rate Confirmed",
    "Dispatched",
    "In Transit",
    "Delivered",
    "POD Verified",
    "Invoiced/Closed",
]


class Org(Base):
    __tablename__ = "orgs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)  # broker | carrier

    users = relationship("User", back_populates="org")
    roles = relationship("Role", back_populates="org")


class Role(Base):
    """A named bundle of permissions, custom-defined per org by its admin."""
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("orgs.id"), nullable=False)
    name = Column(String, nullable=False)
    permissions_json = Column(Text, nullable=False, default="[]")

    org = relationship("Org", back_populates="roles")

    @property
    def permissions(self):
        return json.loads(self.permissions_json)

    @permissions.setter
    def permissions(self, value):
        self.permissions_json = json.dumps(value)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, default="")

    # account_type: "broker" | "carrier" | "shipper"
    account_type = Column(String, nullable=False)

    org_id = Column(Integer, ForeignKey("orgs.id"), nullable=True)  # null for shipper
    is_org_admin = Column(Boolean, default=False)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=True)  # staff custom role

    created_at = Column(DateTime, default=datetime.utcnow)

    org = relationship("Org", back_populates="users")
    role = relationship("Role")

    def get_permissions(self):
        """Org admins implicitly have all permissions within their org."""
        if self.account_type != "shipper" and self.is_org_admin:
            return set(PERMISSION_CATALOG)
        if self.role:
            return set(self.role.permissions)
        return set()


class CarrierComplianceRecord(Base):
    __tablename__ = "carrier_compliance_records"

    id = Column(Integer, primary_key=True, index=True)
    carrier_org_id = Column(Integer, ForeignKey("orgs.id"), nullable=False)
    insurance_expiry = Column(DateTime, nullable=True)
    mc_dot_authority_status = Column(String, default="active")  # active | expired | suspended
    approved_equipment_types_json = Column(Text, default="[]")
    approved_commodity_types_json = Column(Text, default="[]")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def approved_equipment_types(self):
        return json.loads(self.approved_equipment_types_json)

    @approved_equipment_types.setter
    def approved_equipment_types(self, value):
        self.approved_equipment_types_json = json.dumps(value)

    @property
    def approved_commodity_types(self):
        return json.loads(self.approved_commodity_types_json)

    @approved_commodity_types.setter
    def approved_commodity_types(self, value):
        self.approved_commodity_types_json = json.dumps(value)

    def is_compliant(self):
        if self.mc_dot_authority_status != "active":
            return False
        if self.insurance_expiry and self.insurance_expiry < datetime.utcnow():
            return False
        return True


class Load(Base):
    __tablename__ = "loads"

    id = Column(Integer, primary_key=True, index=True)
    shipper_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    broker_org_id = Column(Integer, ForeignKey("orgs.id"), nullable=False)
    carrier_org_id = Column(Integer, ForeignKey("orgs.id"), nullable=True)

    pickup_location = Column(String, nullable=False)
    delivery_location = Column(String, nullable=False)
    commodity = Column(String, default="")
    equipment_type = Column(String, default="")
    weight_lbs = Column(Float, default=0)

    status = Column(String, default="Posted")
    compliance_flag = Column(Boolean, default=False)  # True = blocked by compliance issue

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    rate_confirmations = relationship("RateConfirmation", back_populates="load")
    status_history = relationship("LoadStatusHistory", back_populates="load")
    pods = relationship("POD", back_populates="load")


class LoadStatusHistory(Base):
    __tablename__ = "load_status_history"

    id = Column(Integer, primary_key=True, index=True)
    load_id = Column(Integer, ForeignKey("loads.id"), nullable=False)
    from_status = Column(String, nullable=True)
    to_status = Column(String, nullable=False)
    changed_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    load = relationship("Load", back_populates="status_history")


class RateConfirmation(Base):
    __tablename__ = "rate_confirmations"

    id = Column(Integer, primary_key=True, index=True)
    load_id = Column(Integer, ForeignKey("loads.id"), nullable=False)
    version = Column(Integer, nullable=False, default=1)
    base_rate = Column(Float, nullable=False)
    accessorials = Column(Float, default=0)
    is_current = Column(Boolean, default=True)
    confirmed_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    confirmed_at = Column(DateTime, default=datetime.utcnow)

    load = relationship("Load", back_populates="rate_confirmations")


class POD(Base):
    __tablename__ = "pods"

    id = Column(Integer, primary_key=True, index=True)
    load_id = Column(Integer, ForeignKey("loads.id"), nullable=False)
    file_url = Column(String, nullable=False)
    uploaded_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    load = relationship("Load", back_populates="pods")


class PermissionDeniedLog(Base):
    __tablename__ = "permission_denied_log"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    endpoint = Column(String, nullable=False)
    required_permission = Column(String, nullable=True)
    reason = Column(String, default="")
    timestamp = Column(DateTime, default=datetime.utcnow)
