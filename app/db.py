from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.config import settings


engine = create_async_engine(settings.DB_URL, echo=True, future=True)

AsyncLocalSession = sessionmaker(
    bind= engine,
    autoflush= False,
    autocommit= False,
    expire_on_commit= False,
    class_= AsyncSession
)

async def get_db():
    async with AsyncLocalSession() as session:
        yield session