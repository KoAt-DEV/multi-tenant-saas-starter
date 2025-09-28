from fastapi import Depends, HTTPException, status, Request
from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_
from sqlalchemy.future import select
from app.db import get_db
from app.models.user_tenants import UserTenant
from app.models.tenants import Tenant
from app.models.user_roles import UserRole
from app.models.permissions import Permission
from app.models.role_permissions import RolePermission
from app.services.auth import get_current_user_object, get_current_user
from app.crud.user import get_user_roles
from app.services.tenant import get_current_tenant
from uuid import UUID


async def user_has_permission(db: AsyncSession, user_tenant_id: UUID, permission_name: str) -> bool:
    stmt = await db.execute(
        select(Permission)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(UserRole, UserRole.role_id == RolePermission.role_id)
        .where(UserRole.usertenant_id == user_tenant_id)
        .where(Permission.name == permission_name)
    )
    permission = stmt.scalars().first()
    return permission is not None


def requires_permission(permission_name: str):
    async def permission_checker(
        db: Annotated[AsyncSession, Depends(get_db)],
        tenant: Annotated[Tenant, Depends(get_current_tenant)],
        user=Depends(get_current_user)  
    ):
        
        stmt = await db.execute(
            select(UserTenant)
            .where(and_(UserTenant.user_id == user.id, UserTenant.tenant_id == tenant.id))
        )
        user_tenant = stmt.scalars().first()
        if not user_tenant or not await user_has_permission(db, user_tenant.id, permission_name):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
        return True

    return permission_checker



def role_checker(*roles: str):
    async def role_checker(
        request: Request,
        db: AsyncSession = Depends(get_db),
        current_user = Depends(get_current_user_object)
    ):
        tenant = request.state.tenant
        if not tenant:
            raise HTTPException(status_code=400, detail="Tenant not resolved")

        user_roles = await get_user_roles(db, current_user["user_id"], tenant.id)

        if not any(role in user_roles for role in roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
        return {"user_id": current_user["user_id"], "roles": user_roles, "tenant": tenant.name}
    return role_checker






