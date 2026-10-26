"""Export only allowlisted token/model metadata from a Codex session; never conversation text."""

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("session", type=Path)
parser.add_argument("--output", type=Path, default=Path("evidence/ai-usage.json"))
args = parser.parse_args()
snapshots = []
models = set()
fields = (
    "input_tokens",
    "cached_input_tokens",
    "cache_write_input_tokens",
    "output_tokens",
    "reasoning_output_tokens",
    "total_tokens",
)
for line in args.session.open():
    try:
        record = json.loads(line)
    except ValueError:
        continue
    payload = record.get("payload", {})
    if record.get("type") == "turn_context" and payload.get("model"):
        models.add((payload["model"], payload.get("effort")))
    if record.get("type") == "event_msg" and payload.get("type") == "token_count":
        usage = (payload.get("info") or {}).get("total_token_usage")
        if usage:
            snapshots.append(
                {
                    "timestamp": record.get("timestamp"),
                    "cumulative": {key: usage[key] for key in fields if key in usage},
                }
            )
if not snapshots:
    raise SystemExit("No token counters found; no evidence was fabricated.")
result = {
    "captured_at_utc": datetime.now(UTC).isoformat(),
    "source": "Codex local session event_msg/token_count; sanitized metadata only",
    "scope": "This primary session, including assessment planning and implementation up to snapshot",
    "models": [
        {"model": model, "reasoning_effort": effort} for model, effort in sorted(models)
    ],
    "latest": snapshots[-1],
    "counter_samples_observed": len(snapshots),
    "accounting_note": "Cumulative snapshot, not the sum of snapshots. Cached input is a subset of "
    "input. Reasoning output is a subset of output. Not a price or quota estimate.",
}
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
