"""Gancio opzionale per un commento in linguaggio naturale del report.

ISOLATO DI PROPOSITO: non e nel loop decisionale. Il motore (engine.py) decide
tutto in modo deterministico; qui si traduce solo il risultato gia calcolato in
una frase leggibile. Disattivato di default (cfg.llm_comment).

Se attivato ma nessun backend LLM e configurato, ritorna un riassunto testuale
deterministico (nessuna dipendenza esterna, nessuna chiamata di rete).
"""
from __future__ import annotations

from .engine import Allocation


def generate_comment(alloc: Allocation, calde: list[str]) -> str:
    """Produce un commento sintetico del report.

    Implementazione attuale: riassunto deterministico (no LLM, no rete).
    Per agganciare un vero LLM, sostituire il corpo con una singola chiamata al
    modello passando i dati di `alloc` — senza che questo influenzi l'allocazione.
    """
    if alloc.n_bets == 0:
        return "Nessuna scommessa con valore atteso positivo questa settimana: meglio non puntare."

    top = alloc.bets[0]
    parti = [
        f"Questa settimana {alloc.n_bets} scommesse con EV positivo, "
        f"{alloc.totale_allocato:.2f} EUR allocati su {alloc.budget:.0f} di budget.",
        f"La piu forte e {top.home_team}-{top.away_team} ({top.sport}, esito {top.esito}) "
        f"con EV {top.ev:+.1%} e stake {top.stake:.2f} EUR.",
    ]
    if calde:
        parti.append(
            f"Occhio agli sport in stagione calda ({', '.join(calde)}): "
            f"il loro peso e aumentato nel ranking."
        )
    return " ".join(parti)
