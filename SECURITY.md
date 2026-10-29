# Security

TrustLoop handles review text, so a privacy failure is a security failure.

## Reporting

Report vulnerabilities privately through GitHub Security Advisories
(Security → Advisories → Report a vulnerability). Do not open a public issue.

Include what you observed, the affected component, and the smallest input that
reproduces it. Do not include live review text, reviewer identity, or URLs.

## Supported versions

Only the latest commit on `main` is supported during development. There are no
long-term support branches.

## Rules

- No secret is committed. Local configuration lives in `.env`; shared values
  live in GitHub environments.
- No review text, reviewer identity, host URL, or review key is logged.
- No dataset is redistributed. Only manifests, metrics, and model cards are
  committed.
- `TRUSTLOOP_SCORING_TOKEN` is generated from 32 random bytes and rotated
  immediately if exposed.
- A vulnerability fix lands through a private advisory branch, not a public PR.
