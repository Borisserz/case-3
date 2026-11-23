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
