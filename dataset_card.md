# DialysisFlow-AgentBench Synthetic Scenario Dataset

## Summary
A small fictional dataset for testing operational scheduling/recovery algorithms under synthetic dialysis-service disruptions.

## Intended use
Research and education on operational resource allocation, reproducibility, constraint checking, and fairness-proxy evaluation.

## Not intended for
Clinical triage, treatment decisions, patient-level prediction, staffing decisions in a real clinic, or claims about real dialysis services.

## Data fields
- `scenario_id`: synthetic scenario identifier
- `sessions_requested`: number of fictional sessions needing allocation
- `available_slots`: synthetic slot capacity
- `staff_capacity`: synthetic staff-supported capacity
- `machine_capacity`: synthetic machine-supported capacity
- `disruption_severity`: synthetic severity index (0–4), not a clinical severity score
- `priority_class`: illustrative synthetic category (`standard` or `higher`), not a medical triage label

## Provenance
All rows are generated for this benchmark. No personal, patient, hospital, or identifiable data are included.

## Limitations
Only 20 hand-authored scenarios are included in v0.1.0. They are not statistically representative of any population or service.
