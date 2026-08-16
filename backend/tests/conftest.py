import asyncio
import os
import tempfile

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

os.environ["API_KEY"] = "test_key"

# The setup_db fixture below runs drop_all after every single test. Pointing it
# at a real database destroys it. Default to a dedicated `_test` database and
# refuse to start if the target does not look like a throwaway.
DEFAULT_TEST_DB = (
    "postgresql+asyncpg://flowtrack:flowtrack_secret@localhost:7029/flowtrack_test"
)
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", DEFAULT_TEST_DB)

_db_name = TEST_DATABASE_URL.rsplit("/", 1)[-1].split("?", 1)[0]
if not _db_name.endswith("_test"):
    raise RuntimeError(
        f"Refusing to run: the test suite drops every table, and "
        f"TEST_DATABASE_URL points at the database {_db_name!r}, whose name does "
        f"not end in '_test'. Create a throwaway database first, e.g.\n\n"
        f"    docker compose exec db psql -U flowtrack -d postgres "
        f"-c 'CREATE DATABASE flowtrack_test;'\n"
    )

os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["STORAGE_PATH"] = tempfile.mkdtemp(prefix="flowtrack_test_storage_")

from app.database import Base, get_db
from app.main import app

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=NullPool)
test_session = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def override_get_db():
    async with test_session() as session:
        yield session


app.dependency_overrides[get_db] = override_get_db


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


HEADERS = {"X-API-Key": "test_key"}
