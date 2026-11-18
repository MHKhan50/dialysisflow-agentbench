"""Score plans, run the scenario suite and summarise with paired bootstrap intervals."""
from __future__ import annotations

import csv
import json
import platform
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Sequence

import numpy as np
import scipy

from . import __version__
from .network import COHORTS, SCARCITY_LEVELS, SEVERITY_LEVELS, TRAVEL_LIMIT, Scenario, make_scenario, make_suite
from .policies import POLICIES, Plan

METRICS = ("fulfilment", "unmet_transport", "unmet_independent", "cohort_gap", "mean_burden",
           "time_changes", "transport_overbooked", "chair_overbooked", "travel_violations", "feasible")


def score(scenario: Scenario, plan: Plan) -> Dict[str, float]:
    """Metrics for one plan. Violations are counted, not repaired."""
    by_pid = {p.pid: p for p in scenario.patients}
    chairs = Counter(plan.values())
    seats = Counter(shift for pid, (_, shift) in plan.items() if by_pid[pid].cohort == "transport")
    chair_over = sum(max(0, n - scenario.free_chairs[key]) for key, n in chairs.items())
    seat_over = sum(max(0, n - scenario.transport_seats[s]) for s, n in seats.items())
    travel_bad = sum(scenario.travel[(pid, unit)] > TRAVEL_LIMIT[by_pid[pid].cohort] for pid, (unit, _) in plan.items())
    pattern_bad = sum(shift.split("-")[0] != by_pid[pid].shift.split("-")[0] for pid, (_, shift) in plan.items())

    unmet = {}
    for cohort in COHORTS:
        members = [p for p in scenario.patients if p.cohort == cohort]
        unmet[cohort] = (sum(p.pid not in plan for p in members) / len(members)) if members else float("nan")
    burdens = [scenario.burden(by_pid[pid], u, s) for pid, (u, s) in plan.items()]
    gap = abs(unmet["transport"] - unmet["independent"]) if not any(np.isnan(v) for v in unmet.values()) else float("nan")
    return {
        "n_patients": len(scenario.patients),
        "fulfilment": len(plan) / len(scenario.patients),
        "unmet_transport": unmet["transport"],
        "unmet_independent": unmet["independent"],
        "cohort_gap": gap,
        "mean_burden": float(np.mean(burdens)) if burdens else float("nan"),
        "time_changes": sum(s != by_pid[pid].shift for pid, (_, s) in plan.items()) / len(scenario.patients),
        "transport_overbooked": seat_over,
        "chair_overbooked": chair_over,
        "travel_violations": travel_bad + pattern_bad,
        "feasible": float(seat_over == 0 and chair_over == 0 and travel_bad == 0 and pattern_bad == 0),
    }


def run_suite(n_per_cell: int, base_seed: int = 1000, log=print) -> List[Dict[str, object]]:
    rows = []
    suite = make_suite(n_per_cell, base_seed)
    started = time.monotonic()
    for i, scenario in enumerate(suite, 1):
        for name, policy in POLICIES.items():
            row = {"scenario_id": scenario.scenario_id, "scarcity": scenario.scarcity,
                   "severity": scenario.severity, "policy": name}
            row.update(score(scenario, policy(scenario)))
            rows.append(row)
        if i % 100 == 0:
            log("scenarios %d/%d (%.0f s)" % (i, len(suite), time.monotonic() - started))
    return rows


def _bootstrap_mean(values: np.ndarray, rng: np.random.Generator, n_boot: int = 2000) -> List[float]:
    values = values[~np.isnan(values)]
    if len(values) == 0:
        return [float("nan")] * 3
    idx = rng.integers(0, len(values), size=(n_boot, len(values)))
    means = values[idx].mean(axis=1)
    return [float(values.mean()), float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))]


def summarise(rows: Sequence[Dict[str, object]], seed: int = 7) -> Dict[str, object]:
    rng = np.random.default_rng(seed)
    policies = list(POLICIES)
    table = defaultdict(dict)
    groups = [("all", lambda r: True)] + [("scarcity=%s" % s, (lambda s: lambda r: r["scarcity"] == s)(s)) for s in SCARCITY_LEVELS] \
        + [("severity=%s" % s, (lambda s: lambda r: r["severity"] == s)(s)) for s in SEVERITY_LEVELS]
    for group, keep in groups:
        sub = [r for r in rows if keep(r)]
        for policy in policies:
            pr = [r for r in sub if r["policy"] == policy]
            table[group][policy] = {m: _bootstrap_mean(np.array([float(r[m]) for r in pr]), rng) for m in METRICS}

    # Paired differences against the fair optimum, scenario by scenario.
    paired = defaultdict(dict)
    index = {(r["scenario_id"], r["policy"]): r for r in rows}
    scenarios = sorted({r["scenario_id"] for r in rows})
    for policy in policies:
        if policy == "optimal_fair":
            continue
        for metric in ("fulfilment", "cohort_gap", "mean_burden"):
            diff = np.array([float(index[(s, policy)][metric]) - float(index[(s, "optimal_fair")][metric]) for s in scenarios])
            paired[policy][metric] = _bootstrap_mean(diff, rng)
    return {"by_group": table, "paired_vs_optimal_fair": paired, "n_scenarios": len(scenarios)}


