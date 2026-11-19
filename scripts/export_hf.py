#!/usr/bin/env python3
"""Export the 1,200 benchmark scenarios and the per-policy results as a Hugging Face dataset folder.

Writes ``hf_export/`` with:
  data/scenarios.jsonl      one network per line (units, free chairs, transport seats, patients, travel times)
  data/policy_results.jsonl one row per scenario and policy (from results/per_scenario.csv)
  README.md                 the dataset card (copied from hf/README.md)

Everything is regenerated from seeds, so the export matches the paper exactly.
"""
from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dialysisflow.network import SHIFTS, TRAVEL_LIMIT, make_suite  # noqa: E402


def scenario_record(s) -> dict:
    return {
        "scenario_id": s.scenario_id,
        "scarcity": s.scarcity,
        "severity": s.severity,
        "units": [
            {
                "unit": u,
                "x_km": round(s.unit_location[u][0], 3),
                "y_km": round(s.unit_location[u][1], 3),
                "free_chairs": {sh: s.free_chairs[(u, sh)] for sh in SHIFTS},
            }
            for u in s.units
        ],
        "transport_seats": {sh: s.transport_seats[sh] for sh in SHIFTS},
        "patients": [
            {
                "pid": p.pid,
                "shift": p.shift,
                "cohort": p.cohort,
                "travel_limit_min": TRAVEL_LIMIT[p.cohort],
                "travel_min": {u: s.travel[(p.pid, u)] for u in s.units},
                "options": ["%s|%s" % o for o in s.options(p)],
            }
            for p in s.patients
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--per-cell", type=int, default=200)
    parser.add_argument("--seed", type=int, default=1000)
    parser.add_argument("--out", default=str(ROOT / "hf_export"))
    args = parser.parse_args()

    out = Path(args.out)
    if out.exists():
        shutil.rmtree(out)
    (out / "data").mkdir(parents=True)

    suite = make_suite(args.per_cell, args.seed)
    n_patients = 0
    with open(out / "data" / "scenarios.jsonl", "w", encoding="utf-8") as fh:
        for s in suite:
            fh.write(json.dumps(scenario_record(s), separators=(",", ":")) + "\n")
            n_patients += len(s.patients)

    # The viewer infers one format for the whole repo, so both tables are JSON Lines.
    text = {"scenario_id", "scarcity", "severity", "policy"}
    whole = {"n_patients", "transport_overbooked", "chair_overbooked", "travel_violations"}
    with open(ROOT / "results" / "per_scenario.csv", newline="", encoding="utf-8") as src, \
            open(out / "data" / "policy_results.jsonl", "w", encoding="utf-8") as dst:
        for row in csv.DictReader(src):
            record = {k: (v if k in text else int(float(v)) if k in whole else float(v)) for k, v in row.items()}
            dst.write(json.dumps(record, separators=(",", ":")) + "\n")
    shutil.copy(ROOT / "hf" / "README.md", out / "README.md")
    print("scenarios:", len(suite), "| displaced patients:", n_patients, "| folder:", out)


if __name__ == "__main__":
    main()
