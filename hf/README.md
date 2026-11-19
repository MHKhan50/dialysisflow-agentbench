---
license: mit
pretty_name: DialysisFlow-AgentBench
language:
- en
tags:
- synthetic
- operations-research
- scheduling
- multi-agent
- healthcare-operations
- benchmark
size_categories:
- 1K<n<10K
task_categories:
- other
configs:
- config_name: scenarios
  data_files: data/scenarios.jsonl
- config_name: policy_results
  data_files: data/policy_results.csv
---

# DialysisFlow-AgentBench

1,200 synthetic dialysis networks in which one unit closes some or all of its shifts and its patients must be re-placed in free chairs at nearby units, with a shared patient-transport fleet. The dataset also holds the result of nine placement policies on every network, including two exact MILP optima.

> **Synthetic operational data only.** No patient data, no clinical information. Nothing here supports clinical or treatment decisions.

- Code, paper and full method: [github.com/MHKhan50/dialysisflow-agentbench](https://github.com/MHKhan50/dialysisflow-agentbench)
- Software DOI (all versions): [10.5281/zenodo.24354744](https://doi.org/10.5281/zenodo.24354744)
- Matches release v0.2.1. Every scenario is regenerated from its seed by `scripts/export_hf.py`.

## Configurations

### `scenarios` (1,200 rows, 41,794 displaced patients)

| Field | Meaning |
|---|---|
| `scenario_id` | `S01000` to `S02199`; the number is the generator seed |
| `scarcity` | `low`, `medium` or `high`: 60–75%, 75–85% or 85–95% of chairs already in use |
| `severity` | `partial` (two shifts closed) or `full` (all four) |
| `units` | receiving units: `unit`, position `x_km`, `y_km` (the closed unit is at 20, 20) and `free_chairs` per shift |
| `transport_seats` | spare seats in the shared transport fleet, per shift, for the whole network |
| `patients` | displaced patients: `pid`, current `shift`, `cohort` (`transport` or `independent`), `travel_limit_min` (45 or 75), `travel_min` to each unit, and `options`, the feasible `unit|shift` pairs |

Shifts are `MWF-AM`, `MWF-PM`, `TTS-AM`, `TTS-PM`. A patient keeps their weekday pattern; moving between morning and afternoon is allowed and adds 20 minutes of burden. Travel time is 5 minutes plus 1.5 minutes per km.

### `policy_results` (10,800 rows: 1,200 scenarios × 9 policies)

`scenario_id`, `scarcity`, `severity`, `policy`, `n_patients`, `fulfilment` (share placed), `unmet_transport`, `unmet_independent`, `cohort_gap`, `mean_burden` (minutes), `time_changes`, `transport_overbooked`, `chair_overbooked`, `travel_violations`, `feasible` (1 if the plan respects every chair, seat and travel limit).

Policies: `list_order_greedy`, `most_constrained_greedy`, `independent_units`, `independent_units_gated`, `quota_units`, `repeated_independent_units`, `coordinated_units`, `optimal_throughput`, `optimal_fair`.

## Use

```python
from datasets import load_dataset

scenarios = load_dataset("MHkhan50/dialysisflow-agentbench", "scenarios", split="train")
results = load_dataset("MHkhan50/dialysisflow-agentbench", "policy_results", split="train")
```

A new placement policy can be scored against the same networks and compared with the exact optima in `policy_results`.

## Limitations

The networks are stylised: straight-line travel, one closure at a time, a fixed transport share of about 35%, and no clinical priority between patients. Results describe these networks, not any real dialysis service.

## Citation

```bibtex
@software{hussain_dialysisflow_agentbench,
  author  = {Hussain, Muzammal},
  title   = {DialysisFlow-AgentBench: re-placing displaced dialysis patients after a unit closure},
  version = {0.2.1},
  doi     = {10.5281/zenodo.24354744},
  url     = {https://github.com/MHKhan50/dialysisflow-agentbench}
}
```
