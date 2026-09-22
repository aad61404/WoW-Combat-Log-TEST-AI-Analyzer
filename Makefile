.PHONY: setup dev api web test check e2e

setup:
	bash scripts/setup.sh

dev:
	$(MAKE) -j2 api web

api:
	.venv/bin/python -m uvicorn app.main:app --app-dir apps/api --host 127.0.0.1 --port 8000 --reload --reload-dir apps/api/app

web:
	bash scripts/npm.sh run dev -- --hostname 127.0.0.1 --port 3000

test:
	.venv/bin/python -m pytest -c apps/api/pyproject.toml apps/api/tests -q

check: test
	bash scripts/npm.sh run lint
	bash scripts/npm.sh run build

e2e:
	bash scripts/npm.sh run test:e2e
