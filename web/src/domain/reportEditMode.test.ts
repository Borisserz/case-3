import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  blockEditVisible,
  collapseSetForEditMode,
  docsNeedRebuild,
  parseEditHistory,
  reportEditModeHint,
  reportEditToggleVisible,
  toastUndoVisible,
} from "./reportEditMode";

describe("reportEditMode", () => {
  it("hides block edits when mode is off", () => {
    assert.equal(blockEditVisible(false, true), false);
    assert.equal(blockEditVisible(true, true), true);
    assert.equal(blockEditVisible(true, false), false);
  });

  it("shows top toggle when any editor is wired", () => {
    assert.equal(reportEditToggleVisible({}), false);
    assert.equal(
      reportEditToggleVisible({ onEditParagraph: () => true }),
      true,
    );
    assert.equal(
      reportEditToggleVisible({ onEditFigure: () => true }),
      true,
    );
    assert.equal(
      reportEditToggleVisible({ onEditHeading: () => true }),
      true,
    );
    assert.equal(
      reportEditToggleVisible({ onEditList: () => true }),
      true,
    );
  });

  it("hint describes click-to-edit + deferred print", () => {
    assert.match(reportEditModeHint(true), /Готово/i);
    assert.match(reportEditModeHint(false), /Чтение/);
  });

  it("docsNeedRebuild when stack or redo branch has work", () => {
    assert.equal(docsNeedRebuild(null), false);
    assert.equal(
      docsNeedRebuild({ canUndo: false, canRedo: false, depth: 0 }),
      false,
    );
    assert.equal(
      docsNeedRebuild({ canUndo: true, canRedo: false, depth: 1 }),
      true,
    );
    assert.equal(
      docsNeedRebuild({ canUndo: false, canRedo: true, depth: 0 }),
      true,
    );
  });

  it("entering edit clears collapsed sections", () => {
    const cleared = collapseSetForEditMode(true);
    assert.ok(cleared);
    assert.equal(cleared!.size, 0);
    assert.equal(collapseSetForEditMode(false), null);
  });

  it("parses undo stack descriptor", () => {
    assert.deepEqual(parseEditHistory(null), {
      canUndo: false,
      canRedo: false,
      depth: 0,
    });
    assert.deepEqual(
      parseEditHistory({
        kind: "paragraph",
        target: "1",
        can_undo: true,
        can_redo: false,
        depth: 2,
      }),
      {
        canUndo: true,
        canRedo: false,
        depth: 2,
        kind: "paragraph",
        target: "1",
      },
    );
    assert.equal(
      parseEditHistory({ can_undo: false, can_redo: true, depth: 0 }).canRedo,
      true,
    );
    // Legacy one-slot shape
    assert.equal(parseEditHistory({ kind: "chart", target: "x" }).canUndo, true);
  });

  it("hides toast undo while report edit mode is on", () => {
    assert.equal(
      toastUndoVisible(true, { canUndo: true, canRedo: false, depth: 1 }),
      false,
    );
    assert.equal(
      toastUndoVisible(false, { canUndo: true, canRedo: false, depth: 1 }),
      true,
    );
    assert.equal(toastUndoVisible(false, { canUndo: false, canRedo: true, depth: 0 }), false);
  });
});
