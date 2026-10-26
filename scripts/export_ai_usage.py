"""Export ONLY token counters from a Codex session, never prompts or tool contents.

Usage: python scripts/export_ai_usage.py /path/to/rollout.jsonl
The source file is private and is not copied into the repository.
"""

import argparse
import json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("session", type=Path)
args = parser.parse_args()
events = []
for line in args.session.read_text(encoding="utf-8").splitlines():
    try:
        entry = json.loads(line)
    except json.JSONDecodeError:
        continue
    payload = entry.get("payload", {})
    if entry.get("type") == "event_msg" and payload.get("type") == "token_count" and payload.get("info"):
        info = payload["info"]
        events.append(
            {
                "timestamp": entry["timestamp"],
                "total_token_usage": info.get("total_token_usage"),
                "last_token_usage": info.get("last_token_usage"),
            }
        )
output = Path(__file__).resolve().parents[1] / "docs" / "ai-usage" / "token-usage.json"
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(
    json.dumps(
        {
            "source": "Codex local rollout event_msg.token_count counters",
            "scope": "This conversation, including planning and implementation; cumulative counters include cached input.",
            "caveat": "Snapshot only; later messages and image-generation usage may not be included. These are token counters, not cost estimates.",
            "events": events,
        },
        indent=2,
    )
    + "\n",
    encoding="utf-8",
)
if events:
    latest = events[-1]
    counts = latest["total_token_usage"]
    summary = "# Captured Codex token usage\n\n"
    summary += f"Snapshot timestamp (UTC): {latest['timestamp']}\n\n"
    summary += "| Counter | Tokens |\n| --- | ---: |\n"
    for key, value in counts.items():
        summary += f"| {key} | {value:,} |\n"
    summary += (
        "\nCumulative conversation counters, including planning. Cached input is a subset of input; "
        "reasoning output is reported separately by the tool and must not be added again to total. "
        "Repeated context can make cumulative input large. Not a cost estimate. "
        "Image Gen usage and messages after this snapshot are not included. "
        "See token-usage.json for timestamped evidence.\n"
    )
    output.with_name("SUMMARY.md").write_text(summary, encoding="utf-8")
print(json.dumps({"snapshot": events[-1] if events else None, "events_exported": len(events)}))
