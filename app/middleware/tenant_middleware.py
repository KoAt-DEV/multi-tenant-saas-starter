import logging
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request, HTTPException
from sqlalchemy.future import select
from app.db import AsyncLocalSession
from app.models.tenants import Tenant
from app.config import settings

logger = logging.getLogger(__name__)

class TenantMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        host = request.headers.get("host")
        if not host:
            logger.warning("Missing Host header")
            raise HTTPException(status_code=400, detail="Missing Host header")

        hostname = host.split(":")[0]  # strip port
        subdomain = None

        try:
            if settings.PROD_ENV == "prod" and hostname in ["localhost", "127.0.0.1"]:
                subdomain = settings.DEFAULT_DEV_TENANT or "public"
                logger.debug(f"DEV fallback tenant={subdomain}, hostname={hostname}")
            else:
                parts = hostname.split(".")
                if len(parts) < 3:
                    logger.warning(f"Invalid host format: {hostname}")
                    raise HTTPException(status_code=400, detail="Invalid host format")
                subdomain = parts[0]

            async with AsyncLocalSession() as db:
                result = await db.execute(
                    select(Tenant).where(
                        (Tenant.subdomain == subdomain) | (Tenant.custom_domain == hostname)
                    )
                )
                tenant = result.scalars().first()

            if not tenant:
                logger.error(f"No tenant found for subdomain={subdomain}, host={hostname}")
                raise HTTPException(status_code=404, detail="Tenant not found")

            request.state.tenant = tenant
            logger.info(f"Tenant resolved: {tenant.name} ({tenant.subdomain})")

        except Exception as e:
            request.state.tenant = None
            logger.exception("Tenant resolution failed")
            raise

        return await call_next(request)
