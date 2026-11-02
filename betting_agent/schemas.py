"""Schema pydantic delle risposte dei predictor (/signals, /roi, /health).

Rispecchia il formato prodotto da betting_core/api.py. Validare le risposte protegge
l'agent da predictor che cambiano formato o rispondono in modo inatteso.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class Signal(BaseModel):
    """Una scommessa suggerita dalla strategia mista."""
    match_date: str
    home_team: str
    away_team: str
    tipo: str           # "safe" | "jolly"
    esito: str          # "H" | "D" | "A"
    quota: float
    prob: float         # probabilita stimata dell'esito scelto
    prob_gap: float


class SignalsResponse(BaseModel):
    sport: str
    n_safe: int
    n_jolly: int
    safe: list[Signal]
    jolly: list[Signal]
    stagione_calda: bool


class RoiResponse(BaseModel):
    sport: str
    roi: float | None
    n_scommesse: int
    pl: float
    stagione_calda: bool
    season_start: str
    n_scommesse_totali: int


class HealthResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    status: str
    sport: str
    model_loaded: bool
    dataset_present: bool
    auth_required: bool
    timestamp: str
