#!/usr/bin/env bash
# Brain rule guard: fail if any LLM/ML SDK appears in the dependency manifests or lockfile.
set -euo pipefail

cd "$(dirname "$0")/.."

PATTERN='openai|anthropic|google-generativeai|google-genai|langchain|transformers|llama|mistralai|cohere|ollama'
FILES=(backend/pyproject.toml backend/uv.lock frontend/package.json)

status=0
for file in "${FILES[@]}"; do
  if [[ ! -f "$file" ]]; then
    echo "check_no_llm_deps: required file missing: $file" >&2
    exit 2
  fi
  if grep -inE "$PATTERN" "$file"; then
    echo "check_no_llm_deps: forbidden LLM dependency found in $file" >&2
    status=1
  fi
done

if [[ $status -eq 0 ]]; then
  echo "check_no_llm_deps: OK (no LLM/ML SDK dependencies)"
fi
exit $status
