/** Preview edit-mode: one top toggle opens full inline desk. */

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
    ? "Режим правки — все блоки открыты: текст, заголовки, списки, графики, фото, таблицы"
    : "Чтение · правки PDF/DOCX из того же Source";
}

/** Entering edit expands every section (empty collapse set). */
export function collapseSetForEditMode(editMode: boolean): Set<string> | null {
  return editMode ? new Set() : null;
}
