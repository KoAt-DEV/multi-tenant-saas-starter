from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import Annotated
from datetime import timedelta, datetime, timezone
import uuid
from app.schemas.auth import RefreshTokenSchema, TokenResponseSchema, ForgotPasswordSchema, ResetPasswordSchema
from app.services.auth import create_access_token, create_refresh_token, decode_access_token, generate_reset_token, verify_reset_token, reset_user_password, get_current_user
from app.services.tenant import get_current_tenant
from app.crud.user import authenticate_user, get_user_roles
from app.models.refresh_tokens import RefreshToken
from app.models.user_tenants import UserTenant
from app.models.roles import Role
from app.models.permissions import Permission
from app.models.role_permissions import RolePermission
from app.models.user_roles import UserRole
from app.models.users import User
from app.schemas.users import MeResponse
from app.db import get_db
from app.config import settings


router = APIRouter(prefix="/api/auth", tags=["auth"])



@router.post("/token")
async def login_for_access_token(
    request: Request,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    # 1. tenant a Host headerből
    tenant = request.state.tenant
    if not tenant:
        raise HTTPException(status_code=400, detail="Tenant not resolved")

    # 2. authenticate
    user = await authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

    # 3. ellenőrzés hogy user ehhez a tenant-hoz tartozik-e
    result = await db.execute(
        select(UserTenant).where(
            (UserTenant.user_id == user.id) &
            (UserTenant.tenant_id == tenant.id)
        )
    )
    user_tenant = result.scalars().first()
    if not user_tenant:
        raise HTTPException(status_code=403, detail="User not in this tenant")

    # 4. role-ok lekérése
    stmt = await db.execute(
        select(Role.name)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.usertenant_id == user_tenant.id)
    )
    roles = [r[0] for r in stmt.all()]

    # 5. token generálás tenant + role infóval
    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "tid": str(tenant.id),
            "roles": roles
        }
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "roles": roles,
        "tenant": tenant.subdomain
    }



@router.post("/login")
async def login(
    request: Request,
    email: str,
    password: str,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    tenant = request.state.tenant
    if not tenant:
        raise HTTPException(status_code=400, detail="Tenant not resolved")

    # 1. authenticate
    user = await authenticate_user(db, email, password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    
    # 2. user-tenant connection check
    result = await db.execute(
        select(UserTenant).where(
            (UserTenant.user_id == user.id) &
            (UserTenant.tenant_id == tenant.id)
        )
    )
    user_tenant = result.scalars().first()
    if not user_tenant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not belong to this tenant"
        )

    # 3. role
    stmt = await db.execute(
        select(Role.name)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.usertenant_id == user_tenant.id)
    )
    roles = [r[0] for r in stmt.all()]

    # 4. access token generating
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "tid": str(tenant.id),
            "roles": roles
        },
        expire_delta=access_token_expires,
    )

    # 5. refresh token
    refresh_token = create_refresh_token(
        data={"sub": str(user.id), "tid": str(tenant.id)}
    )
    refresh_jti = decode_access_token(refresh_token)["jti"]

    now = datetime.now(timezone.utc)
    refresh_exp = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    db_token = RefreshToken(
        id=uuid.uuid4(),
        user_tenant_id=user_tenant.id,  
        jti=refresh_jti,
        revoked=False,
        expires_at=refresh_exp, 
        created_at=now,
        user_agent=request.headers.get("User-Agent"),
        ip=request.client.host,
    )
    db.add(db_token)
    await db.commit()
    await db.refresh(db_token)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "roles": roles,
        "tenant": tenant.subdomain
    }

@router.get("/me", response_model=MeResponse)
async def read_users_me(
    db: Annotated[AsyncSession, Depends(get_db)],
    tenant=Depends(get_current_tenant),
    user=Depends(get_current_user)  
):

    stmt = await db.execute(
        select(UserTenant).where(
            (UserTenant.user_id == user.id) &
            (UserTenant.tenant_id == tenant.id)
        )
    )
    user_tenant = stmt.scalars().first()
    if not user_tenant:
        raise HTTPException(status_code=404, detail="User not found in tenant")
    
    stmt = await db.execute(
        select(Role.name)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.usertenant_id == user_tenant.id)
    )

    user_role = stmt.scalars().all()


    return MeResponse(
        user_name=user.full_name,
        user_email=user.email,
        tenant_name=tenant.name,
        roles=user_role
    )


@router.post("/refresh", response_model=TokenResponseSchema)
async def refresh_token(
    payload: RefreshTokenSchema,
    db: Annotated[AsyncSession, Depends(get_db)],
    tenant=Depends(get_current_tenant),
    request: Request = None
):
    token_str = payload.refresh_token
    decoded = decode_access_token(token_str)
    if not decoded or "sub" not in decoded or "jti" not in decoded:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    jti = decoded["jti"]
    stmt = await db.execute(select(RefreshToken).where(
        RefreshToken.jti == jti,
        RefreshToken.revoked == False
    ))
    db_token = stmt.scalars().first()

    if not db_token or db_token.expires_at < datetime.utcnow():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token revoked or expired")

    # generate new tokens
    user_tenant_id = db_token.user_tenant_id
    access_token = create_access_token({"sub": str(decoded["sub"]), "tid": str(tenant.id)})
    
    refresh_token = create_refresh_token(
    {"sub": str(decoded["sub"]), "tid": str(tenant.id)}
)
    refresh_jti = decode_access_token(refresh_token)["jti"]


    # revoke old token
    db_token.revoked = True

    # save new refresh token
    now = datetime.now(timezone.utc)
    new_db_token = RefreshToken(
    id=uuid.uuid4(),
    user_tenant_id=user_tenant_id,
    jti=refresh_jti,
    revoked=False,
    expires_at=now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    created_at=now,
    user_agent=request.headers.get("User-Agent") if request else None,
    ip=request.client.host if request else None,
)

    db.add(new_db_token)
    await db.commit()
    await db.refresh(new_db_token)

    return TokenResponseSchema(access_token=access_token, refresh_token=refresh_token)


#
@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    payload: RefreshTokenSchema,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    token_str = payload.refresh_token
    decoded = decode_access_token(token_str)
    if not decoded or "jti" not in decoded:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    stmt = await db.execute(select(RefreshToken).where(RefreshToken.jti == decoded["jti"]))
    db_token = stmt.scalars().first()
    if db_token:
        db_token.revoked = True
        await db.commit()

    return

@router.post("/forgot-password")
async def forgot_password(payload: ForgotPasswordSchema, db: AsyncSession = Depends(get_db)):
    
    stmt = await db.execute(select(User).where(User.email == payload.email))
    user = stmt.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    token = await generate_reset_token(db, user)
    # TODO: Send in email
    return {"message": "Reset link sent", "token": token}  # give the token in response for testing


@router.post("/reset-password")
async def reset_password(payload: ResetPasswordSchema, db: AsyncSession = Depends(get_db)):
    user, reset_record = await verify_reset_token(db, payload.token)
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    await reset_user_password(db, user, reset_record, payload.new_password)
    return {"message": "Password successfully reset"}
