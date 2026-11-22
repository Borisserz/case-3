import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { redoChord, undoChord } from "./undoChord";

describe("undo chords", () => {
  it("uses Ctrl on Windows and the command key on a Mac", () => {
    assert.equal(undoChord("Win32"), "Ctrl+Z");
    assert.equal(redoChord("Win32"), "Ctrl+Shift+Z");
    assert.match(undoChord("MacIntel"), /⌘Z/);
    assert.equal(undoChord("Linux x86_64"), "Ctrl+Z");
  });
});
