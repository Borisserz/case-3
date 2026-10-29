# Liber diagram repair + premium shell — Plan

> **For agentic workers:** spec `docs/superpowers/specs/2026-10-23-liber-diagram-repair-premium-design.md`

**Goal:** Dual-pass Mermaid in `output_mode=diagram` + premium DiagramPane.

## Done in this pass

1. `prompt/diagram_repair.md` + `src/case3/diagram_repair.py` + tests
2. `pipeline.py` stage `diagram_repair` when mode=diagram
3. Anti-slop in `prompt/system_tex.md`
4. Premium `DiagramPane` / `DiagramChatCard` / CSS
5. Stage labels + thinking phrases

## Verify

```bash
.venv/bin/python -m pytest tests/test_diagram_repair.py tests/test_diagrams.py tests/test_output_mode_diagram.py -q
cd web && npm test -- --run liberRunHelpers  # if configured
```

Manual: Liber → pill Схема → Source with branches → expect non-linear Mermaid + premium pane.
