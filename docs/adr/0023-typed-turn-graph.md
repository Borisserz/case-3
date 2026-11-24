# ADR-0023: Typed Turn Graph

## Status
Accepted

## Date
2026-11-24

## Context
Routing was split across turn_route, chat_act, api caps, and pipeline. Wrong modes.

## Decision
One TurnPlan per message (plan_turn) before revise/build. Locked policies P4–P8 from the TTG spec.

## Consequences
- Positive: single SSOT for mode; multi-artifact steps; clarify for plaque+chart.
- Negative: resolve_turn is compatibility-only; tests must use plan_turn for clarify.