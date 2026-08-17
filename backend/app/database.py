import asyncio
import logging
from pathlib import Path

from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory

from .config import settings

logger = logging.getLogger("flowtrack")

engine = create_async_engine(settings.database_url, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

ALEMBIC_INI = Path(__file__).resolve().parents[1] / "alembic.ini"


class Base(DeclarativeBase):
    pass


async def get_db():
    async with async_session() as session:
        yield session


def _inspect_state(sync_conn) -> tuple[bool, bool]:
    """(has application tables, has an alembic version table)."""
    tables = set(inspect(sync_conn).get_table_names())
    return "projects" in tables, "alembic_version" in tables


def _config() -> Config:
    cfg = Config(str(ALEMBIC_INI))
    cfg.set_main_option("script_location", str(ALEMBIC_INI.parent / "alembic"))
    return cfg


def _adopt_and_upgrade() -> None:
    """Stamp a pre-Alembic database at the base revision, then migrate forward.

    Stamping straight to head would be wrong as soon as a second revision
    exists: the legacy schema matches the *initial* revision, not whatever the
    latest one happens to be.

    Called via asyncio.to_thread — alembic's env.py drives the async engine with
    asyncio.run(), which raises if a loop is already running on the thread, and
    FastAPI's lifespan hook is exactly that situation.
    """
    cfg = _config()
    base = ScriptDirectory.from_config(cfg).get_base()
    command.stamp(cfg, base)
    command.upgrade(cfg, "head")


def _upgrade() -> None:
    command.upgrade(_config(), "head")


async def init_db() -> None:
    """Bring the schema up to date, adopting a pre-Alembic database if needed.

    Replaces the previous create_all() plus a hand-written DO block. That
    approach could not add columns to existing tables reliably, and produced
    different column types depending on whether a database was created fresh or
    patched — projects.status was a native enum in one case and VARCHAR in the
    other.
    """
    async with engine.begin() as conn:
        has_tables, has_version = await conn.run_sync(_inspect_state)

    if has_tables and not has_version:
        # A database created by the old create_all() path. Its schema already
        # matches the initial revision, so record that rather than replaying it.
        logger.info("Adopting existing pre-Alembic database: stamping base, then upgrading")
        await asyncio.to_thread(_adopt_and_upgrade)
        return

    await asyncio.to_thread(_upgrade)
