from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlalchemy.future import select

from app.config import settings
from app.database import engine, Base, AsyncSessionLocal
from app.models import User, System, AccessRole
from app.api.routes import router

async def seed_data():
    async with AsyncSessionLocal() as session:
        user_res = await session.execute(select(User))
        if user_res.scalars().first():
            return

        # Сначала вставляем пользователей без manager_id, чтобы не нарушать FK
        managers = [
            User(id=2, username="petrov_pp", email="petrov@bank.corp", full_name="Петров Петр Петрович", role="MANAGER", department="Департамент расчетных операций", manager_id=None, is_active=True),
            User(id=3, username="sidorov_ss", email="sidorov@bank.corp", full_name="Сидоров Сидор Сидорович", role="SYSTEM_OWNER", department="Управление информационных систем", manager_id=None, is_active=True),
            User(id=4, username="kuznetsov_ib", email="kuznetsov@bank.corp", full_name="Кузнецов Игорь Борисович", role="SECURITY_OFFICER", department="Служба информационной безопасности", manager_id=None, is_active=True),
        ]
        session.add_all(managers)
        await session.flush()

        subordinates = [
            User(id=1, username="ivanov_ii", email="ivanov@bank.corp", full_name="Иванов Иван Иванович", role="EMPLOYEE", department="Департамент расчетных операций", manager_id=2, is_active=True),
            User(id=5, username="dismissed_emp", email="dismissed@bank.corp", full_name="Бывший Сотрудник", role="EMPLOYEE", department="Архив", manager_id=2, is_active=False),
        ]
        session.add_all(subordinates)
        await session.flush()

        systems = [
            System(id=1, code="CORE_BANKING", name="Автоматизированная банковская система (АБС)", description="Главная учетная система банка", owner_id=3, is_active=True),
            System(id=2, code="DBO_CORP", name="Дистанционное банковское обслуживание ЮЛ", description="Клиент-банк для корпоративных клиентов", owner_id=3, is_active=True),
            System(id=3, code="DWH_ANALYTICS", name="Корпоративное хранилище данных (DWH)", description="Хранилище отчетности и витрин данных", owner_id=3, is_active=True),
        ]
        session.add_all(systems)
        await session.flush()

        roles = [
            AccessRole(id=1, system_id=1, code="ABS_OPERATOR", name="Оператор РКО", description="Проведение платежных поручений", is_privileged=False, is_active=True),
            AccessRole(id=2, system_id=1, code="ABS_SENIOR_CONTROLLER", name="Главный контролер РКО", description="Подтверждение крупных платежей", is_privileged=True, is_active=True),
            AccessRole(id=3, system_id=1, code="ABS_DBA_ADMIN", name="Администратор БД АБС", description="Прямой доступ к таблицам базы данных", is_privileged=True, is_active=True),
            AccessRole(id=4, system_id=2, code="DBO_VIEWER", name="Просмотр профилей клиентов ДБО", description="Только чтение информации", is_privileged=False, is_active=True),
            AccessRole(id=5, system_id=3, code="DWH_ANALYST", name="Аналитик витрин данных", description="Доступ к аналитическим витринам", is_privileged=False, is_active=True),
        ]
        session.add_all(roles)
        await session.commit()

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await seed_data()
    yield
    await engine.dispose()

def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version="1.0.0",
        description="AccessFlow — Корпоративная система управления заявками на доступ к банковским системам",
        lifespan=lifespan
    )
    app.include_router(router, prefix=settings.API_V1_PREFIX)
    return app

app = create_app()
