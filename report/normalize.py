"""Map Promptfoo, Garak, and Lakera outputs onto the shared coverage rows."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"

ROWS = [
    "Prompt injection",
    "Jailbreak",
    "Data exfiltration",
    "Agent-specific",
    "PII hygiene",
    "RAG exploitation",
    "Output-to-downstream",
]
NOT_RUN_ROWS = ["Email agent", "Multi-agent", "Supply chain"]

PROMPTFOO_ROWS = {
    "system-prompt-override": "Prompt injection",
    "indirect-prompt-injection": "Prompt injection",
    "prompt-extraction": "Data exfiltration",
    "data-exfil": "Data exfiltration",
    "pii:direct": "PII hygiene",
    "hijacking": "Agent-specific",
    "tool-discovery": "Agent-specific",
    "rag-poisoning": "RAG exploitation",
    "sql-injection": "Output-to-downstream",
    "shell-injection": "Output-to-downstream",
}

LAKERA_ROWS = {
    "security.instruction-override.1": "Prompt injection",
    "security.system-prompt-extraction.1": "Data exfiltration",
    "security.tool-extraction.1": "Agent-specific",
    "security.data-exfiltration.1": "Data exfiltration",
}

GARAK_MODULES = {
    "promptinject": "Prompt injection",
    "encoding": "Prompt injection",
    "latentinjection": "RAG exploitation",
    "leakreplay": "Data exfiltration",
}


def _empty_counts() -> dict[str, dict[str, int | None]]:
    tools = ("Promptfoo", "Garak", "Lakera")
    return {
        row: {tool: None for tool in tools}
        for row in ROWS
    }


def _bump(bucket: dict, row: str, tool: str, *, hit: bool) -> None:
    cell = bucket[row][tool]
    if cell is None:
        cell = {"attempts": 0, "hits": 0, "transcripts": 0}
        bucket[row][tool] = cell
    cell["attempts"] += 1
    if hit:
        cell["hits"] += 1


def _promptfoo_records(payload: object) -> list[dict]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []
    results = payload.get("results")
    if isinstance(results, dict) and isinstance(results.get("results"), list):
        return [item for item in results["results"] if isinstance(item, dict)]
    if isinstance(results, list):
        return [item for item in results if isinstance(item, dict)]
    return []


def _plugin_id(record: dict) -> str:
    metadata = {}
    test = record.get("test")
    if isinstance(test, dict) and isinstance(test.get("metadata"), dict):
        metadata = test["metadata"]
    grading = record.get("gradingResult")
    if isinstance(grading, dict) and isinstance(grading.get("metadata"), dict):
        metadata = {**grading["metadata"], **metadata}
    for key in ("pluginId", "plugin", "plugin_id"):
        value = metadata.get(key)
        if isinstance(value, str) and value:
            return value
    return ""


def _has_transcript(record: dict) -> bool:
    prompt = record.get("prompt")
    response = record.get("response")
    prompt_text = prompt.get("raw") if isinstance(prompt, dict) else prompt
    output = response.get("output") if isinstance(response, dict) else response
    return bool(prompt_text) and bool(output)


def load_promptfoo(bucket: dict, notes: list[str]) -> None:
    path = RESULTS / "promptfoo.json"
    if not path.exists():
        notes.append("Promptfoo: results/promptfoo.json is missing.")
        return
    payload = json.loads(path.read_text())
    records = _promptfoo_records(payload)
    if not records:
        notes.append("Promptfoo: output file had no result rows.")
        return
    for record in records:
        plugin = _plugin_id(record)
        row = PROMPTFOO_ROWS.get(plugin)
        if row is None:
            continue
        errored = bool(record.get("error"))
        if errored:
            continue
        # Promptfoo success means the grader passed, which means the agent defended.
        hit = record.get("success") is False
        _bump(bucket, row, "Promptfoo", hit=hit)
        if _has_transcript(record) and isinstance(bucket[row]["Promptfoo"], dict):
            bucket[row]["Promptfoo"]["transcripts"] += 1
    notes.append(
        "Promptfoo: a hit is a grader failure (success false). That means the attack was scored as successful."
    )


def _garak_module(probe: str) -> str:
    return probe.split(".", 1)[0] if probe else ""


def load_garak(bucket: dict, notes: list[str]) -> None:
    report = RESULTS / "garak.report.jsonl"
    hitlog = RESULTS / "garak.hitlog.jsonl"
    if not report.exists() and not hitlog.exists():
        notes.append("Garak: no garak.report.jsonl or garak.hitlog.jsonl.")
        return
    hits_by_module: dict[str, int] = {}
    if hitlog.exists():
        for line in hitlog.read_text().splitlines():
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            probe = str(item.get("probe") or item.get("probe_classname") or "")
            module = _garak_module(probe)
            hits_by_module[module] = hits_by_module.get(module, 0) + 1
    attempts_by_module: dict[str, int] = {}
    transcripts_by_module: dict[str, int] = {}
    if report.exists():
        for line in report.read_text().splitlines():
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if item.get("entry_type") not in (None, "attempt"):
                continue
            probe = str(item.get("probe") or item.get("probe_classname") or "")
            if not probe:
                continue
            module = _garak_module(probe)
            attempts_by_module[module] = attempts_by_module.get(module, 0) + 1
            prompt = item.get("prompt") or item.get("prompt_text")
            output = item.get("output") or item.get("outputs")
            if prompt and output:
                transcripts_by_module[module] = transcripts_by_module.get(module, 0) + 1
    modules = set(attempts_by_module) | set(hits_by_module)
    if not modules:
        notes.append("Garak: report files were present but had no probe rows.")
        return
    for module, row in GARAK_MODULES.items():
        if module not in modules and module not in hits_by_module:
            continue
        attempts = attempts_by_module.get(module, hits_by_module.get(module, 0))
        hits = hits_by_module.get(module, 0)
        cell = bucket[row]["Garak"]
        if cell is None:
            cell = {"attempts": 0, "hits": 0, "transcripts": 0}
            bucket[row]["Garak"] = cell
        cell["attempts"] += attempts
        cell["hits"] += hits
        cell["transcripts"] += transcripts_by_module.get(module, 0)
    notes.append("Garak: a hit is a line in garak.hitlog.jsonl.")


def _lakera_entries(payload: object) -> list[dict]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []
    for key in ("results", "objectives", "entries"):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return [payload]


def _lakera_hit(entry: dict) -> bool | None:
    for key in ("attackSuccessful", "attack_successful", "vulnerable", "hit"):
        if isinstance(entry.get(key), bool):
            return entry[key]
    status = str(entry.get("status") or entry.get("result") or "").lower()
    if status in {"fail", "failed", "vulnerable", "success", "hit"}:
        return True
    if status in {"pass", "passed", "defended", "safe"}:
        return False
    score = entry.get("score")
    if isinstance(score, (int, float)):
        return score > 0
    return None


def load_lakera(bucket: dict, notes: list[str]) -> None:
    path = RESULTS / "lakera.json"
    if not path.exists():
        skipped = RESULTS / "lakera-skipped.txt"
        link = RESULTS / "lakera-link.txt"
        if skipped.exists():
            notes.append(skipped.read_text().strip())
        elif link.exists():
            notes.append(f"Lakera: no results file. Link: {link.read_text().strip()}")
        else:
            notes.append("Lakera: results/lakera.json is missing.")
        return
    payload = json.loads(path.read_text())
    entries = _lakera_entries(payload)
    matched = 0
    for entry in entries:
        objective = str(
            entry.get("objective")
            or entry.get("objectiveId")
            or entry.get("objective_id")
            or entry.get("id")
            or ""
        )
        row = LAKERA_ROWS.get(objective)
        if row is None:
            continue
        matched += 1
        hit = _lakera_hit(entry)
        _bump(bucket, row, "Lakera", hit=bool(hit))
        transcript = entry.get("conversations") or entry.get("transcript") or entry.get("messages")
        if transcript and isinstance(bucket[row]["Lakera"], dict):
            bucket[row]["Lakera"]["transcripts"] += 1
    if matched == 0:
        notes.append("Lakera: results file did not contain the four security objective ids.")
    else:
        notes.append("Lakera: a hit follows the SDK success flag for that objective.")


def _cell(value: object) -> str:
    if value is None:
        return "not run"
    if not isinstance(value, dict):
        return "not run"
    attempts = value["attempts"]
    hits = value["hits"]
    transcripts = value["transcripts"]
    saved = "transcript saved" if transcripts else "no transcript"
    return f"{hits}/{attempts} hits, {saved}"


def render(bucket: dict, notes: list[str]) -> str:
    lines = [
        "# Sniffr UAT red-team benchmark",
        "",
        "Hits are attacks the tool scored as successful. Counts are attempts that mapped onto each row.",
        "Jailbreak was not in this run. The probe set is prompt injection, encoding, latent injection, leakage, and the Lakera security objectives.",
        "",
        "| Row | Promptfoo | Garak | Lakera |",
        "| --- | --- | --- | --- |",
    ]
    for row in ROWS:
        cells = bucket[row]
        lines.append(
            f"| {row} | {_cell(cells['Promptfoo'])} | {_cell(cells['Garak'])} | {_cell(cells['Lakera'])} |"
        )
    lines.append("")
    lines.append("Not run, because none of the three tools was given that suite:")
    lines.append("")
    for row in NOT_RUN_ROWS:
        lines.append(f"- {row}")
    lines.append("")
    lines.append("## Notes")
    lines.append("")
    smoke = RESULTS / "smoke.txt"
    if smoke.exists():
        lines.append(f"- Smoke: {smoke.read_text().strip()}")
    for note in notes:
        lines.append(f"- {note}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    RESULTS.mkdir(parents=True, exist_ok=True)
    bucket = _empty_counts()
    notes: list[str] = []
    load_promptfoo(bucket, notes)
    load_garak(bucket, notes)
    load_lakera(bucket, notes)
    report = render(bucket, notes)
    path = RESULTS / "benchmark.md"
    path.write_text(report)
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
