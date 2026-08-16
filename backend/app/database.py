from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from .config import settings

engine = create_async_engine(settings.database_url, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with async_session() as session:
        yield session


# Hand-rolled, idempotent schema patches applied on every startup.
#
# create_all() creates missing *tables* but never adds missing *columns* to
# tables that already exist, so columns introduced after a database was first
# created have to be patched in here. Each block is written to be safe to run
# repeatedly.
#
# This is a stopgap. The right answer is Alembic, and it gets cheaper to adopt
# the sooner it happens — see IMPROVEMENT-PLAN.md.
_MIGRATIONS = """
DO $$
BEGIN
    -- projects.status ------------------------------------------------------
    -- Older databases got this column as VARCHAR(20) from a previous version
    -- of this block, while databases created by create_all() got the native
    -- projectstatus enum. That divergence meant the same code ran against two
    -- different schemas. Converge everything on the enum.

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'projectstatus') THEN
        CREATE TYPE projectstatus AS ENUM ('active', 'on_hold', 'deprecated');
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'projects' AND column_name = 'status'
    ) THEN
        ALTER TABLE projects
            ADD COLUMN status projectstatus DEFAULT 'active'::projectstatus;
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'projects'
          AND column_name = 'status'
          AND data_type = 'character varying'
    ) THEN
        ALTER TABLE projects ALTER COLUMN status DROP DEFAULT;
        ALTER TABLE projects
            ALTER COLUMN status TYPE projectstatus USING status::projectstatus;
        ALTER TABLE projects
            ALTER COLUMN status SET DEFAULT 'active'::projectstatus;
    END IF;

    -- projects.tags --------------------------------------------------------
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'projects' AND column_name = 'tags'
    ) THEN
        ALTER TABLE projects ADD COLUMN tags JSONB DEFAULT '[]'::jsonb;
    END IF;
END $$;
"""


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(text(_MIGRATIONS))
