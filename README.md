# betting-agent

Agente centrale dell'ecosistema: interroga i 4 predictor via API, rankinga le scommesse
per Expected Value, alloca il budget con Kelly frazionato e produce il **report settimanale**.

**Python puro** — niente LangChain/LlamaIndex. Il motore decisionale è deterministico
(`httpx` + `pydantic` + aritmetica): stessi input → stesso output, come deve essere per
un calcolo su cui si allocano soldi. Un eventuale commento in linguaggio naturale è un
layer opzionale e isolato, fuori dal loop decisionale.

## Cosa fa

1. Interroga in parallelo `/signals` e `/roi` dei predictor configurati
2. Scarta le scommesse con EV sotto soglia (`min_ev`)
3. Rankinga per **score** = `EV × peso_sport × (1 + bonus se stagione calda)`
4. Alloca il budget con **Kelly frazionato** (cap per scommessa + no leva sul budget)
5. Stampa il report con `rich`

```
EV          = prob × quota − 1
kelly_full  = EV / (quota − 1)
stake       = budget × kelly_full × kelly_fraction   (con cap max_stake_fraction)
```

## Uso

```bash
python3 -m venv /home/egiabot/venvs/betting-agent
/home/egiabot/venvs/betting-agent/bin/pip install -r requirements.txt

# avvia prima le API dei predictor (porte 8001-8004), poi:
./start.sh
# oppure
/home/egiabot/venvs/betting-agent/bin/python -m betting_agent.main
```

## Configurazione (`config.yaml`)

| Campo | Significato |
|---|---|
| `budget` | budget settimanale totale (EUR) |
| `kelly_fraction` | frazione di Kelly (0.25 = prudente, 1.0 = aggressivo) |
| `max_stake_fraction` | cap stake per singola scommessa (frazione del budget) |
| `min_ev` | EV minimo per considerare una scommessa |
| `api_key` | header `X-API-Key` (o env `AGENT_API_KEY`); vuoto = auth off |
| `bonus_stagione_calda` | bonus allo score per sport in stagione calda |
| `predictors` | lista `{name, base_url, peso}` dei predictor da interrogare |

Il `peso` per sport riflette l'edge storico: più alto = più fiducia (es. mercati di nicchia
come la Serie B hanno bookmaker meno precisi → peso leggermente maggiore).

## Robustezza

- Un predictor **offline** o che risponde **503** (quote non disponibili) non blocca gli altri:
  viene segnalato nel report e semplicemente non contribuisce scommesse.
- Il budget non viene mai sforato: se la somma degli stake supera il budget, si ridimensiona
  proporzionalmente.

## Test

```bash
/home/egiabot/venvs/betting-agent/bin/python -m betting_agent.tests_engine   # motore (dati simulati)
/home/egiabot/venvs/betting-agent/bin/python -m betting_agent.tests_e2e      # end-to-end (server mock)
```

## Ecosistema

| Progetto | Ruolo | Porta |
|---|---|---|
| seriea / serieb / laliga2 / bundesliga2-predictor | sensori (predizioni + segnali) | API 8001–8004 |
| betting-core | libreria condivisa (modelli, API layer) | — |
| **betting-agent** | decisore centrale (questo) | — |
