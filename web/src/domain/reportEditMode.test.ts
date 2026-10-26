import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  blockEditVisible,
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
  });
});
