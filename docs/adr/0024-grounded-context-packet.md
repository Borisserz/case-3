# ADR-0024: Grounded Context Packet (GCP)

## Status
Accepted

## Date
2026-11-24

## Context
After [ADR-0023](0023-typed-turn-graph.md), routing is one `TurnPlan` per message. Chat context was still ad hoc: `focus_source` could drop a second document, `_clip_source` lost table middles, dialogue was pasted as «не Source» without retrieval, inline charts rebuilt memory separately, and compare requests did not get equal source quotas. Product needs deterministic evidence before any chat LLM call, with an inspectable manifest.

## Decision
- Introduce **Grounded Context Packet** (`gcp-v1`) as a library layer **after** TTG and source restore (including `## Производные`), **before** chat LLM and inline chart/diagram generation.
- `build_context_packet` in `context_packet.py` + selection in `context_select.py` assemble catalog, scored evidence chunks, dialogue excerpts, coverage, and `selection_manifest`.
- Chat user prompt is `render_chat_user_block(packet)` passed as `context_block` to `try_chat_answer` and inline visuals. Prose and chart/diagram share the same packet evidence.
- Persist `meta["selection_manifest"]` on every chat answer path (`pipeline._finish_chat_answer`).
- Dialogue lane items always have `number_evidence=false`. Historical user stems stay ADR-0015/0016 bindings only. `fact_ground` on new files is unchanged.
- Compare or «оба документа» sets equal `per_source_quota`; explicit single-doc focus omits others with `explicit_focus`.
- Phase A scope: chat analysis + dialogue + evidence only. Build/revise packet renderers and `artifact_context` are Phase B (not required for this ADR).

## Alternatives Considered

### Enlarge `prior_block` / full chain every turn
- Pros: simple.
- Cons: presence ≠ relevance; crowding.
- Rejected.

### RAG / second LLM for selection
- Pros: looser phrasing.
- Cons: extra failure mode, cost, violates P3 in spec.
- Rejected for v1.

### Prompt rewrite without selection layer
- Pros: fast.
- Cons: wrong chunks remain wrong.
- Rejected.

## Consequences
- Positive: one inspectable package per chat turn; named doc and compare probes behave; route projection survives in prompt; manifest in `meta.json` for debug.
- Negative: build paths still use legacy context until Phase B; KI/MEMORY must distinguish chat GCP from old `format_thread` on assemblies.
- Related spec: `docs/superpowers/specs/2026-11-24-liber-grounded-context-packet-design.md`. Routing: ADR-0023. Chain and digits: ADR-0013, ADR-0015, ADR-0016, ADR-0018.