.DEFAULT_GOAL := help

PYTHON ?= python3
FILE ?= fixtures/smoke/01_temp_shares.txt

.PHONY: help setup run dry-run push-debug clean

help:
	@echo "  make setup | make run FILE=fixtures/smoke/01_temp_shares.txt | make dry-run | make push-debug"

setup:
	cd backend && $(PYTHON) -m pip install -e .
	docker compose build

run:
	cd backend && $(PYTHON) -m case3.cli run $(FILE) --format both

dry-run:
	cd backend && $(PYTHON) -m case3.cli run $(FILE) --format both --dry-run

push-debug:
	@stamp=$$(date -u +%Y%m%dT%H%M%SZ); \
	dest=debug-bundle/$$stamp; \
	mkdir -p $$dest/out $$dest/logs; \
	find backend/runs/out -type f \( -name '*.tex' -o -name '*.json' -o -name '*.txt' \) -exec cp -n {} $$dest/out/ \; 2>/dev/null || true; \
	find backend/runs/logs -type f \( -name '*.log' -o -name '*.json' -o -name '*.txt' \) -exec cp -n {} $$dest/logs/ \; 2>/dev/null || true; \
	git checkout -B debug/runs; \
	git add -f $$dest; \
	git commit -m "debug: $$stamp (tex+logs)" || true; \
	git push -u origin debug/runs

clean:
	rm -rf backend/runs/work/* backend/runs/out/* backend/runs/logs/* debug-bundle
	mkdir -p backend/runs/out backend/runs/logs backend/runs/work
	touch backend/runs/out/.gitkeep backend/runs/logs/.gitkeep backend/runs/work/.gitkeep
