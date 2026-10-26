/** Preview edit-mode: one top toggle, then per-block «Изменить». */

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
}): boolean {
  return Boolean(
    opts.onEditFigure ||
      opts.onEditImage ||
      opts.onEditTable ||
      opts.onEditParagraph,
  );
}
