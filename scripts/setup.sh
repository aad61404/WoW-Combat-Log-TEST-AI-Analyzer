#!/bin/bash
set -euo pipefail

project_root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$project_root"

if ! command -v uv >/dev/null; then
    echo "Install uv first: brew install uv" >&2
    exit 1
fi
if [ ! -x .venv/bin/python ]; then
    uv venv .venv --python 3.13
fi
uv pip sync --python .venv/bin/python apps/api/requirements-dev.lock
bash scripts/npm.sh ci

if [ ! -f .env ]; then
    cp .env.example .env
    chmod 600 .env
fi
if [ ! -f apps/web/.env.local ]; then
    printf 'NEXT_PUBLIC_API_URL=http://localhost:8000\n' > apps/web/.env.local
fi
echo "Environment ready. Run 'make dev' to start both services."
