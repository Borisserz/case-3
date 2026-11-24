import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  attachmentsFromDraft,
  composerPlaques,
  dropSourcePart,
  ensureSourceParts,
  mergeSourcePack,
  replaceSourcePartText,
  sourcePackRejects,
} from "./sourcePack";

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

  it("gives each attached file and each snapshot its own plaque", () => {
    const packed = mergeSourcePack(
      mergeSourcePack(null, {
        title: "Поступления.md",
        text: "# Данные дашборда\nянварь",
        fileName: "Поступления.md",
      }),
      {
        title: "Брест.md",
        text: "# Данные дашборда\nбрест",
        fileName: "Брест.md",
      },
    );
    const plaques = composerPlaques(packed);
    assert.equal(plaques.length, 2);
    assert.equal(plaques[0].title, "Поступления.md");
    assert.equal(plaques[1].title, "Брест.md");
    assert.match(plaques[0].subtitle, /символ/);

    const left = dropSourcePart(packed, 1);
    assert.equal(left?.parts?.length, 1);
    assert.equal(left?.parts?.[0].name, "Поступления.md");
    assert.doesNotMatch(left?.text || "", /Брест/);
    assert.equal(dropSourcePart(left!, 0), null);
  });

  it("splits a glued snapshot pack so one screen can be removed", () => {
    const glued = {
      title: "2 документа",
      text: "===== Январь.md =====\n# Данные дашборда\nянварь\n\n===== Брест.md =====\n# Данные дашборда\nбрест",
      fileName: "Январь.md, Брест.md",
      viewMode: "text" as const,
    };
    assert.equal(composerPlaques(glued).length, 2);
    const kept = ensureSourceParts(dropSourcePart(glued, 0));
    assert.equal(kept?.parts?.length, 1);
    assert.match(kept?.text || "", /Брест\.md/);
    assert.doesNotMatch(kept?.text || "", /Январь\.md/);
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

  it("saves an edited markdown back into that plaque only", () => {
    const packed = mergeSourcePack(
      mergeSourcePack(null, {
        title: "отчёт.pdf",
        text: "| Регион | Факт |\n| --- | --- |\n| Минск | 120 |",
        fileName: "отчёт.pdf",
        viewMode: "document",
        ingestId: "ing_1",
      }),
      {
        title: "ещё.md",
        text: "не трогать",
        fileName: "ещё.md",
      },
    );
    const next = replaceSourcePartText(packed, 0, "| Регион | Факт |\n| --- | --- |\n| Минск | 90 |");
    const attachments = attachmentsFromDraft(next);
    assert.equal(attachments[0].sourceEdited, true);
    assert.match(attachments[0].text, /90/);
    assert.equal(attachments[1].text, "не трогать");
    assert.match(next.text, /Минск \| 90/);
    assert.doesNotMatch(next.text, /120/);
  });

  it("refuses a sixth document and keeps the five already attached", () => {
    let packed = null as ReturnType<typeof mergeSourcePack> | null;
    for (let i = 1; i <= 5; i += 1) {
      packed = mergeSourcePack(packed, {
        title: `док-${i}.md`,
        text: `текст ${i}`,
        fileName: `док-${i}.md`,
      });
    }
    assert.equal(sourcePackRejects(packed, { fileName: "док-6.md" }), true);
    assert.equal(sourcePackRejects(packed, { fileName: "док-1.md" }), false);
    const kept = mergeSourcePack(packed, {
      title: "док-6.md",
      text: "лишний",
      fileName: "док-6.md",
    });
    assert.equal(kept, packed);
    assert.match(kept?.text || "", /текст 1/);
    assert.doesNotMatch(kept?.text || "", /лишний/);
  });
});
