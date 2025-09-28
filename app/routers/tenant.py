from fastapi import APIRouter, Request
from app.services.rbac import requires_permission  

router = APIRouter(prefix="/api/tenant", tags=["tenant"])

@router.get("/tenant-data")
async def get_tenant_data(request: Request, _=requires_permission("read")):
    tenant = request.state.tenant
    return {"tenant_name": tenant.name, "subdomain": tenant.subdomain}
