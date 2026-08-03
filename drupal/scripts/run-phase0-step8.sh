#!/usr/bin/env bash
set -Eeuo pipefail

STEP8_RUNNER_VERSION="3.1.0"
MODE="${1:-apply}"
CONFIRMATION="${2:-}"

case "$MODE" in
  apply|audit|migrate-test-source)
    if [[ -n "$CONFIRMATION" ]]; then
      echo "Usage: $0 [apply|audit|migrate-test-source] or $0 remove confirm" >&2
      exit 2
    fi
    ;;
  remove)
    if [[ "$CONFIRMATION" != "confirm" ]]; then
      echo "Removal is destructive. Use: $0 remove confirm" >&2
      exit 2
    fi
    ;;
  *)
    echo "Usage: $0 [apply|audit|migrate-test-source] or $0 remove confirm" >&2
    exit 2
    ;;
esac

ARGS=("$MODE")
if [[ "$MODE" == "remove" ]]; then
  ARGS+=("confirm")
fi

echo "[INFO] Phase 0 Step 8 runner version: $STEP8_RUNNER_VERSION"
echo "Running Phase 0 Step 8 in '$MODE' mode..."
if [[ "$MODE" == "apply" || "$MODE" == "migrate-test-source" ]]; then
  echo "Ensuring required core modules are enabled..."
  ddev drush en -y image text
fi
ddev drush php:script scripts/phase0-step8.php -- "${ARGS[@]}"

echo "Rebuilding Drupal caches and routes..."
ddev drush cache:rebuild

echo
case "$MODE" in
  apply)
    echo "Step 8 structure is installed. Complete the permission handoff with:"
    echo "  ./scripts/run-phase0-step7.sh finalize"
    echo
    echo "Then verify both steps:"
    echo "  ./scripts/run-phase0-step8.sh audit"
    echo "  ./scripts/run-phase0-step7.sh audit"
    echo
    echo "Review queue: https://harness.ddev.site/admin/review-queue"
    ;;
  audit)
    echo "Step 8 audit complete."
    ;;
  migrate-test-source)
    echo "Step 8 source-origin migration complete. Export configuration with: ddev drush cex -y"
    ;;
  remove)
    echo "Step 8 configuration removed. Step 7 roles and accounts were left intact."
    ;;
esac
