.PHONY: install update-data rebuild rebuild-all validate app test lint format typecheck clean help

PYTHON := python3
VENV := .venv
VENV_PYTHON := $(VENV)/bin/python
VENV_PIP := $(VENV)/bin/pip

help:
	@echo ""
	@echo "FourthandStats — available commands:"
	@echo ""
	@echo "  make install       Create venv and install all dependencies"
	@echo "  make update-data   Download latest NFL data (current season)"
	@echo "  make rebuild       Rebuild all derived metric tables"
	@echo "  make rebuild-all   Re-download data + rebuild + validate"
	@echo "  make validate      Run data quality checks"
	@echo "  make app           Launch the Streamlit app"
	@echo "  make test          Run the test suite"
	@echo "  make lint          Run ruff linter"
	@echo "  make format        Run black formatter"
	@echo "  make typecheck     Run mypy type checker"
	@echo "  make clean         Remove __pycache__ and .pytest_cache"
	@echo ""

install:
	$(PYTHON) -m venv $(VENV)
	$(VENV_PIP) install --upgrade pip
	$(VENV_PIP) install -r requirements-dev.txt
	@echo ""
	@echo "✓ Virtual environment ready."
	@echo "  Activate with: source .venv/bin/activate"

update-data:
	$(VENV_PYTHON) scripts/update_data.py --current-season

rebuild:
	$(VENV_PYTHON) scripts/rebuild_metrics.py

rebuild-all:
	$(VENV_PYTHON) scripts/rebuild_all.py

validate:
	$(VENV_PYTHON) scripts/validate_data.py

app:
	$(VENV_PYTHON) -m streamlit run app.py

test:
	$(VENV_PYTHON) -m pytest tests/ -v

lint:
	$(VENV_PYTHON) -m ruff check .

format:
	$(VENV_PYTHON) -m black .

typecheck:
	$(VENV_PYTHON) -m mypy src/

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	@echo "✓ Caches cleaned."
