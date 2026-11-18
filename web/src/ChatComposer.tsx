/** Liber bottom composer: attach · textarea · send; deck style via DeckStyleSheet. */

import type { RefObject } from "react";
import { useEffect, useRef } from "react";
import { ComposerPhotoChips } from "./ComposerPhotoChips";
import { ContextPlaque } from "./ContextPlaque";
import type { DeckStyle, DeckThemePackInfo } from "./deckStyle";
import { DeckTemplateGallery } from "./DeckTemplateGallery";
import { ModeStarterGrid } from "./ModeStarterGrid";
import {
  IconDiagram,
  IconPalette,
  IconPaperclip,
  IconReport,
  IconSend,
  IconSlides,
  IconStop,
} from "./icons";
import { LIBER_MODE_PILLS, type LiberWorkMode } from "./domain/liberModes";
import type { SourceDraft } from "./domain/liberTypes";
import { takeInputFiles } from "./domain/takeInputFiles";

type Props = {
  busy: boolean;
  /** Stop pressed — waiting for server cancelled. */
  stopping?: boolean;
  canSend: boolean;
  /** Stop pipeline / slides while busy (UI free + server cancel). */
  onStop?: () => void;
  chat: string;
  attachPhotos: File[];
  onPreviewPhoto?: (photo: { url: string; name: string }) => void;
  showPlaque: boolean;
  plaqueDraft: { title: string; subtitle: string; fileName?: string } | null;
  sourceDraft: SourceDraft | null;
  file: File | null;
  chatRef: RefObject<HTMLTextAreaElement | null>;
  fileRef: RefObject<HTMLInputElement | null>;
  photoRef: RefObject<HTMLInputElement | null>;
  workMode: LiberWorkMode;
  onWorkMode: (mode: LiberWorkMode) => void;
  /** Mode pills — empty home only (hide once chat has messages). */
  showModes: boolean;
  /** Empty chat + presentation — show template gallery. */
  showPackPresets: boolean;
  /** Empty presentation home only — palette / style sheet. */
  showDeckStyleBtn?: boolean;
  deckStyle: DeckStyle;
  deckPacks?: DeckThemePackInfo[];
  /** Apply pack + structure and fill composer with starter prompt (Julius). */
  onUseDeckTemplate?: (
    next: DeckStyle,
    meta: { title: string; arc: string; starterPrompt: string },
  ) => void;
  /** Transient status after template apply. */
  deckApplyHint?: string | null;
  onDismissDeckApplyHint?: () => void;
  /** Open DeckStyleSheet (sole style surface). */
  onOpenDeckStyle: () => void;
  deckStyleOpen?: boolean;
  onChatChange: (v: string) => void;
  onPasteCapture: (pasted: string) => boolean;
  onSend: () => void;
  onIngestFiles: (list: FileList | File[]) => void;
  onRemovePhoto: (index: number) => void;
  onOpenSource: () => void;
  onDismissPlaque: () => void;
  /** Fill composer from quiet starter card (report/diagram). */
  onPickStarter?: (prompt: string) => void;
};

