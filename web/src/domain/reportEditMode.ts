/** Preview edit-mode: document click-to-edit + session undo/redo. */

export type EditHistoryDesc = {
  canUndo: boolean;
  canRedo: boolean;
  depth: number;
  kind?: string | null;
  target?: string | null;
};

/** Show block edit affordances only while edit mode is on and a handler exists. */
export function blockEditVisible(
  editMode: boolean,
  hasHandler: boolean,
): boolean {
  return editMode && hasHandler;
}

/** Top «Редактировать» only when at least one editor is wired. */
export function reportEditToggleVisible(opts: {
  onEditFigure?: unknown;
  onEditImage?: unknown;
  onEditTable?: unknown;
  onEditParagraph?: unknown;
  onEditHeading?: unknown;
  onEditList?: unknown;
}): boolean {
  return Boolean(
    opts.onEditFigure ||
      opts.onEditImage ||
      opts.onEditTable ||
      opts.onEditParagraph ||
      opts.onEditHeading ||
      opts.onEditList,
  );
}

/** Hint under the top toggle. */
export function reportEditModeHint(editMode: boolean): string {
  return editMode
    ? "Клик по тексту · ⌘Z / ⌘⇧Z"
    : "Чтение · правки PDF/DOCX из того же Source";
}

/** Entering edit expands every section (empty collapse set). */
export function collapseSetForEditMode(editMode: boolean): Set<string> | null {
  return editMode ? new Set() : null;
}

/** Parse API ``undo`` object into bar enablement. */
export function parseEditHistory(
  undo: {
    kind?: string | null;
    target?: string | null;
    can_undo?: boolean;
    can_redo?: boolean;
    depth?: number;
  } | null | undefined,
): EditHistoryDesc {
  if (!undo) {
    return { canUndo: false, canRedo: false, depth: 0 };
  }
  const canUndo =
    typeof undo.can_undo === "boolean"
      ? undo.can_undo
      : Boolean(undo.kind);
  const canRedo = Boolean(undo.can_redo);
  const depth =
    typeof undo.depth === "number" && undo.depth >= 0
      ? undo.depth
      : canUndo
        ? 1
        : 0;
  return {
    canUndo,
    canRedo,
    depth,
    kind: undo.kind ?? null,
    target: undo.target ?? null,
  };
}

/** Toast «Отменить» only outside report edit mode and when undo is available. */
export function toastUndoVisible(
  editMode: boolean,
  history: EditHistoryDesc | null | undefined,
): boolean {
  if (editMode) return false;
  return Boolean(history?.canUndo);
}
