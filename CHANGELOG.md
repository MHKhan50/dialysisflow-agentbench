# Changelog

## Unreleased

- Hugging Face dataset: `scripts/export_hf.py` writes the 1,200 scenarios and the per-policy results with a dataset card (`hf/README.md`); `scripts/upload_hf.py` uploads them. Both tables are Parquet with one fixed schema (travel times are a list in unit order), so the Hugging Face viewer and `load_dataset` read them directly. Results are unchanged.

## 0.2.1 (2026-11-18)

- Two stronger decentralised baselines: fixed transport quotas per unit, and repeated rounds of separate offers without a shared record of transport.
- Sensitivity sweep over the share of patients needing transport and fleet size (`results/sensitivity_summary.csv`).
- The MILP now stops with an error unless every stage is solved to proven optimality.
- Package versions pinned in `requirements.txt`.
- Paper: related work on dialysis in disasters and equitable re-placement, clearer wording on overbooking, the cohort gap and burden comparisons.
- Results for the seven original policies are unchanged.

## 0.2.0 (2026-11-18)

Redesigned as a new experiment.

- v0.1.0 added random errors at fixed rates to the baseline policies and set the coordinated policy's violations to zero, so its ranking was decided by construction. Its `mean_fairness_gap` field was a mean delay burden, not a gap between groups. That code and its 20 hand-written scenarios are removed.
- New seeded generator: 1,200 networks over three chair-scarcity levels and two closure severities.
- Seven policies with no added errors, including two exact MILP optima.
- Two operational cohorts (needs transport or travels independently) and a true unmet-rate gap between them.
- Paired bootstrap intervals over scenarios, tests and charts.

## 0.1.0 (2026-11-15)

First prototype. Superseded by 0.2.0.
