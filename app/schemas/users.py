from pydantic import BaseModel, EmailStr
from uuid import UUID
from typing import Optional, List
import datetime

class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str]


class UserRead(UserBase):
    id: UUID
    is_active: bool
    is_superuser: bool
    created_at: datetime.datetime
    updated_at: datetime.datetime

    class Config:
        orm_mode = True


class MeResponse(BaseModel):
    user_name: str
    user_email: str
    tenant_name: str
    roles: List[str]
