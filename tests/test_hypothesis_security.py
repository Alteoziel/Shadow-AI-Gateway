"""Hypothesis property tests for security helpers."""

from __future__ import annotations

import pytest
from app.proxy.interceptor import intercept_outbound_request
from app.security.auth import key_fingerprint
from app.security.egress import ALLOWED_HOSTS, is_allowed_url
from fastapi import HTTPException
from hypothesis import given, settings
from hypothesis import strategies as st

_MAX = settings(max_examples=50)

_host_chars = st.sampled_from("abcdefghijklmnopqrstuvwxyz0123456789-")
_label = st.text(alphabet=_host_chars, min_size=1, max_size=12).filter(
    lambda s: not s.startswith("-") and not s.endswith("-")
)
_hostname = st.lists(_label, min_size=1, max_size=3).map(".".join).filter(
    lambda h: h.lower() not in ALLOWED_HOSTS
)
_path = st.sampled_from(["", "/", "/v1", "/v1/chat", "/exfil?x=1"])
_non_https = st.sampled_from(["http", "ftp", "ws", "wss", "file"])


@_MAX
@given(scheme=_non_https, host=_hostname, path=_path)
def test_is_allowed_url_never_true_for_non_https(
    scheme: str, host: str, path: str
) -> None:
    assert is_allowed_url(f"{scheme}://{host}{path}") is False


@_MAX
@given(
    host=st.one_of(
        _hostname,
        st.sampled_from(["evil.example.com", "127.0.0.1", "localhost", "api.openai.com.evil"]),
    ),
    path=_path,
)
def test_is_allowed_url_never_true_for_non_allowlisted_https(host: str, path: str) -> None:
    assert is_allowed_url(f"https://{host}{path}") is False


@_MAX
@given(scheme=_non_https, path=_path)
def test_is_allowed_url_never_true_for_http_even_on_allowlisted_hosts(
    scheme: str, path: str
) -> None:
    for host in ALLOWED_HOSTS:
        assert is_allowed_url(f"{scheme}://{host}{path}") is False


@_MAX
@given(token=st.text())
def test_key_fingerprint_stable_and_length_16(token: str) -> None:
    first = key_fingerprint(token)
    second = key_fingerprint(token)
    assert first == second
    assert len(first) == 16
    assert all(c in "0123456789abcdef" for c in first)


@_MAX
@given(
    model=st.one_of(
        st.just(""),
        st.just("   "),
        st.just("\t"),
        st.none(),
        st.integers(),
        st.lists(st.text(), max_size=2),
    )
)
@pytest.mark.asyncio
async def test_interceptor_rejects_empty_or_invalid_model(model: object) -> None:
    with pytest.raises(HTTPException) as exc_info:
        await intercept_outbound_request(
            body={
                "model": model,
                "messages": [{"role": "user", "content": "hi"}],
            },
        )
    assert exc_info.value.status_code == 400
    assert "model" in str(exc_info.value.detail).lower()


@_MAX
@given(
    messages=st.one_of(
        st.just([]),
        st.just(None),
        st.just("not-a-list"),
        st.integers(),
    )
)
@pytest.mark.asyncio
async def test_interceptor_rejects_empty_or_invalid_messages(messages: object) -> None:
    with pytest.raises(HTTPException) as exc_info:
        await intercept_outbound_request(
            body={"model": "gpt-4o-mini", "messages": messages},
        )
    assert exc_info.value.status_code == 400
    assert "messages" in str(exc_info.value.detail).lower()
