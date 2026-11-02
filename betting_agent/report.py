"""Report settimanale formattato con rich."""
from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .client import PredictorData
from .config import AgentConfig
from .engine import Allocation


def render_report(
    data: list[PredictorData], alloc: Allocation, cfg: AgentConfig, comment: str | None = None
) -> None:
    """Stampa il report settimanale a console."""
    console = Console()
    console.rule("[bold]Betting Agent — Report settimanale[/bold]")

    _render_predictor_status(console, data)
    _render_bets(console, alloc)
    _render_summary(console, alloc)

    if comment:
        console.print(Panel(comment, title="Commento", border_style="cyan"))


def _render_predictor_status(console: Console, data: list[PredictorData]) -> None:
    t = Table(title="Stato predictor", show_header=True, header_style="bold")
    t.add_column("Sport")
    t.add_column("Stato")
    t.add_column("ROI stagione", justify="right")
    t.add_column("Stagione calda")
    t.add_column("Note")
    for pd in data:
        if not pd.available:
            t.add_row(pd.name, "[red]offline[/red]", "—", "—", pd.error or "")
            continue
        roi = pd.roi.roi if pd.roi else None
        roi_s = f"{roi*100:+.1f}%" if roi is not None else "—"
        calda = "[bold yellow]SI[/bold yellow]" if (pd.roi and pd.roi.stagione_calda) else "no"
        nota = "" if pd.signals else (pd.error or "nessun segnale")
        t.add_row(pd.name, "[green]online[/green]", roi_s, calda, nota)
    console.print(t)


def _render_bets(console: Console, alloc: Allocation) -> None:
    if alloc.n_bets == 0:
        console.print("[yellow]Nessuna scommessa con EV positivo questa settimana.[/yellow]")
        return
    t = Table(title="Scommesse consigliate (ordinate per score)", show_header=True, header_style="bold")
    t.add_column("#", justify="right")
    t.add_column("Sport")
    t.add_column("Partita")
    t.add_column("Tipo")
    t.add_column("Esito")
    t.add_column("Quota", justify="right")
    t.add_column("Prob", justify="right")
    t.add_column("EV", justify="right")
    t.add_column("Score", justify="right")
    t.add_column("Stake €", justify="right")
    for i, b in enumerate(alloc.bets, 1):
        calda = " 🔥" if b.stagione_calda else ""
        t.add_row(
            str(i), b.sport + calda, f"{b.home_team}-{b.away_team}", b.tipo, b.esito,
            f"{b.quota:.2f}", f"{b.prob*100:.1f}%", f"{b.ev:+.1%}",
            f"{b.score:.3f}", f"{b.stake:.2f}",
        )
    console.print(t)


def _render_summary(console: Console, alloc: Allocation) -> None:
    console.print(
        f"Budget: [bold]{alloc.budget:.2f}€[/bold]  |  "
        f"Allocato: [bold]{alloc.totale_allocato:.2f}€[/bold]  |  "
        f"Residuo: [bold]{alloc.residuo:.2f}€[/bold]  |  "
        f"Scommesse: [bold]{alloc.n_bets}[/bold]"
    )
