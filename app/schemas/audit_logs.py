from pydantic import BaseModel
from typing import Optional, Any
from uuid import UUID
import datetime


class AuditLogBase(BaseModel):
    action: str
    entity: Optional[str] = None
    entity_id: Optional[UUID] = None
    metadata: Optional[Any] = None  
    tenant_id: UUID
    user_id: Optional[UUID] = None


class AuditLogCreate(AuditLogBase):
    pass 


class AuditLogRead(AuditLogBase):
    id: UUID
    created_at: datetime.datetime

    class Config:
        orm_mode = True 
