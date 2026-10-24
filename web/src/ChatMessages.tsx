/** Liber chat transcript — Julius column DNA (user panel + document bot). */

import { AnimatePresence, motion } from "framer-motion";
import { ArtifactCard } from "./ArtifactCard";
import { ContextPlaque } from "./ContextPlaque";
import { EmptyState } from "./EmptyState";
import { IconCopy, IconLiberMark } from "./icons";
import { LONG_TEXT_CHARS } from "./liberConstants";
import type { LiberWorkMode } from "./liberModes";
import type { Msg, RunResult, SourceAttachment } from "./liberTypes";
import { reportThumb, reportTitle } from "./liberRunHelpers";
import { MsgMarkdown } from "./lightMd";
import { ReportPending } from "./ReportView";
import { ThinkingFold } from "./ThinkingFold";

type Props = {
  msgs: Msg[];
  reduceMotion: boolean | null;
  hasStoredReport: boolean;
  /** Julius-style session rename — chat column only (not sidebar). */
  sessionTitle?: string | null;
  thinkingLabel?: string;
  workMode?: LiberWorkMode;
  downloadsPulseMsgId: string | null;
  messagesRef: React.RefObject<HTMLDivElement | null>;
  bottomRef: React.RefObject<HTMLDivElement | null>;
  onRestore: () => void;
  onOpenSource: (draft: SourceAttachment) => void;
  onOpenIntent: (text: string) => void;
  onOpenReport: (msgId: string, result: RunResult) => void;
  onOpenDiagram: (msgId: string, result: RunResult, diagramId: string) => void;
  onMakePresentation: (msgId: string, result: RunResult) => void;
  onOpenPresentation: (msgId: string, result: RunResult) => void;
  onOpenDeckSlides: (msgId: string, result: RunResult) => void;
  onDeckStyle?: () => void;
};

