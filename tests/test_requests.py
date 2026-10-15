import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_get_systems_and_roles(client: AsyncClient):
    response = await client.get("/api/v1/systems")
    assert response.status_code == 200
    systems = response.json()
    assert len(systems) >= 3

    roles_resp = await client.get("/api/v1/roles?system_id=1")
    assert roles_resp.status_code == 200
    roles = roles_resp.json()
    assert len(roles) >= 3

@pytest.mark.asyncio
async def test_create_request_success_and_approval_standard(client: AsyncClient):
    # TC-FR-01: Создание заявки на стандартный доступ (роль 1 = ABS_OPERATOR, is_privileged=False)
    create_payload = {
        "role_id": 1,
        "justification": "Перевод сотрудника в отдел РКО кассового узла"
    }
    resp = await client.post("/api/v1/requests", json=create_payload, headers={"X-User-Id": "1"})
    assert resp.status_code == 201
    data = resp.json()
    req_id = data["id"]
    assert data["status"] == "PENDING_MANAGER"
    assert len(data["audit_logs"]) >= 1

    # TC-FR-05: Согласование руководителем -> сразу APPROVED -> IN_PROVISIONING -> PROVISIONED
    approve_payload = {
        "decision": "APPROVED",
        "comment": "Согласовано руководителем отделения"
    }
    appr_resp = await client.post(f"/api/v1/requests/{req_id}/approve", json=approve_payload, headers={"X-User-Id": "2"})
    assert appr_resp.status_code == 200
    appr_data = appr_resp.json()
    assert appr_data["status"] == "PROVISIONED"
    assert len(appr_data["approvals"]) == 1

@pytest.mark.asyncio
async def test_create_request_dismissed_employee(client: AsyncClient):
    # TC-FR-03: Попытка создания уволенным сотрудником (User 5)
    create_payload = {
        "role_id": 1,
        "justification": "Попытка запроса доступа после увольнения"
    }
    resp = await client.post("/api/v1/requests", json=create_payload, headers={"X-User-Id": "5"})
    assert resp.status_code == 403
    assert "заблокирован или уволен" in resp.json()["detail"]

@pytest.mark.asyncio
async def test_full_privileged_approval_lifecycle(client: AsyncClient):
    # TC-FR-02: Привилегированная роль (роль 2 = ABS_SENIOR_CONTROLLER, is_privileged=True)
    create_payload = {
        "role_id": 2,
        "justification": "Назначение главным контролером отдела РКО"
    }
    resp = await client.post("/api/v1/requests", json=create_payload, headers={"X-User-Id": "1"})
    assert resp.status_code == 201
    req_id = resp.json()["id"]
    assert resp.json()["status"] == "PENDING_MANAGER"

    # Шаг 1: Руководитель одобряет -> PENDING_OWNER
    mgr_resp = await client.post(
        f"/api/v1/requests/{req_id}/approve",
        json={"decision": "APPROVED", "comment": "Согласовано руководителем"},
        headers={"X-User-Id": "2"}
    )
    assert mgr_resp.status_code == 200
    assert mgr_resp.json()["status"] == "PENDING_OWNER"

    # Шаг 2: Владелец системы одобряет -> PENDING_SECURITY
    owner_resp = await client.post(
        f"/api/v1/requests/{req_id}/approve",
        json={"decision": "APPROVED", "comment": "Согласовано владельцем АБС"},
        headers={"X-User-Id": "3"}
    )
    assert owner_resp.status_code == 200
    assert owner_resp.json()["status"] == "PENDING_SECURITY"

    # Шаг 3: Офицер ИБ одобряет -> APPROVED -> PROVISIONED
    sec_resp = await client.post(
        f"/api/v1/requests/{req_id}/approve",
        json={"decision": "APPROVED", "comment": "Проверка прав проведена, согласовано ИБ"},
        headers={"X-User-Id": "4"}
    )
    assert sec_resp.status_code == 200
    assert sec_resp.json()["status"] == "PROVISIONED"

@pytest.mark.asyncio
async def test_reject_request_with_and_without_comment(client: AsyncClient):
    # Создаем заявку
    create_payload = {
        "role_id": 4,
        "justification": "Запрос доступа к витринам ДБО"
    }
    resp = await client.post("/api/v1/requests", json=create_payload, headers={"X-User-Id": "1"})
    req_id = resp.json()["id"]

    # TC-FR-08: Отклонение без комментария -> 400
    bad_resp = await client.post(
        f"/api/v1/requests/{req_id}/approve",
        json={"decision": "REJECTED", "comment": ""},
        headers={"X-User-Id": "2"}
    )
    assert bad_resp.status_code == 400

    # TC-FR-07: Отклонение с комментарием -> REJECTED
    good_resp = await client.post(
        f"/api/v1/requests/{req_id}/approve",
        json={"decision": "REJECTED", "comment": "Недостаточный трудовой стаж"},
        headers={"X-User-Id": "2"}
    )
    assert good_resp.status_code == 200
    assert good_resp.json()["status"] == "REJECTED"

@pytest.mark.asyncio
async def test_cancel_request(client: AsyncClient):
    # TC-FR-09: Отзыв заявки сотрудником
    create_payload = {
        "role_id": 5,
        "justification": "Анализ витрин данных DWH для подготовки отчета"
    }
    resp = await client.post("/api/v1/requests", json=create_payload, headers={"X-User-Id": "1"})
    req_id = resp.json()["id"]

    cancel_resp = await client.post(f"/api/v1/requests/{req_id}/cancel", headers={"X-User-Id": "1"})
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "CANCELLED"
