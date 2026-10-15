from datetime import datetime
from uuid import UUID
from typing import Optional, List
from pydantic import BaseModel, Field, EmailStr, ConfigDict

class UserBase(BaseModel):
    username: str
    email: EmailStr
    full_name: str
    role: str
    department: str
    is_active: bool = True

class UserCreate(UserBase):
    manager_id: Optional[int] = None

class UserResponse(UserBase):
    id: int
    manager_id: Optional[int] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class SystemBase(BaseModel):
    code: str
    name: str
    description: Optional[str] = None
    is_active: bool = True

class SystemCreate(SystemBase):
    owner_id: int

class SystemResponse(SystemBase):
    id: int
    owner_id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class RoleBase(BaseModel):
    code: str
    name: str
    description: Optional[str] = None
    is_privileged: bool = False
    is_active: bool = True

class RoleCreate(RoleBase):
    system_id: int

class RoleResponse(RoleBase):
    id: int
    system_id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class RequestCreate(BaseModel):
    role_id: int
    justification: str = Field(..., min_length=10)
    valid_to: Optional[datetime] = None

class ApprovalDecision(BaseModel):
    decision: str = Field(..., pattern="^(APPROVED|REJECTED)$")
    comment: Optional[str] = None

class ApprovalResponse(BaseModel):
    id: int
    step: str
    approver_id: int
    status: str
    comment: Optional[str] = None
    action_at: datetime
    model_config = ConfigDict(from_attributes=True)

class AuditLogResponse(BaseModel):
    id: int
    action: str
    old_status: Optional[str] = None
    new_status: Optional[str] = None
    details: Optional[dict] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class RequestDetailResponse(BaseModel):
    id: int
    request_uuid: UUID
    employee_id: int
    role_id: int
    status: str
    justification: str
    valid_to: Optional[datetime] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    approvals: List[ApprovalResponse] = []
    audit_logs: List[AuditLogResponse] = []
    model_config = ConfigDict(from_attributes=True)
