# ADR-0025: The desk is Inspectra, in tax-desk green

## Status
Accepted

## Date
2026-11-24

## Context
The product the colleague sees was still named Liber, in Quiet Mono (near-black buttons). He asked for a clearer name, a greener desk, and fewer buttons that repeat the composer. He also asked that a dashboard snapshot not land as a file the user downloads by accident. The reference green is the «Войти» button on the tax-ministry login: `#307060`.

## Decision
The user-facing name is Inspectra: tab title, sidebar, help, chat identity prompts, and the model’s spoken name. Repo package stays `case3`. CSS classes stay `liber-*`. Hooks stay `useLiberRun` and the rest.

The desk field is the login page `#f5fbf7`: shell, sidebar, and chat column. White stays on fields (composer, off pills, cards). Filled actions use `#307060`, hover `#265e4e`. Text links such as «Выбрать данные» use the login blue `#1682e9`. Report and deck palettes (editorial, ocean, sunset, mono, atelier, and the eight packs) are unchanged.

The empty hero no longer offers «Выбрать дашборд Stimulsoft» or «Загрузить документ». Attach stays on the composer paperclip and «Выбрать данные».

A dashboard capture writes PNG/PDF into a temp directory (`inspectra-shot-`) and deletes it before the API returns markdown. The JSON has no path and no file bytes.

## Alternatives Considered

### Rename every identifier and class
- Pros: one word in the repo.
- Cons: a wide, risky rewrite of hooks, tests, and CSS.
- Rejected because the colleague sees the product name, not the class prefix.

### Keep Quiet Mono and only tint the send button
- Pros: smaller CSS diff.
- Cons: mode pills stayed black, so the desk still read as ink.
- Rejected because the active pill and the send button are the green he pointed at.

## Consequences
- Positive: the open desk matches the name and the login green. The raw snapshot is not a download from our API.
- Negative / follow-ups: if the Stimulsoft viewer itself saves `/exports/` into the browser, that file is outside this API. Mode-plaque lock and dropping Docker are separate and not part of this decision.
