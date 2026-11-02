import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { buildRunFormData } from "./buildRunFormData";
import { DEFAULT_DECK_STYLE } from "../deckStyle";

describe("buildRunFormData", () => {
  it("posts document photo_mode and report formats", () => {
    const fd = buildRunFormData({
      file: null,
      draftSnap: null,
      chatTrim: "hello",
      intentText: "hello",
      photosSnapshot: [],
      forbidCharts: false,
      forbidImages: false,
      maxCharts: 2,
      maxImages: 2,
      maxDiagrams: 2,
      dryRun: true,
      workMode: "report",
      deckStyle: DEFAULT_DECK_STYLE,
    });
    assert.equal(fd.get("photo_mode"), "document");
    assert.equal(fd.get("formats"), "both");
    assert.equal(fd.get("dry_run"), "true");
    assert.equal(fd.get("source_text"), "hello");
    assert.equal(fd.get("output_mode"), "report");
  });

  it("zeros charts/images for diagram mode", () => {
    const fd = buildRunFormData({
      file: null,
      draftSnap: null,
      chatTrim: "flow",
      intentText: "flow",
      photosSnapshot: [],
      forbidCharts: false,
      forbidImages: false,
      maxCharts: 2,
      maxImages: 2,
      maxDiagrams: 1,
      dryRun: false,
      workMode: "diagram",
      deckStyle: DEFAULT_DECK_STYLE,
    });
    assert.equal(fd.get("max_charts"), "0");
    assert.equal(fd.get("max_images"), "0");
    assert.equal(fd.get("forbid_charts"), "true");
    assert.equal(fd.get("formats"), "none");
  });
});
