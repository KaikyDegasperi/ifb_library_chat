#!/usr/bin/env bash

set -Eeuo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
venv_dir="${project_dir}/.venv"

if [[ ! -x "${venv_dir}/bin/uvicorn" || ! -x "${venv_dir}/bin/streamlit" ]]; then
    echo "Dependências ausentes. Execute 'uv sync --locked' na raiz do projeto." >&2
    exit 1
fi

cd "${project_dir}"

"${venv_dir}/bin/uvicorn" app.main:app \
    --host 127.0.0.1 \
    --port "${API_PORT:-8000}" \
    --reload &
api_pid=$!

cleanup() {
    kill "${api_pid}" 2>/dev/null || true
    wait "${api_pid}" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

export API_BASE_URL="${API_BASE_URL:-http://127.0.0.1:${API_PORT:-8000}}"

echo "API:       ${API_BASE_URL}"
echo "Interface: http://localhost:${STREAMLIT_PORT:-8501}"

"${venv_dir}/bin/streamlit" run frontend/app.py \
    --server.address 127.0.0.1 \
    --server.port "${STREAMLIT_PORT:-8501}" \
    --server.headless true

