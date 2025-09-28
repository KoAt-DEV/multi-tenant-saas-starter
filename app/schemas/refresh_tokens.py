from pydantic import BaseModel
from uuid import UUID
from typing import Optional
import datetime

class RefreshTokenBase(BaseModel):
    user_tenant_id: UUID
    jti: str
    revoked: bool = False
    expires_at: datetime.datetime
    user_agent: Optional[str] = None
    ip: Optional[str] = None

class RefreshTokenCreate(RefreshTokenBase):
    pass

class RefreshTokenRead(RefreshTokenBase):
    id: UUID
    created_at: datetime.datetime

    class Config:
        orm_mode = True
