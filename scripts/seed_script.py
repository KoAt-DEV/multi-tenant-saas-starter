import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import asyncio
import uuid
import datetime
from datetime import timedelta

from sqlalchemy import select
from app.db import AsyncLocalSession
from app.models.tenants import Tenant
from app.models.users import User
from app.models.user_tenants import UserTenant
from app.models.roles import Role
from app.models.permissions import Permission
from app.models.role_permissions import RolePermission
from app.models.user_roles import UserRole
from app.models.refresh_tokens import RefreshToken
from app.models.audit_logs import AuditLog
from app.models.password_reset import PasswordReset
from app.crud.user import hash_password

async def seed_full_test_data():
    async with AsyncLocalSession() as db:
        # ----------------------
        # 1) Tenants
        # ----------------------
        tenants_data = [
            {"subdomain": "public", "name": "Public Tenant", "code": "PUBLIC"},
            {"subdomain": "client1", "name": "Client 1", "code": "CLIENT1"},
            {"subdomain": "client2", "name": "Client 2", "code": "CLIENT2"},
        ]
        tenants = {}
        for td in tenants_data:
            result = await db.execute(select(Tenant).where(Tenant.subdomain == td["subdomain"]))
            tenant = result.scalars().first()
            if not tenant:
                tenant = Tenant(
                    id=uuid.uuid4(),
                    name=td["name"],
                    subdomain=td["subdomain"],
                    code=td["code"],
                    status=True,
                    created_at=datetime.datetime.utcnow(),
                    updated_at=datetime.datetime.utcnow()
                )
                db.add(tenant)
                await db.commit()
                await db.refresh(tenant)
            tenants[td["subdomain"]] = tenant

        # ----------------------
        # 2) Users
        # ----------------------
        users_data = [
            # Public Tenant
            {"email": "admin@public.com", "full_name": "Public Admin", "password": "admin123", "tenant": "public", "role": "admin_tenant"},
            {"email": "manager@public.com", "full_name": "Public Manager", "password": "manager123", "tenant": "public", "role": "manager"},
            {"email": "operator@public.com", "full_name": "Public Operator", "password": "operator123", "tenant": "public", "role": "operator"},
            # Client1
            {"email": "admin@client1.com", "full_name": "Client1 Admin", "password": "admin123", "tenant": "client1", "role": "admin_tenant"},
            {"email": "manager@client1.com", "full_name": "Client1 Manager", "password": "manager123", "tenant": "client1", "role": "manager"},
            {"email": "operator@client1.com", "full_name": "Client1 Operator", "password": "operator123", "tenant": "client1", "role": "operator"},
            # Client2
            {"email": "admin@client2.com", "full_name": "Client2 Admin", "password": "admin123", "tenant": "client2", "role": "admin_tenant"},
            {"email": "manager@client2.com", "full_name": "Client2 Manager", "password": "manager123", "tenant": "client2", "role": "manager"},
            {"email": "operator@client2.com", "full_name": "Client2 Operator", "password": "operator123", "tenant": "client2", "role": "operator"},
        ]
        users = {}
        for ud in users_data:
            result = await db.execute(select(User).where(User.email == ud["email"]))
            user = result.scalars().first()
            if not user:
                user = User(
                    id=uuid.uuid4(),
                    email=ud["email"],
                    password_hash=hash_password(ud["password"]),
                    full_name=ud["full_name"],
                    is_active=True,
                    is_superuser="admin" in ud["email"],
                    created_at=datetime.datetime.utcnow(),
                    updated_at=datetime.datetime.utcnow()
                )
                db.add(user)
                await db.commit()
                await db.refresh(user)
            users[ud["email"]] = user

        # ----------------------
        # 3) UserTenants
        # ----------------------
        user_tenants = {}
        for ud in users_data:
            user = users[ud["email"]]
            tenant = tenants[ud["tenant"]]
            result = await db.execute(
                select(UserTenant).where(
                    (UserTenant.user_id == user.id) &
                    (UserTenant.tenant_id == tenant.id)
                )
            )
            ut = result.scalars().first()
            if not ut:
                ut = UserTenant(
                    id=uuid.uuid4(),
                    user_id=user.id,
                    tenant_id=tenant.id,
                    is_active=True,
                    default_tenant=(ud["role"]=="admin_tenant"),
                    created_at=datetime.datetime.utcnow(),
                    updated_at=datetime.datetime.utcnow()
                )
                db.add(ut)
                await db.commit()
                await db.refresh(ut)
            user_tenants[(ud["email"], ud["tenant"])] = ut

        # ----------------------
        # 4) Roles
        # ----------------------
        roles_data = [
            {"tenant": "public", "name": "admin_tenant"},
            {"tenant": "public", "name": "manager"},
            {"tenant": "public", "name": "operator"},
            {"tenant": "client1", "name": "admin_tenant"},
            {"tenant": "client1", "name": "manager"},
            {"tenant": "client1", "name": "operator"},
            {"tenant": "client2", "name": "admin_tenant"},
            {"tenant": "client2", "name": "manager"},
            {"tenant": "client2", "name": "operator"},
        ]
        roles = {}
        for rd in roles_data:
            tenant_obj = tenants[rd["tenant"]]
            result = await db.execute(select(Role).where(
                (Role.name == rd["name"]) & (Role.tenant_id == tenant_obj.id)
            ))
            role = result.scalars().first()
            if not role:
                role = Role(
                    id=uuid.uuid4(),
                    tenant_id=tenant_obj.id,
                    name=rd["name"],
                    description=f"{rd['name']} role",
                    is_system=True
                )
                db.add(role)
                await db.commit()
                await db.refresh(role)
            roles[(rd["tenant"], rd["name"])] = role

        # ----------------------
        # 5) Permissions
        # ----------------------
        permissions_data = [
            {"name": "read", "description": "Read access"},
            {"name": "write", "description": "Write access"},
        ]
        permissions = {}
        for pd in permissions_data:
            result = await db.execute(select(Permission).where(Permission.name == pd["name"]))
            perm = result.scalars().first()
            if not perm:
                perm = Permission(
                    id=uuid.uuid4(),
                    name=pd["name"],
                    description=pd["description"]
                )
                db.add(perm)
                await db.commit()
                await db.refresh(perm)
            permissions[pd["name"]] = perm

        # ----------------------
        # 6) RolePermissions
        # ----------------------
        for (tenant_name, role_name), role in roles.items():
            for perm_name, perm in permissions.items():
                result = await db.execute(select(RolePermission).where(
                    (RolePermission.role_id == role.id) & (RolePermission.permission_id == perm.id)
                ))
                rp = result.scalars().first()
                if not rp:
                    rp = RolePermission(
                        id=uuid.uuid4(),
                        role_id=role.id,
                        permission_id=perm.id
                    )
                    db.add(rp)
                    await db.commit()

        # ----------------------
        # 7) UserRoles
        # ----------------------
        for ud in users_data:
            ut = user_tenants[(ud["email"], ud["tenant"])]
            role = roles[(ud["tenant"], ud["role"])]
            result = await db.execute(select(UserRole).where(
                (UserRole.usertenant_id == ut.id) & (UserRole.role_id == role.id)
            ))
            ur = result.scalars().first()
            if not ur:
                ur = UserRole(
                    id=uuid.uuid4(),
                    usertenant_id=ut.id,
                    role_id=role.id
                )
                db.add(ur)
                await db.commit()

        # ----------------------
        # 8) Refresh tokens (demo)
        # ----------------------
        for (email, tenant_sub), ut in user_tenants.items():
            result = await db.execute(select(RefreshToken).where(RefreshToken.user_tenant_id == ut.id))
            token_exists = result.scalars().first()
            if not token_exists:
                db_token = RefreshToken(
                    id=uuid.uuid4(),
                    user_tenant_id=ut.id,
                    jti=str(uuid.uuid4()),
                    revoked=False,
                    expires_at=datetime.datetime.utcnow() + timedelta(days=14),
                    user_agent="Seed Script",
                    ip="127.0.0.1",
                    created_at=datetime.datetime.utcnow()
                )
                db.add(db_token)
                await db.commit()

        print("Seed completed: 3 tenants x 3 users with roles.")

if __name__ == "__main__":
    asyncio.run(seed_full_test_data())