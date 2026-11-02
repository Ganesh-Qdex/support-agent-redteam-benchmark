"""Send one benign turn. Exit 0 only when the agent returns text."""

from __future__ import annotations

import sys

from harness.client import SupportAgentClient


def main() -> int:
    client = SupportAgentClient()
    try:
        reply = client.chat("hello")
    except RuntimeError as exc:
        print(f"smoke failed: {exc}", file=sys.stderr)
        return 1
    print("smoke ok")
    print(reply[:500])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
