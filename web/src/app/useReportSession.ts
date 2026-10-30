/** Restore last report / clear desk for a new report. */

import type { Dispatch, RefObject, SetStateAction } from "react";
import {
  reportReadyText,
  reportTitle,
  uid,
} from "../domain/runHelpers";
import type { Msg, RunResult, SourceDraft } from "../domain/liberTypes";
import type { ActiveArtifact } from "../ArtifactRail";
import type { EditError } from "./useLiberEdits";

type Deps = {
  setMsgs: Dispatch<SetStateAction<Msg[]>>;
  setChatTitle: Dispatch<SetStateAction<string | null>>;
  setChat: Dispatch<SetStateAction<string>>;
  setFile: Dispatch<SetStateAction<File | null>>;
  setSourceDraft: Dispatch<SetStateAction<SourceDraft | null>>;
  setAttachPhotos: Dispatch<SetStateAction<File[]>>;
  setRailExiting: Dispatch<SetStateAction<boolean>>;
  setActiveArtifact: Dispatch<SetStateAction<ActiveArtifact | null>>;
  setPlaqueDismissed: Dispatch<SetStateAction<boolean>>;
  setEditError: Dispatch<SetStateAction<EditError>>;
  chatRef: RefObject<HTMLTextAreaElement | null>;
};

export function useReportSession({
  setMsgs,
  setChatTitle,
  setChat,
  setFile,
  setSourceDraft,
  setAttachPhotos,
  setRailExiting,
  setActiveArtifact,
  setPlaqueDismissed,
  setEditError,
  chatRef,
}: Deps) {
  function restoreLastReport() {
    try {
      const raw = sessionStorage.getItem("liber-last-report");
      if (!raw) return;
      const result = JSON.parse(raw) as RunResult;
      if (!result?.preview?.blocks?.length) return;
      const id = uid();
      setChatTitle(reportTitle(result));
      setMsgs([
        {
          id,
          role: "bot",
          text: reportReadyText(result),
          result,
        },
      ]);
    } catch {
      /* ignore */
    }
  }

  function startNewReport() {
    setMsgs([]);
    setChatTitle(null);
    setChat("");
    setFile(null);
    setSourceDraft(null);
    setAttachPhotos([]);
    setRailExiting(false);
    setActiveArtifact(null);
    setPlaqueDismissed(false);
    setEditError(null);
    chatRef.current?.focus();
  }

  return { restoreLastReport, startNewReport };
}
