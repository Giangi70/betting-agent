"""Entry point del betting-agent.

Uso:
    python -m betting_agent.main                 # usa config.yaml nella root
    python -m betting_agent.main path/config.yaml
"""
from __future__ import annotations

import sys
from pathlib import Path

from .client import fetch_all
from .config import AgentConfig
from .engine import build_allocation
from .llm_comment import generate_comment
from .report import render_report

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = ROOT / "config.yaml"


def run(config_path: str | Path = DEFAULT_CONFIG) -> None:
    cfg = AgentConfig.load(config_path)
    data = fetch_all(cfg)
    alloc = build_allocation(data, cfg)

    calde = [pd.name for pd in data if pd.roi and pd.roi.stagione_calda]
    comment = generate_comment(alloc, calde) if cfg.llm_comment else None

    render_report(data, alloc, cfg, comment)


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_CONFIG
    run(arg)
