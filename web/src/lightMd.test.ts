import assert from "node:assert/strict";
import { test } from "node:test";
import { renderLightMd, spaceAnswer } from "./lightMd";

test("a glued numbered conclusion becomes separate paragraphs", () => {
  const raw =
    "Выводы: план выполнен. 1. Период — январь. 2. Выполнение плана 112%.";
  const spaced = spaceAnswer(raw);
  assert.match(spaced, /\n\n1\. Период/);
  assert.match(spaced, /\n\n2\. Выполнение/);
  const html = renderLightMd(raw);
  assert.equal((html.match(/<p class="src-p">/g) || []).length, 3);
});

test("tables wrap in scrollable container and query highlight never touches HTML tags", () => {
  const md = "| Поле | Описание |\n| --- | --- |\n| table | строка class |\n";
  const html = renderLightMd(md, "table");
  assert.match(html, /<div class="msg-table-wrap"><table class="msg-table">/);
  assert.match(html, /<\/table><\/div>/);
  assert.match(html, /<mark class="src-hit">table<\/mark>/);
  // Attribute class="msg-table" must stay intact!
  assert.match(html, /class="msg-table"/);
});
