from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr


# ---------- Auth ----------
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# ---------- Org / bootstrap ----------
class OrgCreate(BaseModel):
    org_name: str
    org_type: str  # broker | carrier
    admin_email: EmailStr
    admin_password: str
    admin_full_name: str = ""


class ShipperCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str = ""


# ---------- Roles ----------
class RoleCreate(BaseModel):
    name: str
    permissions: List[str]


class RoleOut(BaseModel):
    id: int
    name: str
    permissions: List[str]

    class Config:
        from_attributes = True


# ---------- Staff ----------
class StaffInvite(BaseModel):
    email: EmailStr
    password: str
    full_name: str = ""
    role_id: int


class UserOut(BaseModel):
    id: int
    email: str
    full_name: str
    account_type: str
    org_id: Optional[int]
    is_org_admin: bool
    role_id: Optional[int]

    class Config:
        from_attributes = True


# ---------- Compliance ----------
class ComplianceUpsert(BaseModel):
    insurance_expiry: Optional[datetime] = None
    mc_dot_authority_status: str = "active"
    approved_equipment_types: List[str] = []
    approved_commodity_types: List[str] = []


class ComplianceOut(BaseModel):
    id: int
    carrier_org_id: int
    insurance_expiry: Optional[datetime]
    mc_dot_authority_status: str
    approved_equipment_types: List[str]
    approved_commodity_types: List[str]
    is_compliant: bool

    class Config:
        from_attributes = True


# ---------- Loads ----------
class LoadCreate(BaseModel):
    pickup_location: str
    delivery_location: str
    commodity: str = ""
    equipment_type: str = ""
    weight_lbs: float = 0


class LoadOut(BaseModel):
    id: int
    shipper_id: int
    broker_org_id: int
    carrier_org_id: Optional[int]
    pickup_location: str
    delivery_location: str
    commodity: str
    equipment_type: str
    weight_lbs: float
    status: str
    compliance_flag: bool
    created_at: datetime

    class Config:
        from_attributes = True


class AssignCarrierRequest(BaseModel):
    carrier_org_id: int


class StatusUpdateRequest(BaseModel):
    to_status: str


# ---------- Rate confirmation ----------
class RateConfirmationCreate(BaseModel):
    base_rate: float
    accessorials: float = 0


class RateConfirmationOut(BaseModel):
    id: int
    load_id: int
    version: int
    base_rate: float
    accessorials: float
    is_current: bool
    confirmed_at: datetime

    class Config:
        from_attributes = True


# ---------- POD ----------
class PODCreate(BaseModel):
    file_url: str


class PODOut(BaseModel):
    id: int
    load_id: int
    file_url: str
    uploaded_at: datetime

    class Config:
        from_attributes = True
