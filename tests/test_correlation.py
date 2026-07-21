from datetime import datetime

from app.proxy.correlation import (
    CORRELATION_ID_HEADER,
    generate_correlation_id,
    parse_correlation_id,
    received_at_iso,
)


def test_generate_correlation_id_uses_expected_prefix():
    correlation_id = generate_correlation_id()

    assert correlation_id.startswith("corr_")
    assert len(correlation_id) == len("corr_") + 32


def test_parse_correlation_id_accepts_valid_inbound_header():
    assert (
        parse_correlation_id({CORRELATION_ID_HEADER: " client-request-123 "})
        == "client-request-123"
    )


def test_parse_correlation_id_generates_for_invalid_inbound_header():
    correlation_id = parse_correlation_id({CORRELATION_ID_HEADER: "bad\nvalue"})

    assert correlation_id.startswith("corr_")


def test_received_at_iso_is_timezone_aware():
    received_at = datetime.fromisoformat(received_at_iso())

    assert received_at.tzinfo is not None
