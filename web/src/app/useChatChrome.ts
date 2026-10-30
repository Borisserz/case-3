/** Document title, stick-to-bottom chat scroll, composer autosize, last-report flag. */

import {
  useEffect,
  type Dispatch,
  type MutableRefObject,
  type RefObject,
  type SetStateAction,
} from "react";
import type { Msg, RunResult } from "../domain/liberTypes";

type Deps = {
  chatTitle: string | null;
  msgs: Msg[];
  chat: string;
  messagesRef: RefObject<HTMLDivElement | null>;
  bottomRef: RefObject<HTMLDivElement | null>;
  chatRef: RefObject<HTMLTextAreaElement | null>;
  stickBottom: MutableRefObject<boolean>;
  setHasStoredReport: Dispatch<SetStateAction<boolean>>;
};

export function useChatChrome({
  chatTitle,
  msgs,
  chat,
  messagesRef,
  bottomRef,
  chatRef,
  stickBottom,
  setHasStoredReport,
}: Deps) {
  useEffect(() => {
    document.title = chatTitle ? `${chatTitle} · Liber` : "Liber";
  }, [chatTitle]);

  useEffect(() => {
    const el = messagesRef.current;
    if (!el) return;
    const onScroll = () => {
      const gap = el.scrollHeight - el.scrollTop - el.clientHeight;
      stickBottom.current = gap < 96;
    };
    el.addEventListener("scroll", onScroll, { passive: true });
    return () => el.removeEventListener("scroll", onScroll);
  }, [messagesRef, stickBottom]);

  useEffect(() => {
    const jumpBottom = (smooth: boolean) => {
      const el = messagesRef.current;
      if (el) el.scrollTop = el.scrollHeight;
      bottomRef.current?.scrollIntoView({
        behavior: smooth ? "smooth" : "auto",
        block: "end",
      });
    };
    if (/preview=(artifact|deck)/.test(window.location.search)) {
      stickBottom.current = true;
      jumpBottom(false);
      const t1 = window.setTimeout(() => jumpBottom(false), 120);
      const t2 = window.setTimeout(() => jumpBottom(false), 480);
      return () => {
        window.clearTimeout(t1);
        window.clearTimeout(t2);
      };
    }
    if (!stickBottom.current) return;
    jumpBottom(true);
  }, [msgs, messagesRef, bottomRef, stickBottom]);

  useEffect(() => {
    const el = chatRef.current;
    if (!el) return;
    el.style.height = "0px";
    const next = Math.min(Math.max(el.scrollHeight, 44), 112);
    el.style.height = `${next}px`;
  }, [chat, chatRef]);

  useEffect(() => {
    try {
      const raw = sessionStorage.getItem("liber-last-report");
      if (!raw) {
        setHasStoredReport(false);
        return;
      }
      const result = JSON.parse(raw) as RunResult;
      setHasStoredReport(Boolean(result?.preview?.blocks?.length));
    } catch {
      setHasStoredReport(false);
    }
  }, [msgs, setHasStoredReport]);
}
