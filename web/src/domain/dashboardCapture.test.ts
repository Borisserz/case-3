import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  attachCaptureMarkdowns,
  captureOriginOk,
  captureWarning,
  documentsFromService,
  phrasePlan,
  phraseRoute,
  filesFromCapture,
  markdownDocName,
  viewerFrameUrl,
  CAPTURE_MESSAGE,
} from "./dashboardCapture.ts";

describe("viewerFrameUrl", () => {
  it("defaults to the local preview viewer", () => {
    assert.equal(viewerFrameUrl(""), "http://127.0.0.1:8040/viewer");
  });

  it("appends /viewer when only the origin is set", () => {
    assert.equal(
      viewerFrameUrl("http://127.0.0.1:8040/"),
      "http://127.0.0.1:8040/viewer",
    );
  });
});

describe("filesFromCapture", () => {
  it("keeps png and pdf payloads and drops the rest", () => {
    const files = filesFromCapture({
      type: CAPTURE_MESSAGE,
      files: [
        { name: "экран.png", ext: "png", data_b64: "abc" },
        { name: "Оплаты.pdf", ext: "pdf", data_b64: "def" },
        { name: "notes.txt", ext: "txt", data_b64: "nope" },
        { name: "empty.png", ext: "png", data_b64: "" },
      ],
    });
    assert.deepEqual(
      files.map((file) => file.name),
      ["экран.png", "Оплаты.pdf"],
    );
  });

  it("accepts a message only from the viewer origin", () => {
    const viewer = "http://127.0.0.1:8040/viewer";
    assert.equal(captureOriginOk("http://127.0.0.1:8040", viewer), true);
    assert.equal(captureOriginOk("http://evil.example", viewer), false);
  });
});

describe("phrasePlan", () => {
  it("keeps an open-url only when filters came back", () => {
    assert.equal(phrasePlan({ pull: false }), null);
    const plan = phrasePlan({
      pull: true,
      viewer: "http://127.0.0.1:8040/open?filters=%7B%7D",
      reply: "Сейчас открою.",
      filters: { Month: "Февраль" },
    });
    assert.equal(plan?.filters.Month, "Февраль");
    assert.equal(plan?.reply, "Сейчас открою.");
  });
});

describe("phraseRoute", () => {
  it("sends the message when the dashboard service fails", () => {
    assert.equal(phraseRoute(false, { detail: "нет списка фильтров" }), "send");
  });

  it("keeps a real filter miss and a real open", () => {
    assert.equal(
      phraseRoute(true, { pull: false, asked: true, reply: "Нет такого фильтра." }),
      "miss",
    );
    assert.equal(
      phraseRoute(true, {
        pull: true,
        viewer: "http://127.0.0.1:8040/open",
        reply: "Сейчас открою.",
        filters: { Month: "Март" },
      }),
      "open",
    );
    assert.equal(phraseRoute(true, { pull: false }), "send");
  });
});

describe("documentsFromService", () => {
  it("keeps the truncation warning with the table", () => {
    const docs = documentsFromService({
      documents: [
        {
          name: "Table.pdf",
          markdown: "| a |",
          warnings: ["Таблица обрезана: было 80×600, осталось 64×500."],
        },
      ],
    });
    assert.equal(docs.length, 1);
    assert.deepEqual(docs[0].warnings, [
      "Таблица обрезана: было 80×600, осталось 64×500.",
    ]);
    assert.equal(
      captureWarning(docs),
      "Таблица обрезана: было 80×600, осталось 64×500.",
    );
  });

  it("keeps named markdown from the capture route", () => {
    const docs = documentsFromService({
      documents: [
        { name: "screen.png", markdown: "# Экран" },
        { name: " ", markdown: "пустое имя" },
        { name: "Table.pdf", markdown: "  " },
      ],
    });
    assert.deepEqual(docs, [
      { name: "screen.png", markdown: "# Экран", warnings: [] },
    ]);
  });
});

describe("attachCaptureMarkdowns", () => {
  it("stores each png and pdf as its own named markdown", () => {
    const next = attachCaptureMarkdowns(null, [
      { name: "dashboard_20261121.png", markdown: "# Экран\n\nфильтр" },
      { name: "Оплаты_20261121.pdf", markdown: "| a |\n| --- |\n| 1 |" },
    ]);
    assert.equal(next?.parts?.length, 2);
    assert.equal(next?.parts?.[0].name, "dashboard_20261121.md");
    assert.equal(next?.parts?.[1].name, "Оплаты_20261121.md");
    assert.match(next?.text || "", /===== dashboard_20261121.md =====/);
    assert.match(next?.text || "", /===== Оплаты_20261121.md =====/);
    assert.equal(markdownDocName("Оплаты_20261121.pdf"), "Оплаты_20261121.md");
  });
});
