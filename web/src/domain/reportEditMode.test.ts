import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  blockEditVisible,
  collapseSetForEditMode,
  reportEditModeHint,
  reportEditToggleVisible,
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

  it("hint describes full-open edit desk", () => {
    assert.match(reportEditModeHint(true), /все блоки открыты/i);
    assert.match(reportEditModeHint(false), /Чтение/);
  });

  it("entering edit clears collapsed sections", () => {
    const cleared = collapseSetForEditMode(true);
    assert.ok(cleared);
    assert.equal(cleared!.size, 0);
    assert.equal(collapseSetForEditMode(false), null);
  });
});
