VENV := .venv
PY   := $(VENV)/bin/python
PIP  := $(VENV)/bin/pip

.PHONY: setup run ui test clean

setup:
	python3 -m venv $(VENV)
	$(PIP) install -U pip
	$(PIP) install -e ".[dev]"

run:
	$(VENV)/bin/medusacut "$(URL)" --out out

# Painel local — abre so em 127.0.0.1 (uso pessoal, nao exponha na rede).
ui:
	$(VENV)/bin/streamlit run src/medusacut/ui/app.py --server.address 127.0.0.1

test:
	$(PY) -m pytest -q

clean:
	rm -rf out .venv *.egg-info src/*.egg-info
