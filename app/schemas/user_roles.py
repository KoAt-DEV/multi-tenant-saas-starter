from pydantic import BaseModel
from uuid import UUID

class UserRoleBase(BaseModel):
    user_tenant_id: UUID
    role_id: UUID

class UserRoleCreate(UserRoleBase):
    pass

class UserRoleRead(UserRoleBase):
    id: UUID

    class Config:
        orm_mode = True
