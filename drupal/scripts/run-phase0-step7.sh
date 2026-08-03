#!/usr/bin/env bash
set -Eeuo pipefail

MODE="${1:-bootstrap}"
RESET_ARG="${2:-}"

case "$MODE" in
  bootstrap|finalize|audit)
    ;;
  *)
    echo "Usage: $0 [bootstrap|finalize|audit] [reset-passwords]" >&2
    exit 2
    ;;
esac

if [[ -n "$RESET_ARG" && "$RESET_ARG" != "reset-passwords" ]]; then
  echo "Second argument, when present, must be: reset-passwords" >&2
  exit 2
fi

ARGS=("$MODE")
if [[ "$RESET_ARG" == "reset-passwords" ]]; then
  ARGS+=("reset-passwords")
fi

echo "Running Phase 0 Step 7 in '$MODE' mode..."
ddev drush php:script scripts/phase0-step7.php -- "${ARGS[@]}"
ddev drush cache:rebuild

echo
case "$MODE" in
  bootstrap)
    echo "Bootstrap complete. Create alt_text_suggestion in Step 8, then run:"
    echo "  ./scripts/run-phase0-step7.sh finalize"
    ;;
  finalize)
    echo "Finalization complete. Run the permission/API tests next."
    ;;
  audit)
    echo "Audit complete."
    ;;
esac
