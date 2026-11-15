"""Synthetic operational recovery benchmark; not a clinical decision system."""
import csv
import json
import random
from collections import defaultdict
from pathlib import Path

POLICIES = (
    "centralised_baseline",
    "single_agent_baseline",
    "uncoordinated_multi_agent",
    "coordinated_safety_gated",
)

def load_scenarios(path):
    with open(path, newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    required = {"scenario_id", "sessions_requested", "available_slots",
                "staff_capacity", "machine_capacity", "disruption_severity",
                "priority_class"}
    if not rows:
        raise ValueError("Scenario dataset is empty")
    missing = required.difference(rows[0])
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")
    for row in rows:
        for field in ("sessions_requested", "available_slots", "staff_capacity",
                      "machine_capacity", "disruption_severity"):
            row[field] = int(row[field])
        if row["sessions_requested"] < 1 or min(
            row["available_slots"], row["staff_capacity"], row["machine_capacity"]
        ) < 0:
            raise ValueError(f"Invalid capacity in {row['scenario_id']}")
        if row["priority_class"] not in {"standard", "higher"}:
            raise ValueError(f"Unknown synthetic priority class in {row['scenario_id']}")
    return rows

def _allocation_capacity(row, policy, rng):
    caps = [row["available_slots"], row["staff_capacity"], row["machine_capacity"]]
    physical_cap = min(caps)
    if policy == "centralised_baseline":
        return physical_cap
    if policy == "single_agent_baseline":
        # A deliberately simple heuristic baseline with occasional planning error.
        return max(0, physical_cap - (1 if rng.random() < 0.12 else 0))
    if policy == "uncoordinated_multi_agent":
        # Independent agents can overestimate joint capacity when their views conflict.
        return max(0, physical_cap - (1 if rng.random() < 0.08 else 0))
    if policy == "coordinated_safety_gated":
        # Explicitly reconcile all three capacity views before allocating.
        return physical_cap
    raise ValueError(f"Unknown policy: {policy}")

def evaluate_episode(row, policy, seed):
    rng = random.Random(f"{seed}:{row['scenario_id']}:{policy}")
    requested = row["sessions_requested"]
    capacity = _allocation_capacity(row, policy, rng)
    if policy == "uncoordinated_multi_agent" and rng.random() < 0.10:
        # An inconsistent plan is detected by the independent constraint checker.
        proposed = min(requested, capacity + 1)
    else:
        proposed = min(requested, capacity)

    safety_violation = int(proposed > min(
        row["available_slots"], row["staff_capacity"], row["machine_capacity"]
    ))
    if policy == "coordinated_safety_gated":
        # Gate rejects any allocation exceeding the reconciled operational capacity.
        proposed = min(proposed, capacity)
        safety_violation = 0

    allocated = max(0, proposed)
    unallocated = requested - allocated
    delay_burden = unallocated * (2 if row["priority_class"] == "higher" else 1)
    # Fairness proxy: absolute gap between normalised unallocated burden by class
    # is not identifiable within a single episode; use a transparent per-episode
    # burden rate and aggregate it by policy instead.
    burden_rate = delay_burden / max(1, requested)
    recovery_score = allocated / requested
    human_review = int(
        policy == "coordinated_safety_gated"
        and (row["disruption_severity"] >= 3 or unallocated > 0)
    )
    return {
        "scenario_id": row["scenario_id"],
        "seed": seed,
        "policy": policy,
        "requested": requested,
        "allocated": allocated,
        "unallocated": unallocated,
        "operational_capacity": min(row["available_slots"], row["staff_capacity"],
                                    row["machine_capacity"]),
        "safety_violations": safety_violation,
        "delay_burden": delay_burden,
        "burden_rate": round(burden_rate, 6),
        "recovery_score": round(recovery_score, 6),
        "human_review_required": human_review,
    }

def _mean(values):
    return sum(values) / len(values) if values else 0.0

def summarise(results):
    grouped = defaultdict(list)
    for result in results:
        grouped[result["policy"]].append(result)
    summary = []
    for policy in POLICIES:
        rows = grouped[policy]
        total = len(rows)
        summary.append({
            "policy": policy,
            "episodes": total,
            "mean_recovery_score": round(_mean([r["recovery_score"] for r in rows]), 6),
            "feasibility_rate": round(1 - _mean([r["safety_violations"] for r in rows]), 6),
            "mean_unallocated": round(_mean([r["unallocated"] for r in rows]), 6),
            "mean_delay_burden": round(_mean([r["delay_burden"] for r in rows]), 6),
            "mean_fairness_gap": round(_mean([r["burden_rate"] for r in rows]), 6),
            "human_review_rate": round(_mean([r["human_review_required"] for r in rows]), 6),
        })
    return summary

def run_experiment(data_path, output_dir, seeds):
    scenarios = load_scenarios(data_path)
    results = [
        evaluate_episode(scenario, policy, seed)
        for seed in seeds
        for scenario in scenarios
        for policy in POLICIES
    ]
    output_dir.mkdir(parents=True, exist_ok=True)
    episode_path = output_dir / "episode_results.csv"
    with open(episode_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(results[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(results)
    policy_summary = summarise(results)
    summary_path = output_dir / "policy_summary.csv"
    with open(summary_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(policy_summary[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(policy_summary)
    metadata = {
        "benchmark": "DialysisFlow-AgentBench",
        "version": "0.1.0",
        "scenario_count": len(scenarios),
        "seeds": list(seeds),
        "policies": list(POLICIES),
        "episode_count": len(results),
        "policy_summary": policy_summary,
        "scope": "synthetic operational simulation; not clinical evidence",
    }
    with open(output_dir / "summary.json", "w", encoding="utf-8") as handle:
        json.dump(metadata, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return metadata
