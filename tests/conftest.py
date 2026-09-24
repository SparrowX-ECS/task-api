import os
import sys
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

sys.path.insert(0, str(Path(__file__).parents[1]))
os.environ.setdefault("DB_HOST", "127.0.0.1")
os.environ.setdefault("DB_PORT", "5433")
os.environ.setdefault("DB_NAME", "taskdb")
os.environ.setdefault("DB_USERNAME", "postgres")
os.environ.setdefault("DB_PASSWORD", "postgres")

from src.main import create_app


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    application = create_app(enable_metrics=False)
    async with AsyncClient(transport=ASGITransport(app=application), base_url="http://test") as test_client:
        yield test_client
