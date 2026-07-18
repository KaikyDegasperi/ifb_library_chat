#!/usr/bin/env sh
set -eu

docker compose config --quiet
docker compose up --build --detach --wait

docker compose exec -T api python -c \
  "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=5).read()"
docker compose exec -T frontend python -c \
  "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health', timeout=5).read()"

docker compose ps
echo "Containers da API e do frontend responderam aos health checks."
