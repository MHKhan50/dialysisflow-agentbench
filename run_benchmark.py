#!/usr/bin/env python3
"""Run DialysisFlow-AgentBench experiments using only the Python standard library."""
import argparse
from pathlib import Path
from dialysisflow.benchmark import run_experiment

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", nargs="+", type=int, default=[11, 23, 37, 51, 79])
    parser.add_argument("--data", default="data/scenarios.csv")
    parser.add_argument("--out", default="outputs")
    args = parser.parse_args()
    summary = run_experiment(Path(args.data), Path(args.out), args.seeds)
    print("Benchmark completed.")
    print(f"Scenarios: {summary['scenario_count']}")
    print(f"Seeds: {summary['seeds']}")
    print(f"Policies: {', '.join(summary['policies'])}")
    print(f"Outputs: {args.out}/")
    for row in summary["policy_summary"]:
        print(f"{row['policy']}: recovery_score={row['mean_recovery_score']:.3f}, "
              f"feasibility={row['feasibility_rate']:.3f}, "
              f"fairness_gap={row['mean_fairness_gap']:.3f}")

if __name__ == "__main__":
    main()
