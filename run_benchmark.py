#!/usr/bin/env python3
"""Run the DialysisFlow scenario suite and write results/ (per-scenario rows, summary, charts)."""
from __future__ import annotations

import argparse
from pathlib import Path

from dialysisflow.evaluate import run_suite, summarise, write_outputs
from dialysisflow.figures import make_figures


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--per-cell", type=int, default=200, help="scenarios per scarcity x severity cell (6 cells)")
    parser.add_argument("--seed", type=int, default=1000, help="seed of the first scenario")
    parser.add_argument("--out", default="results")
    args = parser.parse_args()
    rows = run_suite(args.per_cell, args.seed)
    summary = summarise(rows)
    out = Path(args.out)
    write_outputs(rows, summary, out, args.per_cell, args.seed)
    make_figures(summary, out)
    print((out / "summary.md").read_text())


if __name__ == "__main__":
    main()