export function ChatMessages({
  msgs,
  reduceMotion,
  hasStoredReport,
  sessionTitle = null,
  thinkingLabel,
  workMode = null,
  downloadsPulseMsgId,
  messagesRef,
  bottomRef,
  onRestore,
  onOpenSource,
  onOpenIntent,
  onOpenReport,
  onOpenDiagram,
  onMakePresentation: _onMakePresentation,
  onOpenPresentation,
  onOpenDeckSlides,
  onDeckStyle,
}: Props) {
  const showSessionHead = Boolean(sessionTitle && msgs.length > 0);
  return (
    <div className="messages" ref={messagesRef}>
      {showSessionHead ? (
        <header className="chat-session-head">
          <h1 className="chat-session-title" title={sessionTitle || undefined}>
            {sessionTitle}
          </h1>
        </header>
      ) : null}
      <AnimatePresence initial={false}>
        {msgs.length === 0 &&
          !/preview=(artifact|deck|deck-busy|flow)/.test(window.location.search) && (
            <EmptyState
              hasStoredReport={hasStoredReport}
              onRestore={onRestore}
              workMode={workMode}
            />
          )}
        {msgs.map((m, mi) => {
          const hasArtifact =
            m.role === "bot" &&
            Boolean(
              m.result?.preview?.blocks?.length ||
                m.result?.downloads?.pdf ||
                m.result?.downloads?.pptx ||
                m.result?.downloads?.deck_pdf ||
                (m.result?.diagrams && m.result.diagrams.length > 0),
            );
          const slidesLive =
            m.role === "bot" &&
            (Boolean(m.pending && m.pendingStage?.startsWith("slides_")) ||
              m.result?.slides_status === "running" ||
              m.result?.slides_status === "queued");
          const userLong =
            m.role === "user" &&
            !m.attachment &&
            m.text.length > LONG_TEXT_CHARS;
          const userCollapseIntent =
            m.role === "user" && m.text.length > 140 && !m.attachment;
          return (
            <motion.div
              key={m.id}
              className={`msg ${m.role}${hasArtifact ? " has-artifact" : ""}`}
              initial={reduceMotion ? false : { opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{
                duration: 0.35,
                delay: Math.min(mi * 0.03, 0.18),
                ease: [0.22, 1, 0.36, 1],
              }}
            >
              {m.role === "user" ? (
                <>
                  {m.attachment ? (
                    <div className="msg-attach-row">
                      <ContextPlaque
                        title={m.attachment.title}
                        subtitle={`${m.attachment.text.length.toLocaleString("ru-RU")} символов`}
                        fileName={m.attachment.fileName}
                        onOpen={() => onOpenSource(m.attachment!)}
                      />
                    </div>
                  ) : null}
                  {userLong ? (
                    <button
                      type="button"
                      className="msg-body msg-plaque-trigger"
                      onClick={() => onOpenIntent(m.text)}
                    >
                      Intent · {m.text.length} символов — открыть
                    </button>
                  ) : userCollapseIntent ? (
                    <details className="msg-intent-fold">
                      <summary className="msg-intent-summary">
                        <span className="msg-intent-label">Intent</span>
                        <span className="msg-intent-preview">
                          {m.text.slice(0, 72).trim()}
                          {m.text.length > 72 ? "…" : ""}
                        </span>
                      </summary>
                      <div className="msg-body msg-pre">{m.text}</div>
                    </details>
                  ) : (
                    <div className="msg-body msg-pre">{m.text}</div>
                  )}
                </>
              ) : m.role === "bot" && hasArtifact && m.result ? (
                <div className="msg-row">
                  <span className="msg-avatar">
                    <IconLiberMark size={28} />
                  </span>
                  <div className="msg-bot-stack">
                    {m.thinking?.length ? (
                      <ThinkingFold
                        lines={m.thinking}
                        live={slidesLive}
                        liveLabel={
                          slidesLive ? "Собираю презентацию" : undefined
                        }
                        elapsedSec={
                          slidesLive && m.thinkingStartedAt
                            ? Math.max(
                                0,
                                Math.round(
                                  (Date.now() - m.thinkingStartedAt) / 1000,
                                ),
                              )
                            : m.thinkingElapsedSec
                        }
                      />
                    ) : null}
                    <MsgMarkdown text={m.text || "Отчёт готов"} />
                    <ArtifactCard
                      title={reportTitle(m.result)}
                      thumbUrl={reportThumb(m.result)}
                      pdfUrl={m.result.downloads?.pdf}
                      downloads={m.result.downloads}
                      pulse={downloadsPulseMsgId === m.id}
                      updated={downloadsPulseMsgId === m.id}
                      diagrams={m.result.diagrams}
                      slidesStatus={m.result.slides_status}
                      slidesStage={m.result.slides_stage}
                      slidePngs={m.result.slide_pngs}
                      outputMode={m.result.output_mode}
                      onView={() => {
                        const r = m.result!;
                        const diagramOnly =
                          r.output_mode === "diagram" ||
                          (!r.downloads?.pdf && Boolean(r.diagrams?.length));
                        if (diagramOnly && r.diagrams?.[0]) {
                          onOpenDiagram(m.id, r, r.diagrams[0].id);
                        } else if (r.output_mode === "presentation") {
                          onOpenPresentation(m.id, r);
                        } else {
                          onOpenReport(m.id, r);
                        }
                      }}
                      onOpenDiagram={
                        m.result.output_mode === "presentation"
                          ? undefined
                          : (id) => onOpenDiagram(m.id, m.result!, id)
                      }
                      onMakePresentation={undefined}
                      onOpenPresentation={
                        m.result.output_mode === "presentation" ||
                        m.result.slides_status === "ok"
                          ? () => onOpenPresentation(m.id, m.result!)
                          : undefined
                      }
                      onOpenDeckSlides={
                        m.result.output_mode === "presentation" ||
                        m.result.slides_status === "ok"
                          ? () => onOpenDeckSlides(m.id, m.result!)
                          : undefined
                      }
                      onDeckStyle={
                        m.result.output_mode === "presentation"
                          ? onDeckStyle
                          : undefined
                      }
                    />
                    {m.result.warnings?.length ? (
                      <div className="warns">
                        {m.result.warnings.join(" · ")}
                      </div>
                    ) : null}
                    <div className="msg-actions">
                      <button
                        type="button"
                        className="msg-action"
                        title="Копировать"
                        aria-label="Копировать текст"
                        onClick={() => {
                          void navigator.clipboard?.writeText(
                            m.text || "Отчёт готов",
                          );
                        }}
                      >
                        <IconCopy size={14} />
                      </button>
                    </div>
                  </div>
                </div>
              ) : m.role === "bot" && m.pending ? (
                <div className="msg-row">
                  <span className="msg-avatar">
                    <IconLiberMark size={28} />
                  </span>
                  <div className="msg-bot-stack">
                    <ReportPending
                      label={thinkingLabel || m.text || undefined}
                      stage={m.pendingStage || "queued"}
                      detail={m.pendingDetail}
                      mode={m.thinkingMode || workMode || "report"}
                    />
                    <ThinkingFold
                      lines={m.thinking || []}
                      live
                      elapsedSec={
                        m.thinkingStartedAt
                          ? Math.max(
                              0,
                              Math.round(
                                (Date.now() - m.thinkingStartedAt) / 1000,
                              ),
                            )
                          : undefined
                      }
                    />
                    {m.streamingSummary && m.text.trim() ? (
                      <div className="msg-stream-wrap">
                        <MsgMarkdown text={m.text} streaming />
                      </div>
                    ) : null}
                  </div>
                </div>
              ) : (
                <div className="msg-row">
                  <span className="msg-avatar">
                    <IconLiberMark size={28} />
                  </span>
                  <div className="msg-bot-stack">
                    {m.role === "bot" && m.thinking?.length ? (
                      <ThinkingFold
                        lines={m.thinking}
                        live={false}
                        elapsedSec={m.thinkingElapsedSec}
                      />
                    ) : null}
                    {m.role === "bot" && !m.error ? (
                      <MsgMarkdown text={m.text} />
                    ) : (
                      <div className="msg-body">{m.text}</div>
                    )}
                    {m.role === "bot" && m.error && (
                      <p className="err">{m.error}</p>
                    )}
                    {m.role === "bot" &&
                      m.result &&
                      (m.result.downloads?.pdf ||
                        m.result.downloads?.docx) && (
                        <ArtifactCard
                          title={reportTitle(m.result)}
                          thumbUrl={reportThumb(m.result)}
                          pdfUrl={m.result.downloads?.pdf}
                          downloads={m.result.downloads}
                          pulse={downloadsPulseMsgId === m.id}
                          updated={downloadsPulseMsgId === m.id}
                          onView={() => onOpenReport(m.id, m.result!)}
                        />
                      )}
                  </div>
                </div>
              )}
            </motion.div>
          );
        })}
      </AnimatePresence>
      <div ref={bottomRef} />
    </div>
  );
}