def write_outputs(rows: Sequence[Dict[str, object]], summary: Dict[str, object], out: Path, n_per_cell: int, base_seed: int) -> None:
    out.mkdir(parents=True, exist_ok=True)
    with (out / "per_scenario.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    meta = {"version": __version__, "n_per_cell": n_per_cell, "base_seed": base_seed, "python": platform.python_version(),
            "numpy": np.__version__, "scipy": scipy.__version__, "bootstrap": "2000 resamples of scenarios, percentile 95% interval"}
    (out / "results.json").write_text(json.dumps({"meta": meta, **summary}, indent=2) + "\n")
    lines = ["| Policy | Fulfilment | Unmet (transport) | Unmet (independent) | Cohort gap | Mean burden (min) | Feasible plans |",
             "|---|---|---|---|---|---|---|"]
    for policy, m in summary["by_group"]["all"].items():
        def f(key, pct=True):
            v, a, b = m[key]
            return ("%.1f [%.1f, %.1f]" % (100 * v, 100 * a, 100 * b)) if pct else ("%.1f [%.1f, %.1f]" % (v, a, b))
        lines.append("| %s | %s | %s | %s | %s | %s | %s |" % (policy, f("fulfilment"), f("unmet_transport"),
                     f("unmet_independent"), f("cohort_gap"), f("mean_burden", False), f("feasible")))
    (out / "summary.md").write_text("\n".join(lines) + "\n")


SWEEP_SHARES = (0.2, 0.35, 0.5)
SWEEP_FLEET = (0.5, 1.0, 1.5)


def run_sweep(n_per_cell: int = 100, base_seed: int = 9000, log=print) -> List[Dict[str, object]]:
    """Sensitivity to transport: share of patients who need it and fleet size, at medium scarcity.

    Every cell uses the same seeds, so cells differ only in the two transport settings.
    """
    rows = []
    for share in SWEEP_SHARES:
        for fleet in SWEEP_FLEET:
            for severity in SEVERITY_LEVELS:
                for k in range(n_per_cell):
                    scenario = make_scenario(base_seed + k, "medium", severity, transport_share=share, fleet_factor=fleet)
                    for name, policy in POLICIES.items():
                        row = {"transport_share": share, "fleet_factor": fleet, "severity": severity,
                               "seed": base_seed + k, "policy": name}
                        row.update(score(scenario, policy(scenario)))
                        rows.append(row)
            log("sweep share=%.2f fleet=%.1f done" % (share, fleet))
    return rows


def summarise_sweep(rows: Sequence[Dict[str, object]]) -> List[Dict[str, object]]:
    out = []
    keys = sorted({(r["transport_share"], r["fleet_factor"], r["policy"]) for r in rows},
                  key=lambda k: (k[0], k[1], list(POLICIES).index(k[2])))
    for share, fleet, policy in keys:
        sub = [r for r in rows if r["transport_share"] == share and r["fleet_factor"] == fleet and r["policy"] == policy]
        gaps = [float(r["cohort_gap"]) for r in sub if not np.isnan(float(r["cohort_gap"]))]
        out.append({"transport_share": share, "fleet_factor": fleet, "policy": policy, "scenarios": len(sub),
                    "placed": float(np.mean([float(r["fulfilment"]) for r in sub])),
                    "cohort_gap": float(np.mean(gaps)) if gaps else float("nan"),
                    "unmet_transport": float(np.nanmean([float(r["unmet_transport"]) for r in sub])),
                    "unmet_independent": float(np.nanmean([float(r["unmet_independent"]) for r in sub])),
                    "feasible": float(np.mean([float(r["feasible"]) for r in sub]))})
    return out


def write_sweep(rows, summary, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    with (out / "sensitivity_per_scenario.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader(); writer.writerows(rows)
    with (out / "sensitivity_summary.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summary[0].keys()))
        writer.writeheader(); writer.writerows(summary)
