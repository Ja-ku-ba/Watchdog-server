import os
import subprocess
import sys

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base

from utils.env_variables import DATABASE_URL

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)
Base = declarative_base()


async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session


async def run_migrations_once():
    try:
        db_url = DATABASE_URL
        if db_url.startswith("postgresql+asyncpg://"):
            alembic_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
            os.environ["DATABASE_URL_ALEMBIC"] = alembic_url

        # upgrade bez generowania plików
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            print("Migracje zaaplikowane lub brak nowych migracji.")
        else:
            print(f"Błąd migracji:\n{result.stderr}")

    except Exception as e:
        print(f"Błąd podczas uruchamiania migracji: {e}")


