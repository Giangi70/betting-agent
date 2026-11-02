"""Test end-to-end: avvia server mock dei predictor e lancia l'agent completo.

Verifica l'intera pipeline: fetch concorrente -> parsing pydantic -> motore ->
report, incluso un predictor offline e uno senza segnali (503).

Esegui: /home/egiabot/venvs/betting-agent/bin/python -m betting_agent.tests_e2e
"""
from __future__ import annotations

import threading
import time

import uvicorn
from fastapi import FastAPI, Response

from .client import fetch_all
from .config import AgentConfig, PredictorEndpoint
from .engine import build_allocation


def _make_predictor(sport: str, calda: bool, with_signals: bool) -> FastAPI:
    app = FastAPI()

    @app.get("/roi")
    def roi():
        return {
            "sport": sport, "roi": 0.12 if calda else 0.02, "n_scommesse": 30,
            "pl": 3.6, "stagione_calda": calda, "season_start": "2025-08-01",
            "n_scommesse_totali": 50,
        }

    @app.get("/signals")
    def signals():
        if not with_signals:
            return Response(content='{"detail":"quote non disponibili"}',
                            status_code=503, media_type="application/json")
        return {
            "sport": sport, "n_safe": 1, "n_jolly": 1,
            "safe": [{"match_date": "2026-11-08", "home_team": f"{sport}Casa",
                      "away_team": f"{sport}Ospite", "tipo": "safe", "esito": "H",
                      "quota": 1.9, "prob": 0.60, "prob_gap": 0.25}],
            "jolly": [{"match_date": "2026-11-08", "home_team": f"{sport}JCasa",
                       "away_team": f"{sport}JOspite", "tipo": "jolly", "esito": "A",
                       "quota": 6.0, "prob": 0.18, "prob_gap": 0.25}],
            "stagione_calda": calda,
        }

    return app


def _serve(app: FastAPI, port: int) -> uvicorn.Server:
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")
    server = uvicorn.Server(config)
    threading.Thread(target=server.run, daemon=True).start()
    return server


def main():
    print("=== TEST END-TO-END betting-agent (server mock) ===")
    # 3 predictor su porte mock; il 4o volutamente NON avviato (offline).
    servers = [
        _serve(_make_predictor("Serie A", calda=False, with_signals=True), 18001),
        _serve(_make_predictor("Serie B", calda=True, with_signals=True), 18002),   # calda
        _serve(_make_predictor("La Liga 2", calda=False, with_signals=False), 18003),  # 503
    ]
    # attende che i server siano su
    time.sleep(1.5)

    cfg = AgentConfig(
        budget=100.0, kelly_fraction=0.25, max_stake_fraction=0.15, min_ev=0.0,
        api_key="", http_timeout=5.0, llm_comment=True, bonus_stagione_calda=0.5,
        predictors=[
            PredictorEndpoint(name="Serie A", base_url="http://127.0.0.1:18001", peso=1.0),
            PredictorEndpoint(name="Serie B", base_url="http://127.0.0.1:18002", peso=1.1),
            PredictorEndpoint(name="La Liga 2", base_url="http://127.0.0.1:18003", peso=1.05),
            PredictorEndpoint(name="Bundesliga 2", base_url="http://127.0.0.1:18004", peso=1.05),  # OFFLINE
        ],
    )

    data = fetch_all(cfg)
    by_name = {d.name: d for d in data}

    # Asserzioni sullo stato dei predictor
    assert by_name["Serie A"].available and by_name["Serie A"].signals is not None, "Serie A deve avere segnali"
    assert by_name["Serie B"].available and by_name["Serie B"].roi.stagione_calda, "Serie B deve essere calda"
    assert by_name["La Liga 2"].available and by_name["La Liga 2"].signals is None, "La Liga 2: 503 -> roi ok, niente segnali"
    assert not by_name["Bundesliga 2"].available, "Bundesliga 2 deve risultare offline"
    print("[stato predictor] OK — 1 calda, 1 senza segnali (503), 1 offline")

    alloc = build_allocation(data, cfg)

    # Serie A e Serie B danno segnali (2 ciascuno) -> 4 scommesse; La Liga2/Bundes no
    assert alloc.n_bets == 4, f"attese 4 scommesse, ottenute {alloc.n_bets}"
    # La prima in classifica deve essere una safe della Serie B (calda, peso 1.1)
    top = alloc.bets[0]
    assert top.sport == "Serie B" and top.tipo == "safe", f"top inatteso: {top.sport}/{top.tipo}"
    assert top.stagione_calda, "la top deve venire dallo sport caldo"
    print(f"[ranking e2e] OK — top: {top.sport} {top.esito} score={top.score:.3f}")

    # Budget non sforato
    assert alloc.totale_allocato <= cfg.budget + 1e-6
    print(f"[budget e2e] OK — allocato {alloc.totale_allocato:.2f}/{cfg.budget}")

    # Render del report reale (visivo)
    from .llm_comment import generate_comment
    from .report import render_report
    calde = [d.name for d in data if d.roi and d.roi.stagione_calda]
    print("\n--- REPORT RENDERIZZATO ---")
    render_report(data, alloc, cfg, generate_comment(alloc, calde))

    for s in servers:
        s.should_exit = True
    print("\nTEST E2E SUPERATO.")


if __name__ == "__main__":
    main()