export function ChatComposer({
  busy,
  stopping = false,
  canSend,
  onStop,
  chat,
  attachPhotos,
  onPreviewPhoto,
  showPlaque,
  plaqueDraft,
  sourceDraft,
  file,
  chatRef,
  fileRef,
  photoRef,
  workMode,
  onWorkMode,
  showModes,
  showPackPresets,
  showDeckStyleBtn = false,
  deckStyle,
  deckPacks,
  onUseDeckTemplate,
  deckApplyHint = null,
  onDismissDeckApplyHint,
  onOpenDeckStyle,
  deckStyleOpen = false,
  onChatChange,
  onPasteCapture,
  onSend,
  onIngestFiles,
  onRemovePhoto,
  onOpenSource,
  onDismissPlaque,
  onPickStarter,
}: Props) {
  const galleryRef = useRef<HTMLDivElement>(null);
  const placeholder =
    workMode === "diagram"
      ? "Опишите процесс — или просто спросите"
      : workMode === "presentation"
        ? "Материал для презентации — или вопрос по тексту"
        : workMode === "report"
          ? "Материал для отчёта — или вопрос по тексту"
        : sourceDraft || file
          ? "Спросите по этому тексту или попросите отчёт, схему, презентацию"
          : "Напишите вопрос или попросите отчёт, схему, презентацию";

  useEffect(() => {
    if (!showPackPresets) return;
    const t = window.setTimeout(() => {
      galleryRef.current?.scrollIntoView({
        behavior: "smooth",
        block: "nearest",
      });
    }, 80);
    return () => window.clearTimeout(t);
  }, [showPackPresets]);

  /** Stable stage width: empty home (any/no pill) + never shrink mid-chat */
  const isEmptyStage = Boolean(showModes);
  const isDeckHome = Boolean(showPackPresets);
  return (
    <div
      className={`composer-wrap is-stage-wide${isEmptyStage ? " is-empty-stage" : ""}${isDeckHome ? " is-deck-home" : ""}`}
    >
      {/* Same width column as .composer — plaque/Working can't drift left of the sheet */}
      <div className="composer-stack">
        {attachPhotos.length > 0 && (
          <div className="composer-attach-row">
            <ComposerPhotoChips
              files={attachPhotos}
              busy={busy}
              onRemove={onRemovePhoto}
              onPreview={onPreviewPhoto}
            />
          </div>
        )}
        {showPlaque && plaqueDraft ? (
          <ContextPlaque
            title={plaqueDraft.title}
            subtitle={plaqueDraft.subtitle}
            fileName={plaqueDraft.fileName}
            disabled={busy}
            onOpen={onOpenSource}
            onDismiss={onDismissPlaque}
          />
        ) : null}

        {deckApplyHint ? (
          <div className="composer-deck-hint" role="status">
            <span>{deckApplyHint}</span>
            {onDismissDeckApplyHint ? (
              <button
                type="button"
                className="composer-deck-hint-x"
                aria-label="Скрыть"
                onClick={onDismissDeckApplyHint}
              >
                ×
              </button>
            ) : null}
          </div>
        ) : null}

        <div className="composer">
          <input
            ref={fileRef}
            className="composer-file-input"
            type="file"
            accept=".txt,.md,.pdf,.docx,.doc,.docm,.rtf,text/plain,text/markdown,application/pdf,image/png,image/jpeg,.png,.jpg,.jpeg"
            multiple
            onChange={(e) => {
              const files = takeInputFiles(e.target);
              if (files.length) onIngestFiles(files);
            }}
          />
          <input
            ref={photoRef}
            type="file"
            accept="image/*"
            multiple
            hidden
          />
          <textarea
            ref={chatRef}
            className="composer-input"
            rows={2}
            placeholder={placeholder}
            value={chat}
            disabled={busy}
            onChange={(e) => onChatChange(e.target.value)}
            onPaste={(e) => {
              const files = e.clipboardData.files;
              if (files && files.length > 0) {
                const hasMediaOrDoc = Array.from(files).some(
                  (f) =>
                    /^image\//.test(f.type) ||
                    /\.(txt|md|pdf|docx|docm|doc|rtf|png|jpe?g)$/i.test(
                      f.name,
                    ) ||
                    f.type === "text/plain" ||
                    f.type === "text/markdown" ||
                    f.type === "application/pdf",
                );
                if (hasMediaOrDoc) {
                  e.preventDefault();
                  onIngestFiles(files);
                  return;
                }
              }
              const pasted = e.clipboardData.getData("text/plain");
              if (onPasteCapture(pasted)) {
                e.preventDefault();
              }
            }}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                onSend();
              }
            }}
          />
          <div className="composer-inner-bar">
            <button
              type="button"
              className="composer-attach"
              disabled={busy}
              title="Прикрепить PDF/DOCX/TXT/MD или фото"
              aria-label="Прикрепить файл"
              onClick={() => fileRef.current?.click()}
            >
              <IconPaperclip size={18} />
            </button>
            {showDeckStyleBtn ? (
              <button
                type="button"
                className={`composer-palette-btn${deckStyleOpen ? " is-on" : ""}`}
                disabled={busy}
                title="Стиль презентации"
                aria-label="Стиль презентации"
                aria-pressed={deckStyleOpen}
                onClick={onOpenDeckStyle}
              >
                <IconPalette size={18} />
              </button>
            ) : null}
            <span className="composer-inner-spacer" aria-hidden />
            {busy && onStop ? (
              <button
                className={`send is-stop${stopping ? " is-stopping" : ""}`}
                type="button"
                onClick={onStop}
                disabled={stopping}
                aria-label={stopping ? "Останавливаю" : "Остановить"}
                title={stopping ? "Останавливаю…" : "Остановить"}
              >
                <IconStop size={20} />
              </button>
            ) : (
              <button
                className="send"
                type="button"
                disabled={!canSend}
                onClick={onSend}
                aria-label={workMode ? "Собрать" : "Отправить"}
                title={workMode ? "Собрать" : "Отправить"}
              >
                <IconSend size={16} />
              </button>
            )}
          </div>
        </div>

        <div className="chat-bias" role="group" aria-label="Собрать сразу">
          {LIBER_MODE_PILLS.map((p) => {
            const on = workMode === p.id;
            const Icon =
              p.id === "diagram"
                ? IconDiagram
                : p.id === "presentation"
                  ? IconSlides
                  : IconReport;
            return (
              <button
                key={p.id}
                type="button"
                className={on ? "is-on" : ""}
                disabled={busy}
                title={p.hint}
                aria-pressed={on}
                onClick={() => onWorkMode(on ? null : p.id)}
              >
                <Icon size={15} />
                <span>{p.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      {showModes && onPickStarter && workMode ? (
        <ModeStarterGrid
          workMode={workMode}
          busy={busy}
          onPick={onPickStarter}
        />
      ) : null}

      {showPackPresets && onUseDeckTemplate ? (
        <div ref={galleryRef} className="composer-deck-gallery-anchor">
          <DeckTemplateGallery
            deckStyle={deckStyle}
            deckPacks={deckPacks}
            busy={busy}
            onApply={onUseDeckTemplate}
          />
        </div>
      ) : null}
    </div>
  );
}
