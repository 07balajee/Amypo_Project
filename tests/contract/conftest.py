
import pytest
from fastapi.testclient import TestClient

from app.core import config as config_module
from app.core.db import conn as conn_module


@pytest.fixture()
def isolated_settings(tmp_path, monkeypatch):
    """Use the sqlite backend in a fresh tmp dir (no MySQL server needed) and force MockGateway."""
    monkeypatch.setenv("DB__BACKEND", "sqlite")
    monkeypatch.setenv("DB__SQLITE__DIR", str(tmp_path))
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
