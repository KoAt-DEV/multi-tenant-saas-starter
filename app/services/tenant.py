from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import Annotated
from app.models.tenants import Tenant
from app.db import get_db
from app.config import settings


async def get_current_tenant(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)]
) -> Tenant:
    host = request.headers.get("host")  
    if not host:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Host header missing")

    # --- dev fallback ---
    hostname = host.split(":")[0]  
    if settings.PROD_ENV == "prod" and hostname in ["localhost", "127.0.0.1"]:
        subdomain = "public"  
    else:
        parts = hostname.split(".")
        if len(parts) < 3:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid host format")
        subdomain = parts[0]
    # -------------------

    result = await db.execute(
        select(Tenant).where(
            (Tenant.subdomain == subdomain) | (Tenant.custom_domain == hostname)
        )
    )
    tenant = result.scalars().first()

    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    return tenant