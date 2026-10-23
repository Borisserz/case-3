/** Liber bottom composer: attach · textarea · send; deck style via DeckStyleSheet. */

import type { RefObject } from "react";
import { useEffect, useRef } from "react";
import { ComposerPhotoChips } from "./ComposerPhotoChips";
import { ContextPlaque } from "./ContextPlaque";
import type { DeckStyle, DeckThemePackInfo } from "./deckStyle";
import { DeckTemplateGallery } from "./DeckTemplateGallery";
import { IconPalette, IconPaperclip, IconSend } from "./icons";
import { LIBER_MODE_PILLS, type LiberWorkMode } from "./liberModes";
import type { SourceDraft } from "./liberTypes";

type Props = {
  busy: boolean;
  canSend: boolean;
  chat: string;
  attachPhotos: File[];
  showPlaque: boolean;
  plaqueDraft: { title: string; subtitle: string } | null;
  sourceDraft: SourceDraft | null;
  file: File | null;
  chatRef: RefObject<HTMLTextAreaElement | null>;
  fileRef: RefObject<HTMLInputElement | null>;
  photoRef: RefObject<HTMLInputElement | null>;
  workMode: LiberWorkMode;
  onWorkMode: (mode: LiberWorkMode) => void;
  /** Mode pills — stay after first message. */
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
};

export function ChatComposer({
  busy,
  canSend,
  chat,
  attachPhotos,
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
}: Props) {
  const galleryRef = useRef<HTMLDivElement>(null);
  const placeholder =
    workMode === "diagram"
      ? "Опишите процесс или вставьте Source для схемы…"
      : workMode === "presentation"
        ? "Вставьте Source или коротко опишите задачу…"
        : sourceDraft || file
          ? "Спросить Liber…"
          : "Опишите отчёт или вставьте Source…";

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

  return (
    <div
      className={`composer-wrap${showPackPresets ? " is-deck-home" : ""}`}
    >
      {attachPhotos.length > 0 && (
        <div className="composer-attach-row">
          <ComposerPhotoChips
            files={attachPhotos}
            busy={busy}
            onRemove={onRemovePhoto}
          />
        </div>
      )}
      {showPlaque && plaqueDraft ? (
        <ContextPlaque
          title={plaqueDraft.title}
          subtitle={plaqueDraft.subtitle}
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
          type="file"
          accept=".txt,.md,text/plain,text/markdown,image/png,image/jpeg,.png,.jpg,.jpeg"
          multiple
          hidden
          onChange={(e) => {
            const list = e.target.files;
            e.target.value = "";
            if (list?.length) onIngestFiles(list);
          }}
        />
        <input
          ref={photoRef}
          type="file"
          accept="image/*"
          multiple
          hidden
        />
        <button
          type="button"
          className="composer-attach"
          disabled={busy}
          title="Прикрепить .txt / .md или фото"
          aria-label="Прикрепить файл"
          onClick={() => fileRef.current?.click()}
        >
          <IconPaperclip size={18} />
        </button>
        <textarea
          ref={chatRef}
          className="composer-input"
          rows={1}
          placeholder={placeholder}
          value={chat}
          disabled={busy}
          onChange={(e) => onChatChange(e.target.value)}
          onPaste={(e) => {
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
        <button
          className="send"
          type="button"
          disabled={!canSend}
          onClick={onSend}
          aria-busy={busy || undefined}
          aria-label={
            workMode === "diagram"
              ? "Собрать схему"
              : workMode === "presentation"
                ? "Собрать презентацию"
                : "Собрать отчёт"
          }
          title="Собрать"
        >
          {busy ? "…" : <IconSend size={16} />}
        </button>
      </div>

      {showModes ? (
        <div className="composer-toolbar">
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
          <div className="composer-modes" role="group" aria-label="Режим">
            {LIBER_MODE_PILLS.map((p) => {
              const on = workMode === p.id;
              return (
                <button
                  key={p.id}
                  type="button"
                  className={`composer-mode-pill${on ? " is-on" : ""}`}
                  disabled={busy}
                  title={p.hint}
                  aria-pressed={on}
                  onClick={() => onWorkMode(on ? null : p.id)}
                >
                  {p.label}
                </button>
              );
            })}
          </div>
        </div>
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
