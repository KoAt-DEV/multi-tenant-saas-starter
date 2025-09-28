from sqlalchemy import Column, String, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from .base import Base

class AuditLog(Base):
    id = Column(UUID(as_uuid=True), primary_key=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    action = Column(String, nullable=False)        
    entity = Column(String, nullable=True)          
    entity_id = Column(UUID(as_uuid=True), nullable=True) 
    meta_data = Column(JSON, nullable=True)          
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))

    tenant = relationship("Tenant", backref="audit_logs")
    user = relationship("User", backref="audit_logs")
