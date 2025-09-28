from sqlalchemy import Column, String, Boolean, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime, timezone
from .base import Base

class Tenant(Base):
    id = Column(UUID(as_uuid=True), primary_key=True)
    name = Column(String, nullable=False)
    subdomain = Column(String, unique=True, nullable=False)
    code = Column(String, unique=True, nullable=False)
    status = Column(Boolean, default=True)
    custom_domain = Column(String, nullable=True)
    branding = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))