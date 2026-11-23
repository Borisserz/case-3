import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { hideSourcePlaque, removeAttachedSource } from "./sourcePlaque.ts";

describe("hideSourcePlaque", () => {
  it("hides the chip and keeps the document", () => {
    const draft = { title: "regions.txt", text: "Минская 105 865,2" };
    const file = { name: "regions.txt" };
    const next = hideSourcePlaque({ sourceDraft: draft, file });
    assert.equal(next.plaqueDismissed, true);
    assert.equal(next.sourceDraft, draft);
    assert.equal(next.file, file);
  });

  it("removeAttachedSource honestly clears file and draft", () => {
    const next = removeAttachedSource();
    assert.equal(next.plaqueDismissed, false);
    assert.equal(next.sourceDraft, null);
    assert.equal(next.file, null);
  });
});
