#!/usr/bin/env bash
# Abre el juego usando el entorno virtual si existe (.venv aquí o en la carpeta de arriba).
cd "$(dirname "$0")"
PY=python3
for v in .venv ../.venv; do
  if [ -x "$v/bin/python" ]; then PY="$v/bin/python"; break; fi
done
exec "$PY" jugar.py "$@"
