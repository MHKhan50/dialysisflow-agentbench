# Changelog

## 0.2.0 (2026-11-18)

Redesigned as a new experiment.

- v0.1.0 added random errors at fixed rates to the baseline policies and set the coordinated policy's violations to zero, so its ranking was decided by construction. Its `mean_fairness_gap` field was a mean delay burden, not a gap between groups. That code and its 20 hand-written scenarios are removed.
- New seeded generator: 1,200 networks over three chair-scarcity levels and two closure severities.
- Seven policies with no added errors, including two exact MILP optima.
- Two operational cohorts (needs transport or travels independently) and a true unmet-rate gap between them.
- Paired bootstrap intervals over scenarios, tests and charts.

## 0.1.0 (2026-11-15)

First prototype. Superseded by 0.2.0.
