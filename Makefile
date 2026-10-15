.DEFAULT_GOAL := help

PYTHON ?= python3
FILE ?= notes.txt

.PHONY: help setup run dry-run push-debug clean

help:
	@echo "  make setup | make run FILE=notes.txt | make dry-run | make push-debug"

setup:
	$(PYTHON) -m pip install -e .
	docker compose build

run:
	$(PYTHON) -m case3.cli run $(FILE) --format both

dry-run:
	$(PYTHON) -m case3.cli run $(FILE) --format both --dry-run

push-debug:
	@stamp=$$(date -u +%Y%m%dT%H%M%SZ); \
	dest=debug-bundle/$$stamp; \
	mkdir -p $$dest/out $$dest/logs; \
	find out -type f \( -name '*.tex' -o -name '*.json' -o -name '*.txt' \) -exec cp -n {} $$dest/out/ \; 2>/dev/null || true; \
	find logs -type f \( -name '*.log' -o -name '*.json' -o -name '*.txt' \) -exec cp -n {} $$dest/logs/ \; 2>/dev/null || true; \
	git checkout -B debug/runs; \
	git add -f $$dest; \
	git commit -m "debug: $$stamp (tex+logs)" || true; \
	git push -u origin debug/runs

clean:
	rm -rf work/* out/* logs/* debug-bundle
	mkdir -p out logs work
	touch out/.gitkeep logs/.gitkeep
