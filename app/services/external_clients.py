from typing import Dict, Any, Optional

class HrisClient:
    def __init__(self):
        self.mock_registry: Dict[int, Dict[str, Any]] = {
            1: {
                "id": 1,
                "username": "ivanov_ii",
                "full_name": "Иванов Иван Иванович",
                "department": "Департамент расчетных операций",
                "status": "ACTIVE",
                "manager_id": 2
            },
            2: {
                "id": 2,
                "username": "petrov_pp",
                "full_name": "Петров Петр Петрович",
                "department": "Департамент расчетных операций",
                "status": "ACTIVE",
                "manager_id": None
            },
            3: {
                "id": 3,
                "username": "sidorov_ss",
                "full_name": "Сидоров Сидор Сидорович",
                "department": "Управление информационных систем",
                "status": "ACTIVE",
                "manager_id": None
            },
            4: {
                "id": 4,
                "username": "kuznetsov_ib",
                "full_name": "Кузнецов Игорь Борисович",
                "department": "Служба информационной безопасности",
                "status": "ACTIVE",
                "manager_id": None
            },
            5: {
                "id": 5,
                "username": "dismissed_emp",
                "full_name": "Бывший Сотрудник",
                "department": "Архив",
                "status": "DISMISSED",
                "manager_id": 2
            }
        }

    async def get_employee(self, employee_id: int) -> Optional[Dict[str, Any]]:
        return self.mock_registry.get(employee_id)

    async def is_employee_active(self, employee_id: int) -> bool:
        emp = await self.get_employee(employee_id)
        if not emp:
            return False
        return emp.get("status") == "ACTIVE"


class IamClient:
    def __init__(self):
        self.processed_idempotency_keys: Dict[str, Dict[str, Any]] = {}
        self.fail_mode: bool = False

    def set_fail_mode(self, enabled: bool):
        self.fail_mode = enabled

    async def provision_access(
        self,
        idempotency_key: str,
        employee_id: int,
        system_code: str,
        role_code: str
    ) -> Dict[str, Any]:
        if self.fail_mode:
            raise ConnectionError("IAM Service Unavailable: Gateway Timeout 504")

        if idempotency_key in self.processed_idempotency_keys:
            return self.processed_idempotency_keys[idempotency_key]

        result = {
            "status": "SUCCESS",
            "provisioning_id": f"IAM-PROV-{idempotency_key[:8]}",
            "employee_id": employee_id,
            "system_code": system_code,
            "role_code": role_code
        }
        self.processed_idempotency_keys[idempotency_key] = result
        return result

hris_client = HrisClient()
iam_client = IamClient()
