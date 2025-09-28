from pydantic import BaseModel
from uuid import UUID

class RolePermissionBase(BaseModel):
    role_id: UUID
    permission_id: UUID

class RolePermissionCreate(RolePermissionBase):
    pass

class RolePermissionRead(RolePermissionBase):
    id: UUID

    class Config:
        orm_mode = True
