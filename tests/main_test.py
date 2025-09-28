import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.models import UserRole, UserTenant, Role
from seed import seed_test_data
from tests.db_setup import init_test_db
from sqlalchemy.future import select



@pytest_asyncio.fixture
async def client():
    engine, SessionLocal = await init_test_db()

    # dependency override
    from app.db import get_db
    import app.middleware.tenant_middleware as tenant_mw
    tenant_mw.AsyncLocalSession = SessionLocal

    async def _get_db():
        async with SessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = _get_db

    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://client1.local.com") as ac:
        yield ac


    await engine.dispose()



@pytest.mark.asyncio
async def test_successful_admin_token(client):
    _, SessionLocal = await init_test_db()
    data = await seed_test_data(SessionLocal)

    tenant = data["tenants"]["client1"]
    user = data["users"]["admin@client1.com"]

    response = await client.post(
        "/api/auth/token",
        data={"username": user.email, "password": "admin123"},
        headers={"Host": "client1.local.com"},
    )

    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert body["tenant"] == tenant.subdomain


@pytest.mark.asyncio
async def test_successful_admin_login(client):
    _, SessionLocal = await init_test_db()
    data = await seed_test_data(SessionLocal)

    tenant = data["tenants"]["client1"]
    user = data["users"]["admin@client1.com"]

    response = await client.post(
        "/api/auth/login",
        params={"email": user.email, "password": "admin123"},
        headers={"Host": "client1.local.com"},
    )

    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert body["tenant"] == tenant.subdomain

