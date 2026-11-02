"""Render the REST config and run a capped Garak scan. No auth is sent."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SPEC_FILE = Path(__file__).with_name("spec.txt")
TEMPLATE = Path(__file__).with_name("rest.json")


def _fill(value: object, replacements: dict[str, str]) -> object:
    if isinstance(value, str):
        for needle, replacement in replacements.items():
            value = value.replace(needle, replacement)
        return value
    if isinstance(value, list):
        return [_fill(item, replacements) for item in value]
    if isinstance(value, dict):
        return {key: _fill(item, replacements) for key, item in value.items()}
    return value


def render_config(session_id: str) -> Path:
    template = json.loads(TEMPLATE.read_text())
    rendered_doc = _fill(template, {"$SESSION_ID": session_id})
    out_dir = ROOT / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    rendered = out_dir / "garak.rest.json"
    rendered.write_text(json.dumps(rendered_doc, indent=2) + "\n")
    return rendered


def _prepare_runtime() -> None:
    data_home = ROOT / ".garak"
    os.environ["XDG_DATA_HOME"] = str(data_home)
    os.environ["XDG_CACHE_HOME"] = str(data_home)
    os.environ["XDG_CONFIG_HOME"] = str(data_home)
    payload_dir = data_home / "garak" / "data" / "payloads"
    payload_dir.mkdir(parents=True, exist_ok=True)
    source = Path(__file__).with_name("payloads") / "benchmark_canary.json"
    (payload_dir / "benchmark_canary.json").write_text(source.read_text())


def main() -> int:
    _prepare_runtime()
    spec = SPEC_FILE.read_text().strip()
    session_id = f"session_garak_{uuid.uuid4().hex[:12]}"
    rendered = render_config(session_id)
    report_prefix = ROOT / "results" / "garak"
    command = [
        sys.executable,
        "-m",
        "garak",
        "--config",
        str(Path(__file__).with_name("run.yaml")),
        "--target_type",
        "rest.RestGenerator",
        "-G",
        str(rendered),
        "--spec",
        spec,
        "--parallel_attempts",
        "2",
        "--generations",
        "1",
        "--report_prefix",
        str(report_prefix),
    ]
    print("garak spec:", spec)
    completed = subprocess.run(command, cwd=ROOT, env=os.environ.copy(), check=False)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
