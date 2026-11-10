/** Which slide to show after a deck undo/redo.

`target` is the slide id stored with the snapshot. Several ids are joined
with commas when one patch touched more than one slide; the first is enough.
*/

export function slideIndexForUndoTarget(
  slides: { id?: string }[] | null | undefined,
  target: string | null | undefined,
): number {
  const id = (target || "").split(",")[0]?.trim() || "";
  if (!id || !slides?.length) return -1;
  return slides.findIndex((s) => s.id === id);
}
