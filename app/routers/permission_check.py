from fastapi import APIRouter, Depends
from app.services.rbac import role_checker

router = APIRouter(prefix="/api/permission-check", tags=["permission-check"])

@router.post("/admin-only")
async def admin_action(user_tenant = Depends(role_checker("admin_tenant"))):
    return {"msg": f"Hello Admin of tenant {user_tenant['tenant']}!"}
