# tests/test_smoke.py
# -------------------------------
# Minimal smoke test to ensure the Flask app can create a test client
# and that the "/" route returns HTTP 200 with expected content.
# Run with: pytest -q
# -------------------------------

import pytest
from app import create_app


@pytest.fixture
def client():
    app = create_app()
    app.testing = True
    with app.test_client() as client:
        yield client


def test_home_route_loads(client):
    resp = client.get("/")
    assert resp.status_code == 200
    # Brand/title should be stable across steps.
    assert b"March Madness Madness" in resp.data
    # The page renders a table header for seeded games.
    assert b"Round of" in resp.data
