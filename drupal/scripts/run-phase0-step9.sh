#!/usr/bin/env bash
set -Eeuo pipefail

MODE="${1:-apply}"
CONFIRMATION="${2:-}"

case "$MODE" in
  apply|audit|manifest)
    if [[ -n "$CONFIRMATION" ]]; then
      echo "Usage: $0 [apply|audit|manifest] or $0 remove confirm" >&2
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
    echo "Usage: $0 [apply|audit|manifest] or $0 remove confirm" >&2
    exit 2
    ;;
esac

ARGS=("$MODE")
if [[ "$MODE" == "remove" ]]; then
  ARGS+=("confirm")
fi

if [[ "$MODE" == "manifest" ]]; then
  ddev drush --quiet php:script scripts/seed.php -- manifest
  exit 0
fi

echo "Running Phase 0 Step 9 in '$MODE' mode..."

if ! ddev exec php -r 'exit(extension_loaded("gd") ? 0 : 1);'; then
  echo "ERROR: PHP GD is not enabled inside the DDEV web container." >&2
  echo "Inspect the container with: ddev exec php -m | grep -i '^gd$'" >&2
  exit 1
fi

if ! ddev exec php -r 'exit(extension_loaded("mbstring") ? 0 : 1);'; then
  echo "ERROR: PHP mbstring is not enabled inside the DDEV web container." >&2
  exit 1
fi

ddev drush php:script scripts/seed.php -- "${ARGS[@]}"

case "$MODE" in
  apply|remove)
    echo "Rebuilding Drupal caches..."
    ddev drush cache:rebuild
    ;;
esac

echo
case "$MODE" in
  apply)
    echo "Step 9 seed is installed and audited. Useful next checks:"
    echo "  bash scripts/run-phase0-step9.sh audit"
    echo "  ddev drush php:script scripts/seed.php -- manifest"
    echo
    echo "Then inspect several Articles in Drupal before creating Step 10's seeded-clean snapshot."
    ;;
  audit)
    echo "Step 9 audit complete."
    ;;
  remove)
    echo "Step 9 seed content removed. Step 7/8 structure was left intact."
    ;;
esac
