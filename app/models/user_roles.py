from sqlalchemy import Column, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .base import Base

class UserRole(Base):
    id = Column(UUID(as_uuid=True), primary_key=True)
    usertenant_id = Column(UUID(as_uuid=True), ForeignKey("user_tenants.id"), nullable=False)
    role_id = Column(UUID(as_uuid=True), ForeignKey("roles.id"), nullable=False)

    user_tenant = relationship("UserTenant", backref="roles")
    role = relationship("Role", backref="user_roles")

