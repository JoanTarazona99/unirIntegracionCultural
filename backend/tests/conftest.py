"""
Shared pytest fixtures for the KubGU Assistant backend test suite.

This provides a FastAPI ``TestClient`` bound to the real application defined in
``main.py``. The app is imported once per session because its startup
initializes the RAG engine, translator and other singletons.
"""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="session")
def app():
    """Import and return the FastAPI application instance."""
    import main
    return main.app


@pytest.fixture(scope="session")
def client(app):
    """A TestClient for issuing HTTP requests against the app."""
    with TestClient(app) as test_client:
        yield test_client
