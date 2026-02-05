#!/bin/bash
set -e

echo "--- ENTRYPOINT INICIADO ---"
echo "--- AMBIENTE: $(uname -a) ---"
echo "--- DATA: $(date) ---"

# Garantir que a porta esteja definida, padrão 80
export PORT=${PORT:-80}
echo "--- PORTA DEFINIDA: $PORT ---"

# Iniciar Uvicorn
echo "--- INICIANDO UVICORN ---"
# Usamos exec para que o uvicorn assuma o PID 1 e receba sinais de parada corretamente
exec python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT
