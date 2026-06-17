VENV := .venv
PY   := $(VENV)/bin/python
PIP  := $(VENV)/bin/pip

.PHONY: setup run test clean

setup:
	python3 -m venv $(VENV)
	$(PIP) install -U pip
	$(PIP) install -e ".[dev]"

run:
	$(VENV)/bin/medusacut "$(URL)" --out out

test:
	$(PY) -m pytest -q

clean:
	rm -rf out .venv *.egg-info src/*.egg-info
