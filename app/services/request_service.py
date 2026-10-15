from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status

from app.models import Request, AccessRole, User, Approval
from app.schemas import RequestCreate, ApprovalDecision
from app.services.external_clients import hris_client, iam_client
from app.services.audit_service import AuditService

class RequestService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_requests(
        self,
        employee_id: Optional[int] = None,
        status_filter: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Request]:
        query = select(Request).options(
            selectinload(Request.approvals),
            selectinload(Request.audit_logs),
            selectinload(Request.role)
        ).order_by(Request.id.desc()).limit(limit).offset(offset)

        if employee_id:
            query = query.where(Request.employee_id == employee_id)
        if status_filter:
            query = query.where(Request.status == status_filter)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_request_by_id(self, request_id: int) -> Request:
        query = select(Request).options(
            selectinload(Request.approvals),
            selectinload(Request.audit_logs),
            selectinload(Request.role),
            selectinload(Request.employee)
        ).where(Request.id == request_id)
        result = await self.db.execute(query)
        req = result.scalar_one_or_none()
        if not req:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Заявка с ID {request_id} не найдена"
            )
        return req

    async def create_request(self, employee_id: int, data: RequestCreate) -> Request:
        is_active = await hris_client.is_employee_active(employee_id)
        if not is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Сотрудник заблокирован или уволен в кадровой системе (HRIS)"
            )

        role_query = select(AccessRole).where(
            AccessRole.id == data.role_id,
            AccessRole.is_active == True
        )
        role_res = await self.db.execute(role_query)
        role = role_res.scalar_one_or_none()
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Роль с ID {data.role_id} не найдена или неактивна"
            )

        existing_req_query = select(Request).where(
            Request.employee_id == employee_id,
            Request.role_id == data.role_id,
            Request.status.in_(["PENDING_MANAGER", "PENDING_OWNER", "PENDING_SECURITY", "APPROVED", "IN_PROVISIONING", "PROVISIONED"])
        )
        existing_res = await self.db.execute(existing_req_query)
        if existing_res.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Заявка на данную роль уже активна или находится на рассмотрении"
            )

        new_request = Request(
            employee_id=employee_id,
            role_id=data.role_id,
            status="PENDING_MANAGER",
            justification=data.justification,
            valid_to=data.valid_to
        )
        self.db.add(new_request)
        await self.db.commit()
        await self.db.refresh(new_request)

        await AuditService.log_action(
            db=self.db,
            request_id=new_request.id,
            actor_id=employee_id,
            action="CREATE_REQUEST",
            old_status=None,
            new_status="PENDING_MANAGER",
            details={
                "role_id": data.role_id,
                "role_code": role.code,
                "is_privileged": role.is_privileged,
                "justification": data.justification
            }
        )

        return await self.get_request_by_id(new_request.id)

    async def process_approval(
        self,
        request_id: int,
        approver_id: int,
        decision_data: ApprovalDecision
    ) -> Request:
        req = await self.get_request_by_id(request_id)

        if decision_data.decision == "REJECTED" and (not decision_data.comment or len(decision_data.comment.strip()) < 5):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="При отклонении заявки указание причины (не менее 5 символов) строго обязательно"
            )

        if req.status not in ["PENDING_MANAGER", "PENDING_OWNER", "PENDING_SECURITY"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Заявка в статусе {req.status} не может быть согласована или отклонена"
            )

        old_status = req.status
        current_step = old_status.replace("PENDING_", "")

        approval_record = Approval(
            request_id=req.id,
            step=current_step,
            approver_id=approver_id,
            status=decision_data.decision,
            comment=decision_data.comment
        )
        self.db.add(approval_record)

        if decision_data.decision == "REJECTED":
            req.status = "REJECTED"
        else:
            if old_status == "PENDING_MANAGER":
                if req.role.is_privileged:
                    req.status = "PENDING_OWNER"
                else:
                    req.status = "APPROVED"
            elif old_status == "PENDING_OWNER":
                req.status = "PENDING_SECURITY"
            elif old_status == "PENDING_SECURITY":
                req.status = "APPROVED"

        await self.db.commit()
        await self.db.refresh(req)

        await AuditService.log_action(
            db=self.db,
            request_id=req.id,
            actor_id=approver_id,
            action=f"APPROVAL_{decision_data.decision}",
            old_status=old_status,
            new_status=req.status,
            details={"step": current_step, "comment": decision_data.comment}
        )

        if req.status == "APPROVED":
            await self._execute_provisioning(req)

        return await self.get_request_by_id(req.id)

    async def cancel_request(self, request_id: int, employee_id: int) -> Request:
        req = await self.get_request_by_id(request_id)

        if req.employee_id != employee_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Сотрудник может отзывать только свои собственные заявки"
            )

        if req.status not in ["DRAFT", "PENDING_MANAGER", "PENDING_OWNER", "PENDING_SECURITY"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Невозможно отозвать заявку в статусе {req.status}"
            )

        old_status = req.status
        req.status = "CANCELLED"
        await self.db.commit()
        await self.db.refresh(req)

        await AuditService.log_action(
            db=self.db,
            request_id=req.id,
            actor_id=employee_id,
            action="CANCEL_REQUEST",
            old_status=old_status,
            new_status="CANCELLED"
        )

        return await self.get_request_by_id(req.id)

    async def _execute_provisioning(self, req: Request) -> None:
        old_status = req.status
        req.status = "IN_PROVISIONING"
        await self.db.commit()

        await AuditService.log_action(
            db=self.db,
            request_id=req.id,
            actor_id=None,
            action="PROVISIONING_STARTED",
            old_status=old_status,
            new_status="IN_PROVISIONING"
        )

        max_retries = 3
        attempts = 0
        last_error = None

        while attempts < max_retries:
            attempts += 1
            try:
                result = await iam_client.provision_access(
                    idempotency_key=str(req.request_uuid),
                    employee_id=req.employee_id,
                    system_code="CORE_BANKING",
                    role_code=req.role.code
                )
                req.status = "PROVISIONED"
                req.error_message = None
                await self.db.commit()

                await AuditService.log_action(
                    db=self.db,
                    request_id=req.id,
                    actor_id=None,
                    action="PROVISIONING_SUCCESS",
                    old_status="IN_PROVISIONING",
                    new_status="PROVISIONED",
                    details=result
                )
                return
            except Exception as e:
                last_error = str(e)

        req.status = "FAILED"
        req.error_message = f"Provisioning failed after {max_retries} attempts: {last_error}"
        await self.db.commit()

        await AuditService.log_action(
            db=self.db,
            request_id=req.id,
            actor_id=None,
            action="PROVISIONING_FAILED",
            old_status="IN_PROVISIONING",
            new_status="FAILED",
            details={"error": last_error, "attempts": attempts}
        )

    async def retry_provisioning(self, request_id: int, admin_id: int) -> Request:
        req = await self.get_request_by_id(request_id)
        if req.status != "FAILED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Повторный запуск доступен только для заявок в статусе FAILED (текущий: {req.status})"
            )

        await AuditService.log_action(
            db=self.db,
            request_id=req.id,
            actor_id=admin_id,
            action="PROVISIONING_MANUAL_RETRY",
            old_status="FAILED",
            new_status="IN_PROVISIONING"
        )

        await self._execute_provisioning(req)
        return await self.get_request_by_id(req.id)
