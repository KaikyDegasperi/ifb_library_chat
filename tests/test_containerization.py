from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_docker_image_excludes_data_and_runs_as_non_root() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    dockerignore = (ROOT / ".dockerignore").read_text(encoding="utf-8")

    assert "USER 10001:10001" in dockerfile
    assert "COPY . " not in dockerfile
    assert "COPY pdfs_ifb" not in dockerfile
    assert "COPY .env" not in dockerfile
    assert "pdfs_ifb" in dockerignore
    assert "data" in dockerignore
    assert "logs" in dockerignore
    assert "*.pdf" in dockerignore
    assert ".env" in dockerignore


def test_compose_separates_services_and_persists_runtime_data() -> None:
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")

    assert "  api:" in compose
    assert "  frontend:" in compose
    assert "API_BASE_URL: http://api:8000" in compose
    assert "condition: service_healthy" in compose
    assert "127.0.0.1" in compose
    for volume in (
        "pdfs_data",
        "processed_data",
        "chroma_data",
        "logs_data",
        "model_cache",
    ):
        assert volume in compose
    assert compose.count("healthcheck:") == 2
    assert "ADMIN_API_TOKEN:" not in compose


def test_docker_example_and_smoke_test_do_not_contain_secrets() -> None:
    example = (ROOT / ".env.docker.example").read_text(encoding="utf-8")
    smoke_test = (ROOT / "scripts/container-smoke-test.sh").read_text(
        encoding="utf-8"
    )
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")

    assert "ADMIN_API_TOKEN=\n" in example
    assert "LLM_API_KEY=\n" in example
    assert ".env.docker" in gitignore
    assert "docker compose up --build --detach --wait" in smoke_test
    assert "/health" in smoke_test
    assert "/_stcore/health" in smoke_test
