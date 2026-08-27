.PHONY: install test run

# Create an isolated venv and install dev deps (uv preferred, falls back to pip)
install:
	uv venv .venv && uv pip install -p .venv/Scripts/python.exe -r requirements-dev.txt || \
	python -m venv .venv && .venv/Scripts/python -m pip install -r requirements-dev.txt

# Run the mock-based test suite (no live keys / GPU / network needed)
test:
	.venv/Scripts/python -m pytest tests/ -q

# Boot the full stack (backend + frontend + redis)
run:
	docker compose up --build
