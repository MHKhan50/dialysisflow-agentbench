#!/usr/bin/env python3
"""Upload hf_export/ to the Hugging Face dataset repo. Log in first with `hf auth login`."""
from __future__ import annotations

import argparse
from pathlib import Path

from huggingface_hub import HfApi

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default="MHkhan50/dialysisflow-agentbench")
    parser.add_argument("--folder", default=str(ROOT / "hf_export"))
    args = parser.parse_args()
    api = HfApi()
    api.create_repo(args.repo, repo_type="dataset", exist_ok=True)
    api.upload_folder(repo_id=args.repo, repo_type="dataset", folder_path=args.folder,
                      commit_message="DialysisFlow-AgentBench v0.2.1 scenarios and policy results")
    print("https://huggingface.co/datasets/" + args.repo)


if __name__ == "__main__":
    main()
