"""Configurazione del betting-agent (caricata da config.yaml, validata con pydantic)."""
from __future__ import annotations

import os
from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class PredictorEndpoint(BaseModel):
    """Un predictor da interrogare."""
    name: str
    base_url: str
    peso: float = 1.0


class AgentConfig(BaseModel):
    """Configurazione completa dell'agent."""
    budget: float = 100.0
    kelly_fraction: float = Field(0.25, ge=0.0, le=1.0)
    max_stake_fraction: float = Field(0.15, ge=0.0, le=1.0)
    min_ev: float = 0.0
    api_key: str = ""
    http_timeout: float = 10.0
    llm_comment: bool = False
    bonus_stagione_calda: float = 0.5
    predictors: list[PredictorEndpoint]

    @classmethod
    def load(cls, path: str | Path) -> "AgentConfig":
        """Carica e valida la config da file YAML.

        La API key puo essere sovrascritta dalla variabile d'ambiente AGENT_API_KEY.
        """
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        cfg = cls(**data)
        env_key = os.getenv("AGENT_API_KEY")
        if env_key:
            cfg.api_key = env_key
        return cfg
