# Evidence Handling

## Directory purposes

- `tests/` — repeatable test and evidence-generation scripts
- `logs/` — sanitized outputs organized by test/run ID
- `screenshots/` — cropped, reviewed screenshots with no secrets
- `results/` — summarized findings derived from retained evidence

## Minimum evidence record

A retained test should identify:

- test ID
- UTC timestamp
- pinned component versions
- account or role used, without credentials
- sanitized input or request shape
- observed result
- pass/fail criterion
- artifact paths
- safe conclusion

## Sanitization rules

Never retain:

- passwords or API keys
- authorization headers
- cookies or session identifiers
- database exports
- private file paths when unnecessary
- real client, agency, resident, or operational data

## Claim progression

- local evidence alone may support `observed`
- official documentation alone does not prove local behavior
- `verified` requires both, plus pinned versions and a repeatable test

Review every artifact before staging it in Git. Sanitized evidence is intentionally not ignored as
a whole; unsafe evidence must be removed or kept outside the repository.