@pytest.mark.asyncio
async def test_user_me(client):
    _, SessionLocal = await init_test_db()
    data = await seed_test_data(SessionLocal)

    tenant = data["tenants"]["client1"]
    user = data["users"]["admin@client1.com"]
    
    async with SessionLocal() as db:
        stmt = await db.execute(
            select(Role).join(UserRole, UserRole.role_id == Role.id)
            .join(UserTenant, UserTenant.id == UserRole.usertenant_id)
            .where(UserTenant.user_id == user.id, UserTenant.tenant_id == tenant.id)
        )
    role = stmt.scalars().first()


    # 1) Login admin user
    login_response = await client.post(
        "/api/auth/login",
        params={"email": user.email, "password": "admin123"},
        headers={"Host": "client1.local.com"},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]


    # 2) Access admin-only route with token
    response = await client.get(
        "/api/auth/me",
        headers={
            "Host": "client1.local.com",
            "Authorization": f"Bearer {token}"
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["user_name"] == user.full_name
    assert body["user_email"] == user.email
    assert body["tenant_name"] == tenant.name
    assert role.name in body["roles"]
    



@pytest.mark.asyncio
async def test_wrong_tenant_login_try(client):
    _, SessionLocal = await init_test_db()
    data = await seed_test_data(SessionLocal)

    tenant = data["tenants"]["client1"]
    user = data["users"]["admin@client1.com"]

    response = await client.post(
        "/api/auth/login",
        params={"email": user.email, "password": "admin123"},
        headers={"Host": "client2.local.com"},
    )

    assert response.status_code == 403
    body = response.json()
    assert body["detail"] == "User does not belong to this tenant" 
    
    
async def test_wrong_password(client):  
    _, SessionLocal = await init_test_db() 

    data = await seed_test_data(SessionLocal) 
    tenant = data["tenants"]["client1"] 
    user = data["users"]["admin@client1.com"] 
    
    response = await client.post( 
        "/api/auth/login", 
        params={"email": user.email, "password": "wrongpassword"}, 
        headers={"Host": "client1.local.com"}, ) 
    
    assert response.status_code == 401 
    body = response.json() 
    assert body["detail"] == "Invalid credentials"

@pytest.mark.asyncio
async def test_logout_revokes_refresh_token(client):
    _, SessionLocal = await init_test_db()
    data = await seed_test_data(SessionLocal)
    user = data["users"]["admin@client1.com"]

    # 1) Login
    login_response = await client.post(
        "/api/auth/login",
        params={"email": user.email, "password": "admin123"},
        headers={"Host": "client1.local.com"},
    )
    assert login_response.status_code == 200
    tokens = login_response.json()
    refresh_token = tokens["refresh_token"]

    # 2) Logout
    response = await client.post(
        "/api/auth/logout",
        json={"refresh_token": refresh_token},
        headers={"Host": "client1.local.com"},
    )
    assert response.status_code == 204

    # 3) Retry with old/revoked token → 401
    refresh_response = await client.post(
        "/api/auth/refresh",
        json={"refresh_token": refresh_token},
        headers={"Host": "client1.local.com"},
    )
    assert refresh_response.status_code == 401
    assert refresh_response.json()["detail"] == "Token revoked or expired"


@pytest.mark.asyncio
async def test_admin_access(client):
    _, SessionLocal = await init_test_db()
    data = await seed_test_data(SessionLocal)

    tenant = data["tenants"]["client1"]
    user = data["users"]["admin@client1.com"]

    
    login_response = await client.post(
        "/api/auth/login",
        params={"email": user.email, "password": "admin123"},
        headers={"Host": "client1.local.com"},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]

    
    response = await client.post(
        "/api/permission-check/admin-only",
        headers={
            "Host": "client1.local.com",
            "Authorization": f"Bearer {token}"
        },
    )

    assert response.status_code == 200
    body = response.json()
    expected_msg = f"Hello Admin of tenant {tenant.name}!"
    assert body["msg"] == expected_msg

@pytest.mark.asyncio
async def test_no_admin_access_for_operator(client):
    _, SessionLocal = await init_test_db()
    data = await seed_test_data(SessionLocal)

    tenant = data["tenants"]["client1"]
    user = data["users"]["operator@client1.com"]

    # 1) Login admin user
    login_response = await client.post(
        "/api/auth/login",
        params={"email": user.email, "password": "operator123"},
        headers={"Host": "client1.local.com"},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]

    # 2) Try to access admin-only route with token
    response = await client.post(
        "/api/permission-check/admin-only",
        headers={
            "Host": "client1.local.com",
            "Authorization": f"Bearer {token}"
        },
    )

    assert response.status_code == 403
    body = response.json()
    assert body["detail"] == "Not enough permissions"


@pytest.mark.asyncio
async def test_forgot_password_existing_user(client):
    _, SessionLocal = await init_test_db()
    data = await seed_test_data(SessionLocal)
    user = data["users"]["admin@client1.com"]

    response = await client.post(
        "/api/auth/forgot-password",
        json={"email": user.email},
        headers={"Host": "client1.local.com"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["message"] == "Reset link sent"
    assert "token" in body
    assert isinstance(body["token"], str)


@pytest.mark.asyncio
async def test_forgot_password_nonexistent_user(client):
    _, SessionLocal = await init_test_db()
    await seed_test_data(SessionLocal)

    response = await client.post(
        "/api/auth/forgot-password",
        json={"email": "idontexist@client1.com"},
        headers={"Host": "client1.local.com"},
    )

    assert response.status_code == 404
    body = response.json()
    assert body["detail"] == "User not found"


@pytest.mark.asyncio
async def test_tenant_data(client):
    _, SessionLocal = await init_test_db()
    data = await seed_test_data(SessionLocal)

    tenant = data["tenants"]["client1"]
    user = data["users"]["operator@client1.com"]

    # 1) Login admin user
    login_response = await client.post(
        "/api/auth/login",
        params={"email": user.email, "password": "operator123"},
        headers={"Host": "client1.local.com"},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]

    # 2) Try to access tenant-data route with token
    response = await client.get(
        "/api/tenant/tenant-data",
        headers={
            "Host": "client1.local.com",
            "Authorization": f"Bearer {token}"
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["tenant_name"] == f"{tenant.name}"
    assert body["subdomain"] == f"{tenant.subdomain}"