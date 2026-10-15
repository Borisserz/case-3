.DEFAULT_GOAL := help

PYTHON ?= python3

.PHONY: help setup test dry-run run push-debug clean

help:
	@echo "case-3 — text → LaTeX → PDF/DOCX"
	@echo "  make setup              pip + docker image"
	@echo "  make run FILE=notes.txt"
	@echo "  make dry-run FILE=notes.txt"
	@echo "  make push-debug"
	@echo "  make test"

setup:
	$(PYTHON) -m pip install -e . -r requirements.txt
	docker compose build

test:
	$(PYTHON) -m pytest -q

FILE ?= notes.txt

run:
	$(PYTHON) -m case3.cli run $(FILE) --format both

dry-run:
	$(PYTHON) -m case3.cli run $(FILE) --format both --dry-run

push-debug:
	bash scripts/push-debug.sh

clean:
	rm -rf work/* out/* logs/* debug-bundle
	mkdir -p out logs work
	touch out/.gitkeep logs/.gitkeep
