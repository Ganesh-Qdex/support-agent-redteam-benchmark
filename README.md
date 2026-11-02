# Sniffr UAT support-agent red-team benchmark

Runs a bounded security comparison of Promptfoo, Garak, and Lakera Red against the Sniffr UAT support agent.

The chat URL and body live only in `harness/client.py`. The attack text is the `query` field. Auth and identity fields are sent empty. `.env` is only for an optional Lakera key and is not committed.

This run covers security objectives: prompt injection, system-prompt extraction, data exfiltration, PII, tool discovery, RAG poisoning, and downstream SQL or shell injection. It does not include content-safety probes for weapons, biological or chemical synthesis, self-harm, or sexual content.

Garak is capped at 8 prompts per probe. The encoding probe uses a local canary string, not Garak's shipped payload set. The PromptInject classes whose canary is a violent phrase are left out.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Promptfoo's security plugins also need one hosted-generator login:

```bash
npx promptfoo@latest auth login
```

## Run

Smoke-check the agent before any probe:

```bash
python -m harness.smoke
```

Then, from the repo root with the virtualenv active:

```bash
python scripts/run_benchmark.py
```

Or run the tools separately:

```bash
npx promptfoo@latest redteam run -c promptfoo/promptfooconfig.yaml -o results/promptfoo.json
python garak/run.py
python lakera/run_scan.py
python report/normalize.py
```

The written report is `results/benchmark.md`. That directory stays local.
