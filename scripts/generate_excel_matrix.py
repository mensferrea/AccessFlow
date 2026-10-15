import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

wb = openpyxl.Workbook()

# Sheet 1: RTM
ws_rtm = wb.active
ws_rtm.title = "Матрица трассировки (RTM)"

headers_rtm = [
    "Бизнес-требование (BR)",
    "Функциональное требование (FR)",
    "Архитектурный компонент / Endpoint",
    "Идентификаторы тест-кейсов",
    "Статус покрытия"
]

data_rtm = [
    ["BR-01: Единая точка подачи заявок", "FR-01: Создание заявки\nFR-03: Просмотр реестра", "POST /api/v1/requests\nGET /api/v1/requests", "TC-FR-01, TC-FR-02", "Покрыто"],
    ["BR-02: Проверка кадрового статуса", "FR-01: Валидация в HRIS", "HrisClient.get_employee", "TC-FR-03", "Покрыто"],
    ["BR-03: Разделение маршрутов согласования", "FR-02: Определение критичности", "access_roles.is_privileged", "TC-FR-04, TC-FR-05", "Покрыто"],
    ["BR-04: Многоэтапное согласование", "FR-05: Резолюция согласующего\nFR-06: Продвижение по цепочке", "POST /api/v1/requests/{id}/approve", "TC-FR-06, TC-FR-07, TC-FR-08", "Покрыто"],
    ["BR-05: Автоматизированный провижининг", "FR-07: Инициирование в IAM\nFR-08: Обработка ответа", "IamClient.provision_access", "TC-INT-01, TC-INT-02", "Покрыто"],
    ["BR-06: Возможность отзыва заявки", "FR-04: Отмена заявки сотрудником", "POST /api/v1/requests/{id}/cancel", "TC-FR-09, TC-FR-10", "Покрыто"],
    ["BR-07: Неизменяемый аудит", "FR-10: Протоколирование операций", "AuditService.log_action", "TC-FR-11", "Покрыто"],
    ["BR-08: Отказоустойчивость интеграций", "FR-08: Механизм Retry и fallback", "RequestService.retry_provisioning", "TC-INT-03", "Покрыто"],
    ["BR-09: Legacy интеграция XML/XSD", "NFR-11: Валидация XML по XSD", "XmlValidatorService.validate_xml", "TC-INT-04, TC-INT-05", "Покрыто"],
]

# Sheet 2: Test Cases
ws_tc = wb.create_sheet(title="Тест-кейсы")

headers_tc = [
    "ID Тест-кейса",
    "Категория",
    "Название сценария",
    "Предусловия",
    "Шаги воспроизведения",
    "Ожидаемый результат",
    "Тип теста"
]

