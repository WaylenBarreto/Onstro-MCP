"""
pytest configuration — force MOCK_MODE so tests never hit a real API server.

The `get_settings()` function uses @lru_cache, so we clear the cache after
patching the environment to ensure every test session uses mock data.
"""
import os

# Set before any pm_mcp module is imported so pydantic-settings picks it up.
os.environ["MOCK_MODE"] = "true"

# Clear the settings cache in case it was already populated (e.g. by a
# previous import that ran before conftest).
from pm_mcp.config import get_settings  # noqa: E402

get_settings.cache_clear()
