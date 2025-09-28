from passlib.context import CryptContext
import hashlib
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.users import User
from app.models.user_roles import UserRole
from app.models.roles import Role
from app.models.user_tenants import UserTenant

pwd_context = CryptContext(schemes=['bcrypt_sha256'], deprecated='auto')

# --- Password helpers ---
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)

# --- Queries ---
async def get_user_by_email(db: AsyncSession, email: str):
    result = await db.execute(select(User).where(User.email == email))
    return result.scalars().first()

async def get_user_by_id(db: AsyncSession, user_id):
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalars().first()

async def get_user_roles(db: AsyncSession, user_id, tenant_id):
    result = await db.execute(
        select(Role.name)
        .join(UserRole, UserRole.role_id == Role.id)
        .join(UserTenant, UserTenant.id == UserRole.usertenant_id)
        .where((UserTenant.user_id == user_id) & (UserTenant.tenant_id == tenant_id))
    )
    roles = [row[0] for row in result.all()]
    return roles

# --- Authentication ---
async def authenticate_user(db: AsyncSession, email: str, password: str):
    user = await get_user_by_email(db, email)
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user




