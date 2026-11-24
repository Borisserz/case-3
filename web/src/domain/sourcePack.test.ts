import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { attachmentsFromDraft, mergeSourcePack } from "./sourcePack";

describe("sourcePack", () => {
  it("preserves per-document preview metadata when merging multiple files", () => {
    const pdf = mergeSourcePack(null, {
      title: "отчёт.pdf",
      text: "Выручка 120",
      fileName: "отчёт.pdf",
      viewMode: "document",
      previewUrl: "/api/source/files/ing_1/preview",
      originalUrl: "/api/source/files/ing_1/original",
      ingestId: "ing_1",
      format: "pdf",
    });
    const combined = mergeSourcePack(pdf, {
      title: "таблица.md",
      text: "| А | Б |\n| --- | --- |\n| 1 | 2 |",
      fileName: "таблица.md",
      viewMode: "text",
    });

    const attachments = attachmentsFromDraft(combined);
    assert.equal(attachments.length, 2);
    assert.equal(attachments[0].fileName, "отчёт.pdf");
    assert.equal(attachments[0].viewMode, "document");
    assert.equal(attachments[0].previewUrl, "/api/source/files/ing_1/preview");
    assert.equal(attachments[1].fileName, "таблица.md");
    assert.equal(attachments[1].viewMode, "text");
    assert.match(attachments[1].text, /\| 1 \| 2 \|/);
  });

  it("wraps a single draft cleanly in attachmentsFromDraft", () => {
    const single = attachmentsFromDraft({
      title: "notes.txt",
      text: "Текст заметки",
      fileName: "notes.txt",
      viewMode: "text",
    });
    assert.equal(single.length, 1);
    assert.equal(single[0].title, "notes.txt");
    assert.equal(single[0].text, "Текст заметки");
  });
});
