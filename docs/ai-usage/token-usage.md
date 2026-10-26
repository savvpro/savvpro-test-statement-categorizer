# Token usage log

Source: Claude Code's local session transcripts
(`~/.claude/projects/<project>/<session>.jsonl` and `.../subagents/*.jsonl`). Every API
response stores a `usage` block; the numbers below are the sum over unique responses
(deduplicated by message id). Counted on 2026-10-26 at about 1:35 PM PKT, after the PR was
opened. The few follow-up messages after that are not included.

Model: `claude-opus-5-5` (Claude Opus 5.5) for both sessions.

| Session | API calls | Input (uncached) | Output | Cache write | Cache read | Total |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Main session: plan, backend, tests, Docker, CI, docs, git/PR help | 84 | 170 | 94,134 | 178,828 | 12,138,109 | 12,411,241 |
| Frontend subagent: Next.js UI, taste → Impeccable workflow | 43 | 86 | 52,465 | 116,944 | 3,404,771 | 3,574,266 |
| **Total** | **127** | **256** | **146,599** | **295,772** | **15,542,880** | **15,985,507** |

## How to read this

- **Cache read** is most of the total. On every turn the agent re-sends the conversation
  so far (the plan, `CLAUDE.md`, files it has read), and those tokens are served from the
  prompt cache. They are much cheaper than fresh input.
- **Output** (~147K tokens) is what the model actually wrote: code, tests, docs and replies.
- **Cache write** (~296K tokens) is new context that was added to the cache.

## How to reproduce

```bash
python3 - <<'EOF'
import json, glob, os
base = os.path.expanduser("~/.claude/projects/-home-rahat-Desktop-savvpro-test-statement-categorizer")
for f in glob.glob(base + "/*.jsonl") + glob.glob(base + "/*/subagents/*.jsonl"):
    seen, tot = set(), {}
    for line in open(f):
        m = json.loads(line).get("message") or {}
        u = m.get("usage") if isinstance(m, dict) else None
        if not u or m.get("id") in seen:
            continue
        seen.add(m.get("id"))
        for k in ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"):
            tot[k] = tot.get(k, 0) + (u.get(k) or 0)
    print(os.path.basename(f), len(seen), tot)
EOF
```
