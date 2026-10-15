.DEFAULT_GOAL := help

IMAGE := case-3:tex
PYTHON ?= python3

.PHONY: help build-image install test dry-run run render-tex push-debug clean

help:
	@echo "case-3 — text/images → LaTeX (Qwen) → PDF/DOCX"
	@echo ""
	@echo "  make build-image     Docker TeX image"
	@echo "  make install         pip install -e ."
	@echo "  make test            unit tests"
	@echo "  make dry-run         pipeline without LLM (demo job)"
	@echo "  make run JOB=...     full pipeline (needs VISION_API_BASE_URL)"
	@echo "  make push-debug      push out/+logs/ to debug/runs"
	@echo "  make clean           wipe work/ out/ logs/ artifacts"

build-image:
	docker compose build

install:
	$(PYTHON) -m pip install -e ".[dev]" 2>/dev/null || $(PYTHON) -m pip install -e . -r requirements.txt
	$(PYTHON) -m pip install pytest -q

test:
	$(PYTHON) -m pytest -q

JOB ?= in/jobs/demo

dry-run:
	$(PYTHON) -m case3.cli run $(JOB) --format both --dry-run

run:
	$(PYTHON) -m case3.cli run $(JOB) --format both

FILE ?= in/example.tex

render-tex:
	./bin/case-3 both $(FILE)

push-debug:
	bash scripts/push-debug.sh

clean:
	rm -rf work/* out/* logs/* debug-bundle
	mkdir -p out logs work
	touch out/.gitkeep logs/.gitkeep
