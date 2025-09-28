from pydantic import BaseModel
from uuid import UUID
from typing import Optional, Any
import datetime

class TenantBase(BaseModel):
    name: str
    subdomain: str
    slug: str
    status: Optional[str] = "active"
    custom_domain: Optional[str] = None
    branding: Optional[Any] = None

class TenantCreate(TenantBase):
    pass

class TenantRead(TenantBase):
    id: UUID
    created_at: datetime.datetime
    updated_at: datetime.datetime

    class Config:
        orm_mode = True
