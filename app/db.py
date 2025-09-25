from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from urllib.parse import quote_plus
from app.config import settings

password = quote_plus(settings.DB_PASSWORD)
DATABASE_URL = (
    f"mysql+aiomysql://{settings.DB_USER}:"
    f"{password}@{settings.DB_HOST}:"
    f"{settings.DB_PORT}/{settings.DB_DATABASE}"
)

engine = create_async_engine(DATABASE_URL)


# Tạo session factory
SessionLocal = async_sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, class_=AsyncSession)


# Dependency cho FastAPI
async def get_session():
    async with SessionLocal() as session:
        yield session

