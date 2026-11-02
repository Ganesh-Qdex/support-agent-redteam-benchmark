"""Promptfoo target. Every attack is sent through harness.client."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from harness.client import SupportAgentClient  # noqa: E402

_CLIENT: SupportAgentClient | None = None


def call_api(prompt, options, context):  # noqa: ARG001
    global _CLIENT
    if _CLIENT is None:
        _CLIENT = SupportAgentClient()
    text = prompt if isinstance(prompt, str) else str(prompt)
    try:
        output = _CLIENT.chat(text)
    except RuntimeError as exc:
        return {"error": str(exc)}
    return {"output": output}
