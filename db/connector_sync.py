from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from utils.env_variables import DATABASE_URL


engine_sync = create_engine(
    DATABASE_URL.replace("+asyncpg", ""),
    poolclass=NullPool,
    future=True,
    echo=False  # Ustaw True do debugowania SQL
)
# /|\ poolclass:
# - NIE przechowuje połączeń
# - Każde zapytanie → nowe połączenie → zamyka natychmiast
# - Wolniejsze, ale bezpieczne dla multiprocessingu

SessionSync = sessionmaker(bind=engine_sync, expire_on_commit=False)
