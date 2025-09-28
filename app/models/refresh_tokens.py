from sqlalchemy import Column, Boolean, DateTime, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from .base import Base

class RefreshToken(Base):
    id = Column(UUID(as_uuid=True), primary_key=True)
    user_tenant_id = Column(UUID(as_uuid=True), ForeignKey("user_tenants.id"), nullable=False)
    jti = Column(String, nullable=False, unique=True)  
    revoked = Column(Boolean, default=False)          
    expires_at = Column(DateTime(timezone=True), nullable=False)
    user_agent = Column(String, nullable=True)        
    ip = Column(String, nullable=True)                
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))

    user_tenant = relationship("UserTenant", backref="refresh_tokens")
