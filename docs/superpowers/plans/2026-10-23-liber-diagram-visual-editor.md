# Liber visual diagram editor — Plan

> Spec: `docs/superpowers/specs/2026-10-23-liber-diagram-visual-editor-design.md`

## Files

| File | Role |
|------|------|
| `web/src/diagramIr.ts` | Types + parse/serialize flowchart Mermaid |
| `web/src/diagramIr.test.ts` | Unit tests |
| `web/src/DiagramVisualEditor.tsx` | Modal React Flow + inspector |
| `web/src/DiagramPane.tsx` | Open visual editor on «Изменить» |
| `web/package.json` | `@xyflow/react` |

## Tasks

1. TDD parse/serialize round-trip  
2. Install xyflow · visual editor UI  
3. Wire pane · fallback if parse fails  
4. Verify tests + manual smoke  