data_tc = [
    ["TC-FR-01", "Функциональный", "Создание заявки на стандартный доступ", "Сотрудник активен в HRIS", "1. Выбрать роль с is_privileged=false\n2. Заполнить обоснование\n3. Отправить POST /api/v1/requests", "HTTP 201 Created, статус PENDING_MANAGER", "Позитивный"],
    ["TC-FR-02", "Функциональный", "Создание заявки на привилегированный доступ", "Сотрудник активен в HRIS", "1. Выбрать роль с is_privileged=true\n2. Отправить POST /api/v1/requests", "HTTP 201 Created, статус PENDING_MANAGER (3 этапа)", "Позитивный"],
    ["TC-FR-03", "Функциональный", "Создание заявки уволенным сотрудником", "Статус в HRIS = DISMISSED", "1. Отправить POST /api/v1/requests", "HTTP 403 Forbidden с сообщением об увольнении", "Негативный"],
    ["TC-FR-04", "Функциональный", "Предотвращение дублирования заявки", "Уже есть активная заявка на роль", "1. Отправить POST /api/v1/requests повторно", "HTTP 409 Conflict", "Негативный"],
    ["TC-FR-05", "Функциональный", "Согласование стандартного доступа руководителем", "Заявка в PENDING_MANAGER, стандартная", "1. POST /api/v1/requests/{id}/approve (decision=APPROVED)", "Статус переходит в APPROVED -> IN_PROVISIONING -> PROVISIONED", "Позитивный"],
    ["TC-FR-06", "Функциональный", "Согласование руководителем привилегированного доступа", "Заявка в PENDING_MANAGER, привилегированная", "1. POST /api/v1/requests/{id}/approve (decision=APPROVED)", "Статус переходит в PENDING_OWNER", "Позитивный"],
    ["TC-FR-07", "Функциональный", "Отклонение руководителем с указанием причины", "Заявка в PENDING_MANAGER", "1. POST /api/v1/requests/{id}/approve (decision=REJECTED, comment='...')", "Статус переходит в REJECTED, коммент сохранен", "Позитивный"],
    ["TC-FR-08", "Функциональный", "Отклонение без обязательного комментария", "Заявка в PENDING_MANAGER", "1. POST /api/v1/requests/{id}/approve (decision=REJECTED, comment=null)", "HTTP 400 Bad Request", "Негативный"],
    ["TC-FR-09", "Функциональный", "Отзыв заявки инициатором", "Заявка в PENDING_MANAGER", "1. POST /api/v1/requests/{id}/cancel", "Статус переходит в CANCELLED", "Позитивный"],
    ["TC-FR-10", "Функциональный", "Запрет отзыва согласованной заявки", "Заявка в PROVISIONED", "1. POST /api/v1/requests/{id}/cancel", "HTTP 400 Bad Request", "Негативный"],
    ["TC-INT-01", "Интеграционный", "Успешный провижининг через IAM", "Заявка согласована (APPROVED)", "1. Вызов IAM API провижининга", "HTTP 201 Created от IAM, заявка переходит в PROVISIONED", "Позитивный"],
    ["TC-INT-02", "Интеграционный", "Идемпотентность по заголовку Idempotency-Key", "Запрос в IAM уже выполнен", "1. Повторный вызов IAM с тем же ключом", "Возврат того же статуса без дублирования прав", "Позитивный"],
    ["TC-INT-03", "Интеграционный", "Обработка ошибки IAM (503) и переход в FAILED", "IAM недоступен", "1. Вызов провижининга в IAM", "3 попытки Retry, после чего статус заявки = FAILED", "Негативный"],
    ["TC-INT-04", "Интеграционный", "Валидация XML-сообщения по XSD-схеме", "Корректный XML по схеме", "1. Вызов XmlValidatorService.validate", "Валидация успешна (is_valid = True)", "Позитивный"],
    ["TC-INT-05", "Интеграционный", "Обнаружение нарушения XSD схемы", "XML с отсутствующим тегом SystemCode", "1. Вызов XmlValidatorService.validate", "Валидация неуспешна (is_valid = False), список ошибок", "Негативный"]
]

header_fill = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid")
header_font = Font(name="Arial", size=11, bold=True, color="FFFFFF")
cell_font = Font(name="Arial", size=10)
thin_border = Border(
    left=Side(style='thin', color='D9D9D9'),
    right=Side(style='thin', color='D9D9D9'),
    top=Side(style='thin', color='D9D9D9'),
    bottom=Side(style='thin', color='D9D9D9')
)

def format_sheet(ws, headers, data):
    ws.append(headers)
    for col_num in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_num)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    for row_idx, row_data in enumerate(data, start=2):
        ws.append(row_data)
        for col_num in range(1, len(row_data) + 1):
            cell = ws.cell(row=row_idx, column=col_num)
            cell.font = cell_font
            cell.border = thin_border
            cell.alignment = Alignment(vertical="center", wrap_text=True)

    for col in ws.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            val = str(cell.value or '')
            lines = val.split('\n')
            for line in lines:
                if len(line) > max_len:
                    max_len = len(line)
        ws.column_dimensions[col_letter].width = min(max(max_len + 4, 15), 45)

format_sheet(ws_rtm, headers_rtm, data_rtm)
format_sheet(ws_tc, headers_tc, data_tc)

wb.save("C:/Users/tamer/PycharmProjects/AccessFlow/docs/testing/Traceability_Matrix_and_Test_Cases.xlsx")
print("Excel matrix generated successfully")
