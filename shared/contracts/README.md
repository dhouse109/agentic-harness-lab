# Gate 0.5 Substrate Contracts

`GATE05-SUBSTRATE-FREEZE.json` is generated only by a passing Step 05 certification run.

`GATE05-SUBSTRATE-FREEZE.sha256` contains the SHA-256 of the exact JSON manifest bytes.

The manifest freezes the shared Drupal tool surface and fairness boundary. It intentionally marks
all three framework vertical slices as not yet certified.

To verify it:

```bash
bash scripts/run-gate05-step05.sh audit
```

Do not hand-edit the generated manifest. Material changes require an ADR and a new certification
run.
