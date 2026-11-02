#!/bin/bash
set -e

VENV="/home/egiabot/venvs/betting-agent"
PROJECT="/home/egiabot/PROJECT/betting-agent"

source "$VENV/bin/activate"

echo "📊 Betting Agent — report settimanale"
echo "   (assicurati che le API dei predictor siano attive sulle porte 8001-8004)"
cd "$PROJECT"
python -m betting_agent.main "$@"
