import asyncio
from pathlib import Path

import httpx

from app.api import app, provide_settings
from app.config import Settings


def test_health_reports_essential_components(tmp_path: Path) -> None:
    settings = Settings(
        documents_dir=tmp_path / "documents",
        processed_dir=tmp_path / "processed",
        chroma_dir=tmp_path / "chroma",
        logs_dir=tmp_path / "logs",
        llm_provider="none",
    )
    async def override_settings() -> Settings:
        return settings

    app.dependency_overrides[provide_settings] = override_settings

    async def request_health() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            return await client.get("/health")

    try:
        response = asyncio.run(request_health())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["retrieval"]["provider"] == "bm25"
    assert payload["configuration"]["top_k"] == 8
    assert payload["configuration"]["llm_temperature"] == 0.1
    assert payload["configuration"]["corpus"]["artifact_count"] == 0
    assert payload["chroma"]["available"] is True
    assert payload["embeddings"]["available"] is True
    assert payload["llm"] == {
        "available": False,
        "provider": "none",
        "detail": "not_configured",
    }
    assert "api_key" not in response.text.lower()
