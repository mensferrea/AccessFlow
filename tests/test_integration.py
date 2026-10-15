import pytest
from httpx import AsyncClient
from app.services.external_clients import iam_client

@pytest.mark.asyncio
async def test_iam_provisioning_failure_and_retry(client: AsyncClient):
    # TC-INT-03: Проверка сценария сбоя IAM и перевод заявки в статус FAILED
    create_payload = {
        "role_id": 1,
        "justification": "Тестирование обработки отказа IAM"
    }
    resp = await client.post("/api/v1/requests", json=create_payload, headers={"X-User-Id": "1"})
    req_id = resp.json()["id"]

    # Включаем имитацию сбоя IAM
    iam_client.set_fail_mode(True)

    approve_resp = await client.post(
        f"/api/v1/requests/{req_id}/approve",
        json={"decision": "APPROVED", "comment": "Согласовано руководителем"},
        headers={"X-User-Id": "2"}
    )
    assert approve_resp.status_code == 200
    assert approve_resp.json()["status"] == "FAILED"
    assert "Provisioning failed after 3 attempts" in approve_resp.json()["error_message"]

    # TC-INT-04: Ручной перезапуск упавшего провижининга админом
    iam_client.set_fail_mode(False)
    retry_resp = await client.post(
        f"/api/v1/requests/{req_id}/retry",
        headers={"X-User-Id": "4"}
    )
    assert retry_resp.status_code == 200
    assert retry_resp.json()["status"] == "PROVISIONED"
    assert retry_resp.json()["error_message"] is None

@pytest.mark.asyncio
async def test_duplicate_request_conflict(client: AsyncClient):
    # TC-FR-04: Предотвращение дублирования активной заявки на ту же роль
    create_payload = {
        "role_id": 1,
        "justification": "Запрос доступа на согласованную роль повторно"
    }
    # Первая заявка создается успешно
    resp1 = await client.post("/api/v1/requests", json=create_payload, headers={"X-User-Id": "1"})
    assert resp1.status_code == 201

    # Вторая заявка на ту же роль вызывает конфликт 409
    resp2 = await client.post("/api/v1/requests", json=create_payload, headers={"X-User-Id": "1"})
    assert resp2.status_code == 409
    assert "уже активна или находится на рассмотрении" in resp2.json()["detail"]
