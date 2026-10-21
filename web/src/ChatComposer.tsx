/** Liber bottom composer: attach · textarea · send + optional plaque/photos. */

import type { RefObject } from "react";
import { ComposerPhotoChips } from "./ComposerPhotoChips";
import { ContextPlaque } from "./ContextPlaque";
import { IconPaperclip, IconSend } from "./icons";
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
  onChatChange,
  onPasteCapture,
  onSend,
  onIngestFiles,
  onRemovePhoto,
  onOpenSource,
  onDismissPlaque,
}: Props) {
  return (
    <div className="composer-wrap">
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
          placeholder={
            sourceDraft || file
              ? "Спросить Liber…"
              : "Опишите отчёт или вставьте Source…"
          }
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
          aria-label="Собрать отчёт"
          title="Собрать"
        >
          {busy ? "…" : <IconSend size={16} />}
        </button>
      </div>
    </div>
  );
}
