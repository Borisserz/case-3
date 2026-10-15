.DEFAULT_GOAL := help

PYTHON ?= python3

.PHONY: help setup run dry-run push-debug clean

help:
	@echo "  make setup"
	@echo "  make run FILE=notes.txt"
	@echo "  make dry-run FILE=notes.txt"
	@echo "  make push-debug"

setup:
	$(PYTHON) -m pip install -e .
	docker compose build

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
