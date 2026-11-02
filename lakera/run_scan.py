"""Run a Lakera Red static scan for the four security objectives."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from harness.client import SupportAgentClient  # noqa: E402

OBJECTIVES = [
    "security.instruction-override.1",
    "security.system-prompt-extraction.1",
    "security.tool-extraction.1",
    "security.data-exfiltration.1",
]
APP_CONTEXT = Path(__file__).with_name("app_context.yaml")
TARGET_NAME = "sniffr-uat-support"


async def main() -> int:
    import os

    from lakera_red_sdk import LakeraRedClient, StaticStrategyOptions

    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
    api_key = (os.environ.get("LAKERA_RED_API_KEY") or "").strip()
    if not api_key:
        out_dir = ROOT / "results"
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "lakera-skipped.txt").write_text(
            "Lakera was not run because LAKERA_RED_API_KEY is empty.\n"
        )
        print("lakera skipped: missing LAKERA_RED_API_KEY", file=sys.stderr)
        return 2

    agent = SupportAgentClient()

    async def handler(session) -> None:
        async for message in session:
            reply = await asyncio.to_thread(agent.chat, message.attack, session.id)
            await message.respond(reply)

    out_dir = ROOT / "results"
    out_dir.mkdir(parents=True, exist_ok=True)

    async with LakeraRedClient(
        api_key=api_key,
        base_url="https://red-webhooks.lakera.ai",
        log_level="info",
    ) as client:
        target = await client.create_or_get_target(
            TARGET_NAME,
            app_context_file=str(APP_CONTEXT),
        )
        target_id = getattr(target, "target_id", None) or TARGET_NAME
        scan = await client.create_scan(
            target_id,
            name="Sniffr UAT security benchmark",
            strategy=StaticStrategyOptions(number_of_probes=5),
            objectives=OBJECTIVES,
            concurrency=2,
        )
        await scan.run(handler)
        await scan.write_results(str(out_dir / "lakera.json"))
        link = getattr(scan, "dashboard_link", "")
        (out_dir / "lakera-link.txt").write_text(str(link) + "\n")
        if link:
            print(f"lakera report: {link}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
