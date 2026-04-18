"""Database initialisation script — applies schema.sql then seed.sql.

Run with:
    python -m backend.db.init_db

Requires DATABASE_URL to be set in .env (or the environment).
All SQL statements are idempotent (IF NOT EXISTS / ON CONFLICT DO NOTHING),
so this script is safe to re-run against an existing database.
"""

import asyncio
import logging
import pathlib

logger = logging.getLogger(__name__)

_DB_DIR = pathlib.Path(__file__).parent
_SCHEMA_SQL = (_DB_DIR / "schema.sql").read_text()
_SEED_SQL = (_DB_DIR / "seed.sql").read_text()


async def _run() -> None:
    import asyncpg
    from backend.config import settings

    # asyncpg uses a plain postgresql:// DSN, not the SQLAlchemy dialect prefix
    dsn = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")

    logger.info("Connecting to database…")
    conn: asyncpg.Connection = await asyncpg.connect(dsn, ssl="require")
    try:
        logger.info("Applying schema.sql…")
        await conn.execute(_SCHEMA_SQL)
        logger.info("Applying seed.sql…")
        await conn.execute(_SEED_SQL)
        logger.info("✓ Database initialised successfully")
    finally:
        await conn.close()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)-8s %(message)s",
    )
    asyncio.run(_run())
