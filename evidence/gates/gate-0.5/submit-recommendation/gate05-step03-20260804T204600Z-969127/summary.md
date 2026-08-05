# Gate 0.5 Step 03 Submit Recommendation Summary

- **Status:** PASS
- **Run ID:** `gate05-step03-20260804T204600Z-969127`
- **Operation:** `submit_recommendation(recommendation)`
- **Canonical target:** sequence 1
- **Transient recommendation node:** `21`
- **Transient recommendation UUID:** `44f34994-9553-4128-9e3c-b68dcaeb2414`
- **Review status:** `pending`
- **Idempotent replay:** same node and revision
- **Transient queue count:** 1
- **Final queue count after reset:** 0
- **Source Article changed:** no
- **Model call performed:** no
- **Framework execution claimed:** no
- **Controlled preflight:** yes

The preflight exercises the frozen `drupal_ai` provenance enum branch because
`recommendation.schema.json` intentionally excludes test-only origins. It is not evidence that the
Drupal AI harness generated this recommendation.

## Negative controls

- anonymous denied
- `editor_dana` denied
- malformed recommendation rejected
- stale revision and changed file rejected
- source/run mismatch rejected
- unsupported source rejected
- empty, overlong, preamble, generic, filename-echo, and duplicate-current-alt text rejected
- same idempotency identity with different payload rejected

## Next step

Gate 0.5 Step 04 adds `get_recommendation_status()` and proves one explicit human review decision.
