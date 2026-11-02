"""Motore decisionale: EV, ranking per score, allocazione budget con Kelly frazionato.

Tutto deterministico: stessi input -> stesso output. Nessun LLM nel loop decisionale.

Definizioni:
    EV   = prob_stimata * quota - 1        (valore atteso per euro, > 0 = profittevole)
    kelly_full = (prob*quota - 1) / (quota - 1) = EV / (quota - 1)   (frazione ottima)
    stake = budget * kelly_full * kelly_fraction, con cap max_stake_fraction

Score di ranking (dal piano BettingEcosystem):
    score = EV * peso_sport * (1 + bonus_stagione_calda_se_attiva)
"""
from __future__ import annotations

from dataclasses import dataclass

from .client import PredictorData
from .config import AgentConfig


@dataclass
class RankedBet:
    """Una scommessa valutata e pronta per l'allocazione."""
    sport: str
    home_team: str
    away_team: str
    match_date: str
    tipo: str
    esito: str
    quota: float
    prob: float
    ev: float
    score: float
    stagione_calda: bool
    stake: float = 0.0  # riempito in fase di allocazione


def expected_value(prob: float, quota: float) -> float:
    """EV per euro giocato: prob*quota - 1."""
    return prob * quota - 1.0


def kelly_fraction_full(prob: float, quota: float) -> float:
    """Frazione di Kelly piena. 0 se la scommessa non ha edge (EV <= 0)."""
    b = quota - 1.0
    if b <= 0:
        return 0.0
    f = (prob * quota - 1.0) / b
    return max(f, 0.0)


def rank_bets(data: list[PredictorData], cfg: AgentConfig) -> list[RankedBet]:
    """Costruisce e ordina le scommesse candidate da tutti i predictor.

    Filtra quelle con EV < cfg.min_ev. Ordina per score decrescente.
    """
    bets: list[RankedBet] = []
    for pd in data:
        if not pd.available or pd.signals is None:
            continue
        calda = pd.signals.stagione_calda
        bonus = (1.0 + cfg.bonus_stagione_calda) if calda else 1.0
        for sig in pd.signals.safe + pd.signals.jolly:
            ev = expected_value(sig.prob, sig.quota)
            if ev < cfg.min_ev:
                continue
            score = ev * pd.peso * bonus
            bets.append(RankedBet(
                sport=pd.name, home_team=sig.home_team, away_team=sig.away_team,
                match_date=sig.match_date, tipo=sig.tipo, esito=sig.esito,
                quota=sig.quota, prob=sig.prob, ev=ev, score=score,
                stagione_calda=calda,
            ))
    bets.sort(key=lambda b: b.score, reverse=True)
    return bets


def allocate_budget(bets: list[RankedBet], cfg: AgentConfig) -> list[RankedBet]:
    """Assegna uno stake a ciascuna scommessa con Kelly frazionato.

    - stake_grezzo = budget * kelly_full * kelly_fraction
    - cap per scommessa = budget * max_stake_fraction
    - se la somma degli stake supera il budget, si ridimensiona proporzionalmente
      (nessuna leva: non si scommette piu del budget disponibile).
    """
    cap = cfg.budget * cfg.max_stake_fraction
    for b in bets:
        kf = kelly_fraction_full(b.prob, b.quota)
        raw = cfg.budget * kf * cfg.kelly_fraction
        b.stake = round(min(raw, cap), 2)

    totale = sum(b.stake for b in bets)
    if totale > cfg.budget and totale > 0:
        fattore = cfg.budget / totale
        for b in bets:
            b.stake = round(b.stake * fattore, 2)
    return bets


@dataclass
class Allocation:
    """Risultato completo dell'allocazione."""
    bets: list[RankedBet]
    budget: float
    totale_allocato: float
    n_bets: int

    @property
    def residuo(self) -> float:
        return round(self.budget - self.totale_allocato, 2)


def build_allocation(data: list[PredictorData], cfg: AgentConfig) -> Allocation:
    """Pipeline completa del motore: rank -> allocate."""
    ranked = allocate_budget(rank_bets(data, cfg), cfg)
    totale = round(sum(b.stake for b in ranked), 2)
    return Allocation(bets=ranked, budget=cfg.budget, totale_allocato=totale, n_bets=len(ranked))
