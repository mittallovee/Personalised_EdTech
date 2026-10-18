from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from qbank.core.config import AppEnv, Settings
from qbank.main import create_app

# A URL that is never reachable: the engine connects lazily, so tests that don't touch the database
# can build the app without a server.
UNREACHABLE_DB = "postgresql+psycopg://nobody:nothing@127.0.0.1:1/none"


def make_settings(database_url: str = UNREACHABLE_DB) -> Settings:
    return Settings(app_env=AppEnv.TEST, database_url=database_url)


@pytest.fixture
def app() -> FastAPI:
    return create_app(make_settings())


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
