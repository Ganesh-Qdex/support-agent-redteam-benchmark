"""HTTP client for the Sniffr UAT support agent.

The endpoint does not require authentication. The attack text is sent as `query`.
Identity and token fields stay in the body as empty strings so the JSON shape
matches the chat API.
"""

from __future__ import annotations

import uuid

import requests

ENDPOINT = "https://support-agents-uat-493458094930.asia-southeast1.run.app/chat"


class SupportAgentClient:
    """Posts one user turn and returns the agent's `response` text."""

    def build_body(self, payload: str, session_id: str) -> dict:
        return {
            "user_id": "",
            "query": payload,
            "session_id": session_id,
            "auth_token": "",
            "context": {
                "auth_token": "",
                "user_email": "",
                "user": {
                    "email": "",
                    "uid": "",
                    "displayName": None,
                },
            },
        }

    def chat(self, payload: str, session_id: str | None = None) -> str:
        session = session_id or f"session_{uuid.uuid4().hex}"
        response = requests.post(
            ENDPOINT,
            json=self.build_body(payload, session),
            headers={"Content-Type": "application/json"},
            timeout=120,
        )
        if response.status_code != 200:
            raise RuntimeError(f"chat failed status {response.status_code}")
        try:
            data = response.json()
        except ValueError as exc:
            raise RuntimeError("chat returned non-json") from exc
        text = data.get("response") if isinstance(data, dict) else None
        if not isinstance(text, str) or not text.strip():
            raise RuntimeError("chat returned an empty response field")
        return text
