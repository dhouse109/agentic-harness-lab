#!/usr/bin/env bash
set -Eeuo pipefail
repo="${2:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)}"; mode="${1:-audit}"
case "$mode" in
 audit) exec env -u OPENAI_API_KEY -u OPENAI_CANDIDATE_MODEL -u CREWAI_CANDIDATE_MODEL PYTHONDONTWRITEBYTECODE=1 python3 "$repo/scripts/gate2b_step08_audit.py" --repo "$repo" --mode permanent ;;
 certify) [[ "${GATE2B_STEP08_CERTIFICATION_AUTHORIZED:-}" == "certify-frozen-crewai-composite-once" ]] || { echo '[FAIL] certification authorization missing' >&2; exit 1; }; rid="${3:?certification run id required}"; env -u OPENAI_API_KEY -u OPENAI_CANDIDATE_MODEL -u CREWAI_CANDIDATE_MODEL PYTHONDONTWRITEBYTECODE=1 python3 "$repo/scripts/gate2b_step08_audit.py" --repo "$repo" --mode predecessor; env -u OPENAI_API_KEY -u OPENAI_CANDIDATE_MODEL -u CREWAI_CANDIDATE_MODEL PYTHONDONTWRITEBYTECODE=1 python3 "$repo/scripts/gate2b_step08_certify.py" --repo "$repo" --run-id "$rid"; exec env -u OPENAI_API_KEY -u OPENAI_CANDIDATE_MODEL -u CREWAI_CANDIDATE_MODEL PYTHONDONTWRITEBYTECODE=1 python3 "$repo/scripts/gate2b_step08_audit.py" --repo "$repo" --mode permanent ;;
 *) echo "usage: $0 {audit|certify} [repo] [run-id]" >&2; exit 2;;
esac
