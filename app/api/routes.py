from typing import List, Optional
from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database import get_db
from app.models import System, AccessRole, User
from app.schemas import (
    SystemResponse, RoleResponse, RequestCreate,
    RequestDetailResponse, ApprovalDecision, UserResponse
)
from app.services.request_service import RequestService

router = APIRouter()

@router.get("/users", response_model=List[UserResponse])
async def list_users(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User))
    return list(result.scalars().all())

@router.get("/systems", response_model=List[SystemResponse])
async def list_systems(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(System))
    return list(result.scalars().all())

@router.get("/roles", response_model=List[RoleResponse])
async def list_roles(
    system_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    query = select(AccessRole)
    if system_id:
        query = query.where(AccessRole.system_id == system_id)
    result = await db.execute(query)
    return list(result.scalars().all())

@router.get("/requests", response_model=List[RequestDetailResponse])
async def list_requests(
    employee_id: Optional[int] = None,
    status_filter: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    service = RequestService(db)
    return await service.get_requests(
        employee_id=employee_id,
        status_filter=status_filter,
        limit=limit,
        offset=offset
    )

@router.post("/requests", response_model=RequestDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_request(
    data: RequestCreate,
    x_user_id: int = Header(1, alias="X-User-Id"),
    db: AsyncSession = Depends(get_db)
):
    service = RequestService(db)
    return await service.create_request(employee_id=x_user_id, data=data)

@router.get("/requests/{request_id}", response_model=RequestDetailResponse)
async def get_request(
    request_id: int,
    db: AsyncSession = Depends(get_db)
):
    service = RequestService(db)
    return await service.get_request_by_id(request_id)

@router.post("/requests/{request_id}/approve", response_model=RequestDetailResponse)
async def approve_request(
    request_id: int,
    decision_data: ApprovalDecision,
    x_user_id: int = Header(2, alias="X-User-Id"),
    db: AsyncSession = Depends(get_db)
):
    service = RequestService(db)
    return await service.process_approval(
        request_id=request_id,
        approver_id=x_user_id,
        decision_data=decision_data
    )

@router.post("/requests/{request_id}/cancel", response_model=RequestDetailResponse)
async def cancel_request(
    request_id: int,
    x_user_id: int = Header(1, alias="X-User-Id"),
    db: AsyncSession = Depends(get_db)
):
    service = RequestService(db)
    return await service.cancel_request(
        request_id=request_id,
        employee_id=x_user_id
    )

@router.post("/requests/{request_id}/retry", response_model=RequestDetailResponse)
async def retry_request(
    request_id: int,
    x_user_id: int = Header(4, alias="X-User-Id"),
    db: AsyncSession = Depends(get_db)
):
    service = RequestService(db)
    return await service.retry_provisioning(
        request_id=request_id,
        admin_id=x_user_id
    )
