
import pytest
from fastapi.testclient import TestClient

from app.core import config as config_module
from app.core.db import conn as conn_module


@pytest.fixture()
def isolated_settings(tmp_path, monkeypatch):
    """Point ops/amypo DBs at a fresh tmp dir and force MockGateway, per test."""
    monkeypatch.setenv("DB__OPS_DB_PATH", str(tmp_path / "ops.db"))
    monkeypatch.setenv("DB__AMYPO_DB_PATH", str(tmp_path / "amypo.db"))
    monkeypatch.setenv("GATEWAY__USE_MOCK", "true")
    config_module.get_settings(reload=True)
    conn_module._initialized.clear()
    yield
    config_module.get_settings(reload=True)


@pytest.fixture()
def router_client(isolated_settings):
    from app.router.api import app

    with TestClient(app) as client:
        yield client


@pytest.fixture()
def qa_client(isolated_settings):
    from app.qa.api import app

    with TestClient(app) as client:
        yield client
