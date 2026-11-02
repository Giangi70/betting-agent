"""Test del motore su dati simulati + verifica end-to-end con server mock.

Esegui: /home/egiabot/venvs/betting-agent/bin/python -m betting_agent.tests_engine
"""
from __future__ import annotations

from .client import PredictorData
from .config import AgentConfig, PredictorEndpoint
from .engine import (
    allocate_budget,
    build_allocation,
    expected_value,
    kelly_fraction_full,
    rank_bets,
)
from .schemas import Signal, SignalsResponse


def _cfg(**over) -> AgentConfig:
    base = dict(
        budget=100.0, kelly_fraction=0.25, max_stake_fraction=0.15, min_ev=0.0,
        api_key="", http_timeout=5.0, llm_comment=False, bonus_stagione_calda=0.5,
        predictors=[PredictorEndpoint(name="X", base_url="http://x", peso=1.0)],
    )
    base.update(over)
    return AgentConfig(**base)


def _signal(prob, quota, tipo="safe", esito="H") -> Signal:
    return Signal(match_date="2026-11-08", home_team="A", away_team="B",
                  tipo=tipo, esito=esito, quota=quota, prob=prob, prob_gap=0.2)


def _data(signals, peso=1.0, calda=False, name="X") -> PredictorData:
    sr = SignalsResponse(sport=name, n_safe=len(signals), n_jolly=0,
                         safe=signals, jolly=[], stagione_calda=calda)
    return PredictorData(name=name, peso=peso, available=True, signals=sr, roi=None)


def t_ev():
    # prob 0.6, quota 2.0 -> EV = 0.2
    assert abs(expected_value(0.6, 2.0) - 0.2) < 1e-9
    # prob 0.5, quota 2.0 -> EV = 0 (break-even)
    assert abs(expected_value(0.5, 2.0)) < 1e-9
    print("[EV] OK")
    return True


def t_kelly():
    # prob 0.6 quota 2.0: kelly = (1.2-1)/(2-1) = 0.2
    assert abs(kelly_fraction_full(0.6, 2.0) - 0.2) < 1e-9
    # EV negativo -> kelly 0
    assert kelly_fraction_full(0.4, 2.0) == 0.0
    print("[Kelly] OK")
    return True


def t_filtro_min_ev():
    cfg = _cfg(min_ev=0.0)
    data = [_data([_signal(0.6, 2.0), _signal(0.4, 2.0)])]  # 2a ha EV<0
    bets = rank_bets(data, cfg)
    assert len(bets) == 1 and abs(bets[0].ev - 0.2) < 1e-9
    print("[filtro min_ev] OK — scartata la scommessa EV<=0")
    return True


def t_ranking_e_bonus_stagione_calda():
    cfg = _cfg()
    # stessa EV (0.2) ma uno sport e in stagione calda -> deve rankare piu in alto
    d_normale = _data([_signal(0.6, 2.0)], peso=1.0, calda=False, name="Normale")
    d_calda = _data([_signal(0.6, 2.0)], peso=1.0, calda=True, name="Calda")
    bets = rank_bets([d_normale, d_calda], cfg)
    assert bets[0].sport == "Calda", "la stagione calda deve rankare prima"
    # score calda = 0.2 * 1.0 * 1.5 = 0.3 ; normale = 0.2
    assert abs(bets[0].score - 0.3) < 1e-9 and abs(bets[1].score - 0.2) < 1e-9
    print("[ranking + bonus stagione calda] OK")
    return True


def t_peso_sport():
    cfg = _cfg()
    d_a = _data([_signal(0.6, 2.0)], peso=1.0, name="A")
    d_b = _data([_signal(0.6, 2.0)], peso=1.5, name="B")
    bets = rank_bets([d_a, d_b], cfg)
    assert bets[0].sport == "B", "peso_sport piu alto deve rankare prima"
    print("[peso_sport] OK")
    return True


def t_cap_stake():
    # kelly alto -> stake grezzo oltre il cap, deve essere limitato a budget*max_stake_fraction
    cfg = _cfg(budget=100.0, kelly_fraction=1.0, max_stake_fraction=0.15)
    data = [_data([_signal(0.9, 2.0)])]  # kelly_full = (1.8-1)/1 = 0.8 -> raw=80€
    alloc = build_allocation(data, cfg)
    assert alloc.bets[0].stake == 15.0, f"atteso cap 15.0, ottenuto {alloc.bets[0].stake}"
    print("[cap stake] OK — stake limitato al 15% del budget")
    return True


def t_budget_non_sforato():
    # tante scommesse forti: la somma stake non deve superare il budget
    cfg = _cfg(budget=100.0, kelly_fraction=1.0, max_stake_fraction=0.5)
    sigs = [_signal(0.9, 2.0) for _ in range(5)]  # 5 x raw cap 50€ = 250€ > budget
    alloc = build_allocation([_data(sigs)], cfg)
    assert alloc.totale_allocato <= cfg.budget + 1e-6, "il budget non deve essere sforato"
    print(f"[budget cap] OK — allocato {alloc.totale_allocato:.2f} <= {cfg.budget}")
    return True


def t_predictor_offline():
    cfg = _cfg()
    offline = PredictorData(name="Down", peso=1.0, available=False, error="timeout")
    online = _data([_signal(0.6, 2.0)])
    bets = rank_bets([offline, online], cfg)
    assert len(bets) == 1, "il predictor offline non deve contribuire scommesse"
    print("[predictor offline] OK — ignorato senza crash")
    return True


def main():
    print("=== TEST MOTORE betting-agent (dati simulati) ===")
    tests = [t_ev, t_kelly, t_filtro_min_ev, t_ranking_e_bonus_stagione_calda,
             t_peso_sport, t_cap_stake, t_budget_non_sforato, t_predictor_offline]
    ok = sum(bool(t()) for t in tests)
    print(f"\n{ok}/{len(tests)} test superati.")
    if ok != len(tests):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
