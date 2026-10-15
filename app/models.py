import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, ForeignKey, Text, JSON
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base

def utc_now():
    return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False)
    full_name = Column(String(150), nullable=False)
    role = Column(String(30), nullable=False, default="EMPLOYEE")
    department = Column(String(100), nullable=False)
    manager_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    owned_systems = relationship("System", back_populates="owner")
    requests = relationship("Request", back_populates="employee")
    approvals = relationship("Approval", back_populates="approver")


class System(Base):
    __tablename__ = "systems"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    owner = relationship("User", back_populates="owned_systems")
    roles = relationship("AccessRole", back_populates="system")


class AccessRole(Base):
    __tablename__ = "access_roles"

    id = Column(Integer, primary_key=True, index=True)
    system_id = Column(Integer, ForeignKey("systems.id"), nullable=False)
    code = Column(String(50), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    is_privileged = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    system = relationship("System", back_populates="roles")
    requests = relationship("Request", back_populates="role")


class Request(Base):
    __tablename__ = "requests"

    id = Column(Integer, primary_key=True, index=True)
    request_uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False, index=True)
    employee_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    role_id = Column(Integer, ForeignKey("access_roles.id"), nullable=False, index=True)
    status = Column(String(30), nullable=False, default="PENDING_MANAGER", index=True)
    justification = Column(Text, nullable=False)
    valid_to = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    employee = relationship("User", back_populates="requests")
    role = relationship("AccessRole", back_populates="requests")
    approvals = relationship("Approval", back_populates="request", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="request", cascade="all, delete-orphan")


class Approval(Base):
    __tablename__ = "approvals"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(Integer, ForeignKey("requests.id"), nullable=False, index=True)
    step = Column(String(30), nullable=False)
    approver_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String(20), nullable=False)
    comment = Column(Text, nullable=True)
    action_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    request = relationship("Request", back_populates="approvals")
    approver = relationship("User", back_populates="approvals")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(Integer, ForeignKey("requests.id"), nullable=True, index=True)
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(50), nullable=False, index=True)
    old_status = Column(String(30), nullable=True)
    new_status = Column(String(30), nullable=True)
    details = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    request = relationship("Request", back_populates="audit_logs")
