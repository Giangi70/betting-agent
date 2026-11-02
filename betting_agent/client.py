"""Client HTTP che interroga i predictor in parallelo.

Usa httpx in modalita asincrona per colpire i 4 endpoint contemporaneamente.
Un predictor non raggiungibile o che risponde 503 (quote non disponibili) non
blocca gli altri: viene marcato come 'non disponibile' e il report lo segnala.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass

import httpx

from .config import AgentConfig, PredictorEndpoint
from .schemas import RoiResponse, SignalsResponse


@dataclass
class PredictorData:
    """Dati raccolti da un predictor (o lo stato di errore)."""
    name: str
    peso: float
    available: bool
    signals: SignalsResponse | None = None
    roi: RoiResponse | None = None
    error: str | None = None


def _headers(cfg: AgentConfig) -> dict[str, str]:
    return {"X-API-Key": cfg.api_key} if cfg.api_key else {}


async def _fetch_one(
    client: httpx.AsyncClient, ep: PredictorEndpoint, cfg: AgentConfig
) -> PredictorData:
    """Interroga /signals e /roi di un singolo predictor."""
    headers = _headers(cfg)
    try:
        r_sig, r_roi = await asyncio.gather(
            client.get(f"{ep.base_url}/signals", headers=headers),
            client.get(f"{ep.base_url}/roi", headers=headers),
        )
    except httpx.HTTPError as exc:
        return PredictorData(ep.name, ep.peso, available=False, error=f"connessione: {exc}")

    # /roi deve rispondere 200; /signals puo dare 503 se mancano le quote live.
    if r_roi.status_code != 200:
        return PredictorData(ep.name, ep.peso, available=False,
                             error=f"/roi HTTP {r_roi.status_code}")

    roi = RoiResponse.model_validate(r_roi.json())

    signals = None
    err = None
    if r_sig.status_code == 200:
        signals = SignalsResponse.model_validate(r_sig.json())
    else:
        # Quote non disponibili: ROI c'e, ma niente segnali da giocare questa settimana.
        detail = ""
        try:
            detail = r_sig.json().get("detail", "")
        except Exception:  # noqa: BLE001
            detail = r_sig.text[:120]
        err = f"/signals HTTP {r_sig.status_code}: {detail}"

    return PredictorData(ep.name, ep.peso, available=True,
                         signals=signals, roi=roi, error=err)


async def _fetch_all(cfg: AgentConfig) -> list[PredictorData]:
    timeout = httpx.Timeout(cfg.http_timeout)
    async with httpx.AsyncClient(timeout=timeout) as client:
        tasks = [_fetch_one(client, ep, cfg) for ep in cfg.predictors]
        return await asyncio.gather(*tasks)


def fetch_all(cfg: AgentConfig) -> list[PredictorData]:
    """Entry point sincrono: raccoglie i dati da tutti i predictor in parallelo."""
    return asyncio.run(_fetch_all(cfg))
