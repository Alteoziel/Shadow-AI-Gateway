"""Locust load smoke for the gateway health + chat endpoints."""

from __future__ import annotations

import os

from locust import HttpUser, between, task

GATEWAY_API_KEY = os.environ.get("GATEWAY_API_KEY", "test-gateway-key")

CHAT_BODY = {
    "model": "gpt-4o-mini",
    "messages": [{"role": "user", "content": "ping"}],
    "stream": False,
}


class GatewayUser(HttpUser):
    wait_time = between(0.5, 2.0)

    def on_start(self) -> None:
        self.client.headers.update(
            {"Authorization": f"Bearer {GATEWAY_API_KEY}"},
        )

    @task(5)
    def health(self) -> None:
        self.client.get("/health", name="GET /health")

    @task(1)
    def chat_completions(self) -> None:
        self.client.post(
            "/v1/chat/completions",
            json=CHAT_BODY,
            name="POST /v1/chat/completions",
        )
