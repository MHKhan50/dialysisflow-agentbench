import tempfile
import unittest
from pathlib import Path
from dialysisflow.benchmark import (
    POLICIES, evaluate_episode, load_scenarios, run_experiment
)

ROOT = Path(__file__).resolve().parents[1]

class BenchmarkTests(unittest.TestCase):
    def test_dataset_loads(self):
        rows = load_scenarios(ROOT / "data" / "scenarios.csv")
        self.assertEqual(len(rows), 20)

    def test_allocation_never_exceeds_capacity_for_safety_gated_policy(self):
        row = load_scenarios(ROOT / "data" / "scenarios.csv")[1]
        result = evaluate_episode(row, "coordinated_safety_gated", 11)
        self.assertLessEqual(result["allocated"], result["operational_capacity"])
        self.assertEqual(result["safety_violations"], 0)

    def test_runner_writes_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            summary = run_experiment(ROOT / "data" / "scenarios.csv", Path(tmp), [11, 23])
            self.assertEqual(summary["episode_count"], 20 * len(POLICIES) * 2)
            self.assertTrue((Path(tmp) / "episode_results.csv").exists())
            self.assertTrue((Path(tmp) / "policy_summary.csv").exists())
            self.assertTrue((Path(tmp) / "summary.json").exists())

if __name__ == "__main__":
    unittest.main()
