/** Liber chat transcript — Julius column DNA (user panel + document bot). */

import { AnimatePresence, motion } from "framer-motion";
import { ArtifactCard } from "./ArtifactCard";
import { ContextPlaque } from "./ContextPlaque";
import { EmptyState } from "./EmptyState";
import { IconCopy, IconLiberMark } from "./icons";
import { LONG_TEXT_CHARS } from "./domain/liberConstants";
import type { LiberWorkMode } from "./domain/liberModes";
import type { CraftFilmFrame } from "./domain/craftSteps";
import type { Msg, RunResult, SourceAttachment, UserPhotoThumb } from "./domain/liberTypes";
import { reportThumb, reportTitle } from "./domain/runHelpers";
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
  onOpenPresentation: (msgId: string, result: RunResult) => void;
  onOpenDeckSlides: (msgId: string, result: RunResult) => void;
  onOpenFilm?: (msgId: string, frame: CraftFilmFrame) => void;
  onOpenPhoto?: (photo: UserPhotoThumb) => void;
  /** Continue failed pipeline from failed_stage (same run_id). */
  onResumeRun?: (msgId: string, runId: string) => void;
  /** Message whose deck file lags the screen. Its PPTX/PDF stay closed. */
  deckDownloadsBlockedMsgId?: string | null;
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
  onOpenPresentation,
  onOpenDeckSlides,
  onOpenFilm,
  onOpenPhoto,
  onResumeRun,
  deckDownloadsBlockedMsgId = null,
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
                  {m.photos?.length ? (
                    <div className="msg-photos" aria-label="Прикреплённые фото">
                      {m.photos.map((photo, pi) => (
                        <button
                          key={`${photo.url}-${pi}`}
                          type="button"
                          className="msg-photo-btn"
                          onClick={() => onOpenPhoto?.(photo)}
                          title={photo.name ? `Открыть ${photo.name}` : "Открыть фото"}
                          aria-label={photo.name ? `Открыть фото ${photo.name}` : "Открыть фото"}
                        >
                          <img
                            src={photo.url}
                            alt={photo.name || "Фото"}
                          />
                        </button>
                      ))}
                    </div>
                  ) : null}
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
                      Запрос · {m.text.length} символов — открыть
                    </button>
                  ) : userCollapseIntent ? (
                    <details className="msg-intent-fold">
                      <summary className="msg-intent-summary">
                        <span className="msg-intent-label">Запрос</span>
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
                    {m.thinking?.length ||
                    m.craftFilm?.length ||
                    m.craftSubsteps?.length ||
                    m.craftRecap ||
                    m.errorHint ? (
                      <ThinkingFold
                        lines={m.thinking || []}
                        live={slidesLive}
                        liveLabel={
                          slidesLive ? "Собираю презентацию" : undefined
                        }
                        stage={m.pendingStage || m.result?.slides_stage}
                        thinkingMode={m.thinkingMode || "report"}
                        reduceMotion={reduceMotion}
                        craftSubsteps={m.craftSubsteps}
                        craftSkipped={m.craftSkipped}
                        craftFilm={m.craftFilm}
                        craftRecap={m.craftRecap}
                        onOpenFilm={
                          onOpenFilm
                            ? (frame) => onOpenFilm(m.id, frame)
                            : undefined
                        }
                        etaSec={m.etaSec}
                        craftFrozen={m.craftFrozen}
                        errorHint={m.errorHint}
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
                      deck={m.result.deck}
                      runId={m.result.run_id}
                      outputMode={m.result.output_mode}
                      deckDownloadsBlocked={m.id === deckDownloadsBlockedMsgId}
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
                    />
                    {(() => {
                      const displayWarns = (m.result.warnings || []).filter(
                        (w) =>
                          !/charts? (?:failed|skipped)|фото пропущены|Image API|Часть медиа|skipped/i.test(
                            w
                          )
                      );
                      return displayWarns.length ? (
                        <div className="warns">
                          {displayWarns.join(" · ")}
                        </div>
                      ) : null;
                    })()}
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
                      stage={m.pendingStage}
                      thinkingMode={m.thinkingMode || "report"}
                      reduceMotion={reduceMotion}
                      craftSubsteps={m.craftSubsteps}
                      craftSkipped={m.craftSkipped}
                      craftFilm={m.craftFilm}
                      craftRecap={m.craftRecap}
                      onOpenFilm={
                        onOpenFilm
                          ? (frame) => onOpenFilm(m.id, frame)
                          : undefined
                      }
                      etaSec={m.etaSec}
                      craftFrozen={m.craftFrozen}
                      errorHint={m.errorHint}
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
                    {m.role === "bot" &&
                    (m.thinking?.length ||
                      m.craftFilm?.length ||
                      m.craftSubsteps?.length ||
                      m.craftRecap ||
                      m.errorHint) ? (
                      <ThinkingFold
                        lines={m.thinking || []}
                        live={false}
                        stage={m.pendingStage}
                        thinkingMode={m.thinkingMode || "report"}
                        reduceMotion={reduceMotion}
                        craftSubsteps={m.craftSubsteps}
                        craftSkipped={m.craftSkipped}
                        craftFilm={m.craftFilm}
                        craftRecap={m.craftRecap}
                        onOpenFilm={
                          onOpenFilm
                            ? (frame) => onOpenFilm(m.id, frame)
                            : undefined
                        }
                        etaSec={m.etaSec}
                        craftFrozen={m.craftFrozen}
                        errorHint={m.errorHint}
                        elapsedSec={m.thinkingElapsedSec}
                      />
                    ) : null}
                    {m.role === "bot" && !m.error ? (
                      <MsgMarkdown text={m.text} />
                    ) : (
                      <div className="msg-body">{m.text}</div>
                    )}
                    {m.role === "bot" && m.error && (
                      <div className="msg-error-block">
                        <p className="err">{m.error}</p>
                        {m.canResume && m.failedRunId && onResumeRun ? (
                          <button
                            type="button"
                            className="btn-resume-run"
                            onClick={() =>
                              onResumeRun(m.id, m.failedRunId as string)
                            }
                          >
                            Продолжить
                          </button>
                        ) : null}
                      </div>
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
