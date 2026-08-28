"""
Shared pytest fixtures for the KubGU Assistant backend test suite.

This provides a FastAPI ``TestClient`` bound to the real application defined in
``main.py``. The app is imported once per session because its startup
initializes the RAG engine, translator and other singletons.
"""

import socket
import urllib.request

import pytest


@pytest.fixture(autouse=True)
def block_external_network(monkeypatch):
    """Fail closed if any test attempts a real network connection."""
    def blocked(*args, **kwargs):
        raise RuntimeError("External network access is disabled during pytest")

    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)
    monkeypatch.setattr(urllib.request, "urlopen", blocked)


@pytest.fixture(scope="session")
def app():
    """Import and return the FastAPI application instance."""
    import main
    return main.app


@pytest.fixture(scope="session")
def client(app):
    """A TestClient for issuing HTTP requests against the app."""
    from fastapi.testclient import TestClient

    with TestClient(app) as test_client:
        yield test_client
