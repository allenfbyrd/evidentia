"""Shared fixtures for FastAPI TestClient coverage of the controlbridge-api layer.

Each test gets a fresh FastAPI app + TestClient. The gap store is redirected
to a per-test tmp_path so saved reports don't leak between tests or into the
developer's real platformdirs store.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def api_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """Fresh TestClient backed by a tmp_path gap store + clean config dir."""
    # Redirect the gap store to tmp_path so save_report/list_reports don't
    # touch the developer's real user-data directory.
    monkeypatch.setenv("CONTROLBRIDGE_GAP_STORE_DIR", str(tmp_path / "gap_store"))
    # Avoid picking up any parent controlbridge.yaml during find_config_file().
    monkeypatch.chdir(tmp_path)

    # Clear the config loader's LRU cache from previous tests.
    from controlbridge_core.config import _load_config_cached

    _load_config_cached.cache_clear()

    # Reset network-guard state so a prior test can't leak offline-mode.
    from controlbridge_core.network_guard import set_offline

    set_offline(False)

    # Reset the framework registry singleton — some tests mutate it.
    from controlbridge_core.catalogs.registry import FrameworkRegistry

    FrameworkRegistry.reset_instance()

    from controlbridge_api.app import create_app

    client = TestClient(create_app())
    return client
