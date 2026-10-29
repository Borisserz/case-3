/** Paste-long-text + file/photo ingest + drop for Liber composer. */

import {
  useCallback,
  type Dispatch,
  type DragEvent,
  type SetStateAction,
} from "react";
import type { ActiveArtifact } from "../ArtifactRail";
import { LONG_TEXT_CHARS } from "../domain/liberConstants";
import type { SourceDraft } from "../domain/liberTypes";
import { readTextFile } from "../domain/runHelpers";

type Deps = {
  setFile: Dispatch<SetStateAction<File | null>>;
  setSourceDraft: Dispatch<SetStateAction<SourceDraft | null>>;
  setPlaqueDismissed: Dispatch<SetStateAction<boolean>>;
  setDeckApplyHint: Dispatch<SetStateAction<string | null>>;
  setActiveArtifact: Dispatch<SetStateAction<ActiveArtifact | null>>;
  setAttachPhotos: Dispatch<SetStateAction<File[]>>;
  setForbidImages: Dispatch<SetStateAction<boolean>>;
  setMaxImages: Dispatch<SetStateAction<number>>;
  setDrag: Dispatch<SetStateAction<boolean>>;
  showToast: (message: string, ms?: number) => void;
};

export function useSourceIngest({
  setFile,
  setSourceDraft,
  setPlaqueDismissed,
  setDeckApplyHint,
  setActiveArtifact,
  setAttachPhotos,
  setForbidImages,
  setMaxImages,
  setDrag,
  showToast,
}: Deps) {
  const capturePastedSource = useCallback(
    (text: string) => {
      const trimmed = text.trim();
      if (trimmed.length <= LONG_TEXT_CHARS) return false;
      const draft = {
        title: "Текст",
        text: trimmed,
      };
      setFile(null);
      setSourceDraft(draft);
      setPlaqueDismissed(false);
      setDeckApplyHint(null);
      setActiveArtifact({
        kind: "source",
        tab: "source",
        title: draft.title,
        text: draft.text,
      });
      return true;
    },
    [
      setFile,
      setSourceDraft,
      setPlaqueDismissed,
      setDeckApplyHint,
      setActiveArtifact,
    ],
  );

  const ingestFiles = useCallback(
    (list: FileList | File[]) => {
      const arr = Array.from(list);
      for (const f of arr) {
        if (
          /\.(txt|md)$/i.test(f.name) ||
          f.type === "text/plain" ||
          f.type === "text/markdown"
        ) {
          setFile(f);
          setPlaqueDismissed(false);
          setDeckApplyHint(null);
          void (async () => {
            try {
              const text = await readTextFile(f);
              const draft = {
                title: f.name,
                text,
                fileName: f.name,
              };
              setSourceDraft(draft);
              setActiveArtifact({
                kind: "source",
                tab: "source",
                title: draft.title,
                text: draft.text,
                fileName: draft.fileName,
              });
            } catch (err) {
              showToast(
                err instanceof Error
                  ? err.message
                  : "Не удалось прочитать файл",
              );
            }
          })();
          continue;
        }
        if (/^image\//.test(f.type) || /\.(png|jpe?g)$/i.test(f.name)) {
          setAttachPhotos((prev) => [...prev, f].slice(0, 2));
          setForbidImages(false);
          setMaxImages((n) => Math.max(n, 2));
        }
      }
    },
    [
      setFile,
      setPlaqueDismissed,
      setDeckApplyHint,
      setSourceDraft,
      setActiveArtifact,
      setAttachPhotos,
      setForbidImages,
      setMaxImages,
      showToast,
    ],
  );

  const onDrop = useCallback(
    (e: DragEvent) => {
      e.preventDefault();
      setDrag(false);
      if (e.dataTransfer.files?.length) ingestFiles(e.dataTransfer.files);
    },
    [ingestFiles, setDrag],
  );

  return { capturePastedSource, ingestFiles, onDrop };
}
