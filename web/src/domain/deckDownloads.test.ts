import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { deckDownloadLinks } from "./deckDownloads";

describe("deckDownloadLinks", () => {
  it("returns PPTX then deck PDF", () => {
    const links = deckDownloadLinks({
      pptx: "/p.pptx",
      deck_pdf: "/d.pdf",
      pdf: "/report.pdf",
    });
    assert.deepEqual(
      links.map((l) => l.kind),
      ["pptx", "deck_pdf"],
    );
    assert.equal(links[1]?.label, "PDF");
  });

  it("marks stale during deferred flush", () => {
    const links = deckDownloadLinks(
      { pptx: "/p.pptx" },
      { stale: true },
    );
    assert.equal(links[0]?.stale, true);
    assert.match(links[0]?.label || "", /устарел/i);
  });
});
