# Liber Quiet Mono UI — Design

**Date:** 2026-10-23  
**Status:** implemented (chrome tokens live)  
**Extends:** ADR-0006 soft-premium shell (anatomy kept; Atelier olive chrome replaced)

## Goal

Product chrome that feels **minimal, rich, clear, and easy on the eyes** — quiet luxury via contrast and type, not olive/cream décor.

## Decision

**Quiet Mono** for Liber shell (`web/src/styles/tokens.css` + chrome washes):

| Token | Hex | Role |
|-------|-----|------|
| `--paper` / `--bg-app` | `#F7F7F5` | Cool neutral stage (not cream) |
| `--sheet` / `--surface` | `#FFFFFF` | Cards, composer |
| `--ink` | `#121212` | Primary text |
| `--muted` | `#6B6B6B` | Secondary text |
| `--primary` / `--accent` | `#1A1A1A` | CTA, brand mark, focus |
| `--on-primary` | `#FFFFFF` | Text/icons on primary fills |
| `--secondary` | `#ECECEB` | Soft wash / selected chip |
| `--foil` | `#8A8A86` | Hairline metal (not gold) |
| `--ok` | `#2F5D45` | Success only (not brand) |

Shadows tint from `--ink`, never olive. Body radials = faint gray, not sage.

## Out of scope

- Chart/report palettes (`atelier` / `editorial` / …) and deck theme packs — still Source/Settings driven.
- Dark mode.
- Typography swap (keep DM Sans + Crimson).

## Success

- Empty home reads as editorial desk, not green salon.
- Primary buttons readable (dark fill + white label).
- No hardcoded `#3f5210` / cream radials in product chrome CSS.
