"""Smoke-check the agent, then run Promptfoo, Garak, and Lakera."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(command: list[str]) -> int:
    print("+", " ".join(command), flush=True)
    completed = subprocess.run(command, cwd=ROOT, check=False)
    return completed.returncode


def main() -> int:
    smoke = run([sys.executable, "-m", "harness.smoke"])
    if smoke != 0:
        print("stopped: smoke check failed", file=sys.stderr)
        return smoke
    promptfoo = run(
        [
            "npx",
            "--yes",
            "promptfoo@latest",
            "redteam",
            "run",
            "-c",
            "promptfoo/promptfooconfig.yaml",
            "-o",
            "results/promptfoo.json",
        ]
    )
    garak = run([sys.executable, "garak/run.py"])
    lakera = run([sys.executable, "lakera/run_scan.py"])
    run([sys.executable, "report/normalize.py"])
    if promptfoo != 0 or garak != 0 or lakera not in (0, 2):
        return promptfoo or garak or lakera
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
