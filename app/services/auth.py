from datetime import datetime, timedelta, timezone
from typing import Optional, Annotated
from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.crud.user import hash_password
from app.models.password_reset import PasswordReset
from app.models.users import User
from app.models.tenants import Tenant
from app.models.user_tenants import UserTenant
from app.db import get_db
import uuid
from sqlalchemy.future import select

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.JWT_ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS = settings.REFRESH_TOKEN_EXPIRE_DAYS

oaut2_scheme = OAuth2PasswordBearer(tokenUrl='/api/auth/token', scheme_name='JWT')

def create_access_token(data: dict, expire_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expire_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({'exp': expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str):
    try: 
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    
    except JWTError as e:
        print(f'Failed to decode token: {e}')
        return None
    
async def get_current_user_object(
        token: Annotated[str, Depends(oaut2_scheme)]
):
    credential_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"}
    )

    print("Validating token...")
    payload = decode_access_token(token)
    if payload is None or "sub" not in payload:
        print("Failed to decode token")
        raise credential_exception
    
    return {
        "user_id": payload["sub"],
        "tenant_id": payload.get("tid"),
        "roles": payload.get("roles", [])
    }

async def get_current_user( token: Annotated[str, Depends(oaut2_scheme)],
                            db: Annotated[AsyncSession, Depends(get_db)] 
        ): 
        
        credential_exception = HTTPException( 
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Could not validate credentials", 
            headers={"WWW-Authenticate": "Bearer"} 
            ) 
        
        print("Validating token...") 

        payload = decode_access_token(token) 
        if payload is None or "sub" not in payload: 
            print("Failed to decode token") 
            raise credential_exception 
        
        user_id = payload["sub"] # UUID string 
        user = await db.get(User, uuid.UUID(user_id)) 
        if user is None: 
            raise credential_exception 
        
        return user

async def get_current_user_with_tenant(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),  
) -> UserTenant:
    tenant: Tenant = request.state.tenant
    if not tenant:
        raise HTTPException(status_code=400, detail="Tenant not resolved")

    result = await db.execute(
    select(UserTenant).where(
        (UserTenant.user_id == uuid.UUID(current_user["user_id"])) &
        (UserTenant.tenant_id == tenant.id)
    )
)

    user_tenant = result.scalars().first()

    if not user_tenant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not belong to this tenant"
        )
    return user_tenant


def create_refresh_token(data: dict, expire_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expire_delta or timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS))
    to_encode.update({
        "exp": expire,
        "jti": str(uuid.uuid4())  
    })
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


async def generate_reset_token(db: AsyncSession, user: User, expires_in_minutes: int = 60) -> str:
    token = str(uuid.uuid4())
    expire_at = datetime.now(timezone.utc) + timedelta(minutes=expires_in_minutes)

    reset = PasswordReset(
        id=uuid.uuid4(),
        user_id=user.id,
        token=token,
        expires_at=expire_at,
        used=False,
        created_at=datetime.now(timezone.utc)
    )
    db.add(reset)
    await db.commit()
    await db.refresh(reset)
    return token


async def verify_reset_token(db: AsyncSession, token: str) -> User:
    stmt = await db.execute(select(PasswordReset).where(
        PasswordReset.token == token,
        PasswordReset.used == False,
        PasswordReset.expires_at >= datetime.datetime.now(timezone.utc)
    ))
    reset_record = stmt.scalars().first()
    if not reset_record:
        return None

    stmt_user = await db.execute(select(User).where(User.id == reset_record.user_id))
    user = stmt_user.scalars().first()
    return user, reset_record


async def reset_user_password(db: AsyncSession, user: User, reset_record: PasswordReset, new_password: str):
    user.password_hash = hash_password(new_password)
    reset_record.used = True
    await db.commit()