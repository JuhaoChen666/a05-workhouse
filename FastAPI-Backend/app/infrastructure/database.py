import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

# 获取数据库连接URL，默认使用MySQL+aiomysql
DATABASE_URL = os.getenv("DATABASE_URL", "mysql+aiomysql://root:password@localhost:3306/emo2vec")

# 创建异步引擎
engine = create_async_engine(
    DATABASE_URL,
    echo=os.getenv("APP_DEBUG", "false").lower() == "true",
    pool_size=int(os.getenv("DATABASE_POOL_SIZE", 20)),
    max_overflow=int(os.getenv("DATABASE_MAX_OVERFLOW", 30)),
    pool_pre_ping=True,
    pool_recycle=3600
)

# 创建异步Session工厂
AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False,
)

async def get_db_session() -> AsyncSession:
    """获取数据库Session生成器（FastAPI Depends注入用或独立使用）"""
    from app.infrastructure.resume_runtime import session_factory
    async with session_factory()() as session:
        yield session
