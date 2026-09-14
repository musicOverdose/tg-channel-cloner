import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from backend.app.main import app, seed_admin_user
from backend.app.database import init_db
from backend.app.config import settings


@pytest_asyncio.fixture(scope="module", autouse=True)
async def setup_test_db():
    await init_db()
    await seed_admin_user()


@pytest.mark.asyncio
async def test_health_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "timestamp" in data


@pytest.mark.asyncio
async def test_auth_and_protected_endpoints():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Login with admin credentials
        login_resp = await client.post(
            "/api/auth/login",
            json={"username": settings.ADMIN_USERNAME, "password": settings.ADMIN_PASSWORD},
        )
        assert login_resp.status_code == 200
        token_data = login_resp.json()
        token = token_data["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Check /api/auth/me
        me_resp = await client.get("/api/auth/me", headers=headers)
        assert me_resp.status_code == 200
        assert me_resp.json()["username"] == settings.ADMIN_USERNAME

        # 3. Check system info
        sys_resp = await client.get("/api/system/info", headers=headers)
        assert sys_resp.status_code == 200
        assert sys_resp.json()["status"] == "healthy"

        # 4. Check dashboard stats
        dash_resp = await client.get("/api/dashboard/stats", headers=headers)
        assert dash_resp.status_code == 200
        assert "total_jobs" in dash_resp.json()
        assert "upcoming_runs" in dash_resp.json()

        # 5. Check bots list
        bots_resp = await client.get("/api/bots", headers=headers)
        assert bots_resp.status_code == 200
        assert isinstance(bots_resp.json(), list)

        # 6. Check jobs list
        jobs_resp = await client.get("/api/jobs", headers=headers)
        assert jobs_resp.status_code == 200
        assert isinstance(jobs_resp.json(), list)


@pytest.mark.asyncio
async def test_frontend_root_serving():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "Telegram Channel Cloner" in response.text

