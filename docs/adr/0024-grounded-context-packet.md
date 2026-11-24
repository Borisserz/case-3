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
- **Phase A (shipped 2026-11-24):** chat analysis + dialogue + evidence only; `render_chat_user_block`, `selection_manifest` on chat answers.
- **Phase B (shipped 2026-11-24):** `artifact_context.resolve_artifact_targets` fills `ContextPacket.artifact_targets` (`number_evidence=false`); `render_revise_user_block` / build prompts inject GCP-selected evidence; `chat_revise` uses precomputed targets when `TurnPlan.edit_act` + packet target; report/diagram/presentation builds persist `selection_manifest` and keep **canonical** full Source for `fact_ground`; TTG child steps inherit parent catalog hashes (`selection_manifest.hashes` or `source_catalog_hashes`).

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
- Negative: Phase B build/revise context is evidence-selected, not a full chain paste; reopen and some legacy paths may still use `format_thread`. KI/MEMORY distinguish chat vs build GCP.
- Related spec: `docs/superpowers/specs/2026-11-24-liber-grounded-context-packet-design.md`. Routing: ADR-0023. Chain and digits: ADR-0013, ADR-0015, ADR-0016, ADR-0018.