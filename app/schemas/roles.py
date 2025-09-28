from pydantic import BaseModel
from uuid import UUID
from typing import Optional
import datetime

class RoleBase(BaseModel):
    tenant_id: Optional[UUID] = None  
    name: str
    description: Optional[str] = None
    is_system: bool = False

class RoleCreate(RoleBase):
    pass

class RoleRead(RoleBase):
    id: UUID
    created_at: datetime.datetime
    updated_at: datetime.datetime

    class Config:
        orm_mode = True
