#!/usr/bin/env bash
set -Eeuo pipefail

mode="${1:-}"
repo="${2:-}"
shift $(( $# >= 2 ? 2 : $# ))
[[ -d "$repo/.git" ]] || { echo '[FAIL] repository required' >&2; exit 1; }
repo="$(cd "$repo" && pwd -P)"
py="$repo/crewai/.venv/bin/python"
rehearsal="$repo/scripts/gate2c_step02_rehearsal.py"
reset_rehearsal="$repo/scripts/gate2c_step02_reset_rehearsal.py"
certify="$repo/scripts/gate2c_step02_certify.py"
audit="$repo/scripts/gate2c_step02_audit.py"
corrected_preflight="$repo/scripts/gate2c_step02_corrected_environment_preflight.py"

safe_python() {
  env -u OPENAI_API_KEY -u OPENAI_CANDIDATE_MODEL -u CREWAI_CANDIDATE_MODEL \
    PYTHONDONTWRITEBYTECODE=1 "$py" "$@"
}

case "$mode" in
  audit)
    safe_python "$audit" --repo "$repo" --mode installed "$@"
    ;;
  authorize-offline-rehearsal)
    [[ "${GATE2C_STEP02_ONE_RUN_ADMISSION_AUTHORIZED:-}" == "one-offline-rehearsal-identity-admission" ]] || {
      echo '[FAIL] explicit one-run identity admission authorization token required' >&2; exit 1;
    }
    safe_python "$rehearsal" authorize-offline --repo "$repo" "$@"
    ;;
  authorize-offline-rehearsal-replacement)
    [[ "${GATE2C_STEP02_REPLACEMENT_ADMISSION_AUTHORIZED:-}" == "one-fresh-offline-rehearsal-replacement-identity" ]] || {
      echo '[FAIL] separate explicit one-run replacement authorization token required' >&2; exit 1;
    }
    safe_python "$audit" --repo "$repo" --mode installed
    safe_python "$rehearsal" authorize-offline-replacement --repo "$repo" "$@"
    ;;
  authorize-corrected-environment-offline-rehearsal)
    [[ "${GATE2C_STEP02_CORRECTED_ENVIRONMENT_ADMISSION_AUTHORIZED:-}" == "one-corrected-environment-offline-rehearsal-identity" ]] || {
      echo '[FAIL] separate corrected-environment identity authorization token required' >&2; exit 1;
    }
    [[ "${GATE2C_CODEX_SANDBOX_MODE:-}" == "danger-full-access" ]] || {
      echo '[FAIL] explicit Codex danger-full-access session declaration required' >&2; exit 1;
    }
    safe_python "$audit" --repo "$repo" --mode installed
    preflight_dir="$(mktemp -d)"
    trap 'rm -rf -- "$preflight_dir"' EXIT
    safe_python "$corrected_preflight" --result "$preflight_dir/result.json"
    safe_python "$rehearsal" authorize-offline-corrected-environment --repo "$repo" --preflight-result "$preflight_dir/result.json" "$@"
    rm -rf -- "$preflight_dir"
    trap - EXIT
    ;;
  offline-rehearsal)
    [[ "${GATE2C_STEP02_OFFLINE_REHEARSAL_AUTHORIZED:-}" == "one-disposable-offline-hard-termination-rehearsal" ]] || {
      echo '[FAIL] explicit offline hard-termination rehearsal authorization token required' >&2; exit 1;
    }
    [[ "${GATE2C_CODEX_SANDBOX_MODE:-}" == "danger-full-access" ]] || {
      echo '[FAIL] explicit Codex danger-full-access session declaration required' >&2; exit 1;
    }
    preflight_dir="$(mktemp -d)"
    trap 'rm -rf -- "$preflight_dir"' EXIT
    safe_python "$corrected_preflight" --result "$preflight_dir/result.json"
    safe_python "$rehearsal" offline --repo "$repo" --preflight-result "$preflight_dir/result.json" "$@"
    rm -rf -- "$preflight_dir"
    trap - EXIT
    ;;
  record-post-inspection)
    [[ "${GATE2C_STEP02_POST_INSPECTION_AUTHORIZED:-}" == "classify-post-inspection-artifacts-separately" ]] || {
      echo '[FAIL] separate post-inspection classification authorization token required' >&2; exit 1;
    }
    safe_python "$rehearsal" record-post-inspection --repo "$repo" "$@"
    ;;
  crewai-startup-diagnostic)
    [[ "${GATE2C_STEP02_CREWAI_STARTUP_DIAGNOSTIC_AUTHORIZED:-}" == "one-disposable-crewai-startup-diagnostic-no-sigkill" ]] || {
      echo '[FAIL] separate CrewAI startup diagnostic authorization token required' >&2; exit 1;
    }
    safe_python "$rehearsal" crewai-startup-diagnostic --repo "$repo" "$@"
    ;;
  lancedb-async-diagnostic)
    [[ "${GATE2C_STEP02_LANCEDB_ASYNC_DIAGNOSTIC_AUTHORIZED:-}" == "one-disposable-public-lancedb-async-connect-diagnostic" ]] || {
      echo '[FAIL] separate public LanceDB async-connection diagnostic authorization token required' >&2; exit 1;
    }
    safe_python "$rehearsal" lancedb-async-diagnostic --repo "$repo" "$@"
    ;;
  lancedb-memory-async-diagnostic)
    [[ "${GATE2C_STEP02_LANCEDB_MEMORY_ASYNC_DIAGNOSTIC_AUTHORIZED:-}" == "one-disposable-public-lancedb-memory-async-connect-diagnostic" ]] || {
      echo '[FAIL] separate public LanceDB in-memory async-connection diagnostic authorization token required' >&2; exit 1;
    }
    safe_python "$rehearsal" lancedb-memory-async-diagnostic --repo "$repo" "$@"
    ;;
  authorize-drupal-replacement)
    [[ "${GATE2C_STEP02_DRUPAL_REPLACEMENT_ADMISSION_AUTHORIZED:-}" == "one-fresh-drupal-replacement-identity-admission" ]] || {
      echo '[FAIL] separate Drupal replacement identity-admission authorization token required' >&2; exit 1;
    }
    safe_python "$audit" --repo "$repo" --mode installed
    safe_python "$rehearsal" authorize-drupal-replacement --repo "$repo" "$@"
    ;;
  authorize-drupal-further-replacement)
    [[ "${GATE2C_STEP02_DRUPAL_FURTHER_REPLACEMENT_ADMISSION_AUTHORIZED:-}" == "one-fresh-drupal-further-replacement-identity-admission" ]] || {
      echo '[FAIL] separate further Drupal replacement identity-admission authorization token required' >&2; exit 1;
    }
    safe_python "$audit" --repo "$repo" --mode installed
    safe_python "$rehearsal" authorize-drupal-further-replacement --repo "$repo" "$@"
    ;;
  drupal-start)
    [[ "${GATE2C_STEP02_DRUPAL_REPLACEMENT_START_AUTHORIZED:-}" == "one-admitted-repaired-drupal-worker-and-sigkill" ]] || {
      echo '[FAIL] separate admitted replacement Drupal start/SIGKILL authorization token required' >&2; exit 1;
    }
    safe_python "$rehearsal" drupal-start --repo "$repo" "$@"
    ;;
  drupal-further-start)
    [[ "${GATE2C_STEP02_DRUPAL_FURTHER_REPLACEMENT_START_AUTHORIZED:-}" == "one-admitted-process-identity-repaired-drupal-worker-and-sigkill" ]] || {
      echo '[FAIL] separate admitted further replacement Drupal start/SIGKILL authorization token required' >&2; exit 1;
    }
    safe_python "$rehearsal" drupal-further-start --repo "$repo" "$@"
    ;;
  drupal-immediate)
    [[ "${GATE2C_STEP02_DRUPAL_IMMEDIATE_AUTHORIZED:-}" == "one-immediate-dedicated-lock-observation" ]] || {
      echo '[FAIL] separate immediate lock-observation authorization token required' >&2; exit 1;
    }
    safe_python "$rehearsal" drupal-immediate --repo "$repo" "$@"
    ;;
  drupal-post-expiry)
    [[ "${GATE2C_STEP02_DRUPAL_POST_EXPIRY_AUTHORIZED:-}" == "one-post-natural-expiry-dedicated-invocation" ]] || {
      echo '[FAIL] separate post-natural-expiry authorization token required' >&2; exit 1;
    }
    safe_python "$rehearsal" drupal-post-expiry --repo "$repo" "$@"
    ;;
  drupal-post-expiry-partial)
    [[ "${GATE2C_STEP02_DRUPAL_POST_EXPIRY_PARTIAL_AUTHORIZED:-}" == "one-existing-final-identity-post-expiry-partial-observation" ]] || {
      echo '[FAIL] separate non-certifying post-expiry partial-observation authorization token required' >&2; exit 1;
    }
    safe_python "$audit" --repo "$repo" --mode installed
    safe_python "$rehearsal" drupal-post-expiry-partial --repo "$repo" "$@"
    ;;
  drupal-finalize)
    [[ "${GATE2C_STEP02_DRUPAL_FINALIZE_AUTHORIZED:-}" == "seal-complete-drupal-lifecycle-evidence-only" ]] || {
      echo '[FAIL] separate non-Drupal evidence-finalization authorization token required' >&2; exit 1;
    }
    safe_python "$rehearsal" drupal-finalize --repo "$repo" "$@"
    ;;
  reset-rehearsal)
    [[ "${GATE2C_STEP02_RESET_REHEARSAL_AUTHORIZED:-}" == "one-disposable-anchor-reset-exact-restore-rehearsal" ]] || {
      echo '[FAIL] separate snapshot/reset/restoration rehearsal authorization token required' >&2; exit 1;
    }
    safe_python "$reset_rehearsal" --repo "$repo" "$@"
    ;;
  record-crewai-decision)
    [[ "${GATE2C_STEP02_CREWAI_DECISION_AUTHORIZED:-}" == "explicit-human-approve-or-reject-after-evidence" ]] || {
      echo '[FAIL] explicit human CrewAI architecture decision authorization token required' >&2; exit 1;
    }
    safe_python "$certify" decision --repo "$repo" "$@"
    ;;
  certify)
    [[ "${GATE2C_STEP02_CERTIFICATION_AUTHORIZED:-}" == "accept-model-free-step02-evidence-once" ]] || {
      echo '[FAIL] explicit Step 2C.02 certification authorization token required' >&2; exit 1;
    }
    result="$(safe_python "$certify" certify --repo "$repo" "$@")"
    safe_python "$audit" --repo "$repo" --mode installed --evidence "$repo/$result"
    printf '%s\n' "$result"
    ;;
  *)
    echo "usage: $0 {audit|authorize-offline-rehearsal|authorize-offline-rehearsal-replacement|authorize-corrected-environment-offline-rehearsal|offline-rehearsal|record-post-inspection|crewai-startup-diagnostic|lancedb-async-diagnostic|lancedb-memory-async-diagnostic|authorize-drupal-replacement|authorize-drupal-further-replacement|drupal-start|drupal-further-start|drupal-immediate|drupal-post-expiry|drupal-post-expiry-partial|drupal-finalize|reset-rehearsal|record-crewai-decision|certify} REPO [arguments]" >&2
    exit 1
    ;;
esac
