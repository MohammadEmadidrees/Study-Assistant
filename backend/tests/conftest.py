import pytest
import asyncio
import sys
from pathlib import Path
import anyio
from sse_starlette.sse import AppStatus

# Add backend root to sys.path
backend_root = Path(__file__).resolve().parents[1]
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from app.core.database import init_db


@pytest.fixture(autouse=True)
def reset_sse_event():
    """Ensure AppStatus event loop is reset per test session to avoid cross-loop binding."""
    AppStatus.should_exit_event = anyio.Event()
    yield


@pytest.fixture(autouse=True, scope="session")
def setup_test_db():
    """Ensure database tables are initialized and active engine is resolved once for test session."""
    asyncio.run(init_db())
    yield
