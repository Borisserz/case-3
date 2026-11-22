import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  ATTACHED_TOAST,
  SCREEN_READ_NOTE,
  SOURCE_LABEL,
  screenReadNote,
} from "./sourceCopy";

describe("source copy", () => {
  it("uses one name for the attached document", () => {
    assert.equal(SOURCE_LABEL, "Документ");
    assert.equal(SOURCE_LABEL.includes("Source"), false);
    assert.notEqual(SOURCE_LABEL, "Текст");
  });

  it("says the model could read numbers from the screen", () => {
    assert.equal(screenReadNote(true), SCREEN_READ_NOTE);
    assert.match(SCREEN_READ_NOTE, /экран/i);
    assert.match(SCREEN_READ_NOTE, /модель/i);
    assert.equal(screenReadNote(false), "");
  });

  it("names a successful attach", () => {
    assert.equal(ATTACHED_TOAST, "Данные прикреплены");
  });
});
