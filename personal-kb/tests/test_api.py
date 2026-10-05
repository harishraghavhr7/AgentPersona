import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from starlette.testclient import TestClient
from api.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "qdrant_status" in data
    assert "ollama_status" in data
    assert "llm_fallback_chain" in data
    assert data["llm_fallback_chain"] == ["groq", "gemini", "openrouter"]
    assert "providers_configured" in data


def test_documents_endpoint(client):
    response = client.get("/documents")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_query_endpoint(client):
    response = client.post(
        "/query",
        json={"query": "What is my current production database decision?"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert "sources" in data
    assert data["query_type"] == "CURRENT_STATE"
