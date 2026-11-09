# YojanaSuno evaluation report

These scores are exact-match results on a small fixture set. They are **not field accuracy**; most fixtures are synthetic and have not been reviewed by a native speaker.

Selected extractor: `both`. Evon: unreachable/not configured; used mock fallback.

| Language | Human-reviewed cases | Synthetic/unreviewed cases | Mock slot accuracy | Evon slot accuracy |
|---|---:|---:|---:|---:|
| hi | 0 | 30 | 27/30 (90.0%) | 27/30 (90.0%) |
| ta | 0 | 30 | 27/30 (90.0%) | 27/30 (90.0%) |
| te | 0 | 30 | 27/30 (90.0%) | 27/30 (90.0%) |
| en | 0 | 30 | 28/30 (93.3%) | 28/30 (93.3%) |

Eligibility engine: 9/9 (100.0%) on deterministic fixture cases.

## Language-scenario fixture checks

Offline behavioral pass rates on curated YAML scenarios. These are fixture checks, not field accuracy.

| Language | Passed / total | Fixture pass rate | Human-reviewed | Synthetic / unreviewed |
|---|---:|---:|---:|---:|
| hi | 12/12 | 100.0% | 0 | 12 |
| ta | 12/12 | 100.0% | 0 | 12 |
| te | 12/12 | 100.0% | 0 | 12 |
| en | 12/12 | 100.0% | 0 | 12 |

## Side-by-side disagreements

| Case | Language | Fields | Mock values | Evon values |
|---|---|---|---|---|
| — | — | No disagreements in compared fields | — | — |
