import assert from "node:assert/strict";
import { describe, it, beforeEach } from "node:test";
import {
  createFolder,
  deleteFolder,
  loadFolders,
  loadHistory,
  moveHistoryToFolder,
  pushHistory,
  togglePinHistory,
} from "./reportHistory";

const mem = new Map<string, string>();

beforeEach(() => {
  mem.clear();
  (globalThis as { sessionStorage?: Storage }).sessionStorage = {
    getItem: (k) => mem.get(k) ?? null,
    setItem: (k, v) => {
      mem.set(k, String(v));
    },
    removeItem: (k) => {
      mem.delete(k);
    },
    clear: () => mem.clear(),
    key: () => null,
    length: 0,
  };
});

describe("reportHistory folders + pin", () => {
  it("pins float to top", () => {
    pushHistory({
      id: "a",
      title: "A",
      runId: "a",
      savedAt: 1,
    });
    pushHistory({
      id: "b",
      title: "B",
      runId: "b",
      savedAt: 2,
    });
    togglePinHistory("a");
    const list = loadHistory();
    assert.equal(list[0].runId, "a");
    assert.equal(list[0].pinned, true);
  });

  it("create folder and move chat", () => {
    pushHistory({
      id: "x",
      title: "X",
      runId: "x",
      savedAt: 3,
    });
    const folders = createFolder("Клиенты");
    assert.equal(folders.length, 1);
    const moved = moveHistoryToFolder("x", folders[0].id);
    assert.equal(moved[0].folderId, folders[0].id);
    const after = deleteFolder(folders[0].id);
    assert.equal(after.folders.length, 0);
    assert.equal(loadHistory()[0].folderId, null);
    assert.equal(loadFolders().length, 0);
  });
});
