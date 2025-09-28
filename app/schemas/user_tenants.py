from pydantic import BaseModel
from uuid import UUID
from typing import Optional
import datetime

class UserTenantBase(BaseModel):
    user_id: UUID
    tenant_id: UUID
    is_active: bool = True
    default_tenant: bool = False

class UserTenantCreate(UserTenantBase):
    pass

class UserTenantRead(UserTenantBase):
    id: UUID
    created_at: datetime.datetime
    updated_at: datetime.datetime

    class Config:
        orm_mode = True
