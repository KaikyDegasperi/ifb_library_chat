import logging

from app.logging_config import StructuredFormatter


def test_structured_observability_fields_do_not_include_credentials() -> None:
    record = logging.LogRecord(
        name="app.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="rag_request_completed",
        args=(),
        exc_info=None,
    )
    record.request_id = "request-1"
    record.endpoint = "/chat"
    record.status = "ok"
    record.duration_ms = 12
    record.source_count = 2
    record.context_chars = 800
    record.error_type = "none"

    output = StructuredFormatter().format(record)

    assert 'request_id="request-1"' in output
    assert 'source_count="2"' in output
    assert "Authorization" not in output
    assert "ADMIN_API_TOKEN" not in output
    assert "LLM_API_KEY" not in output
