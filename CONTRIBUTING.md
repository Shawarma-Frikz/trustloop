# Contributing

This is a solo project; the rules exist to keep the history and the evidence
consistent, not to satisfy a review committee.

## Branches

`main` is always green. Never commit to it directly.

| Prefix | Use |
|---|---|
| `feat/` | One coherent capability |
| `fix/` | A defect with a regression test |
| `contract/` | Any change under `contracts/` |
| `model/` | Training, evaluation, or artifact changes |
| `docs/` | Documentation and evidence |
| `chore/` | Tooling, dependencies, CI |

One branch, one purpose, under three days of life.

## Commits

Conventional Commits with a scope:

```text
feat(api): add analyze endpoint with batch validation
fix(extension): keep dedup keys stable across rescans
test(scoring): cover version mismatch on score response
docs: record Phase 0 spike result and fallback
ci: add contract fixture workflow
```

Scopes: `api`, `scoring`, `extension`, `contract`, `model`, `docs`, `ci`.

## Pull requests

Every change goes through a PR into `main`, even solo. The PR is where CI runs
and where the reason for the change is written. Squash merge only; delete the
branch afterwards.

## Tests

Tests belong to the change that introduces the behaviour. A pull request is not
done with failing or missing tests.

## Never commit

- Real secrets, tokens, or `.env` files.
- Datasets, reviewer-level data, or live review text.
- Model binaries over roughly 5 MB.
- Logs containing review text, URLs, or review keys.