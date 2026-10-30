/** Transient Liber toast + optional undo. */

type Props = {
  toast: string | null;
  undoOffer: { msgId: string; runId: string } | null;
  onUndo: () => void;
};

export function LiberToastBar({ toast, undoOffer, onUndo }: Props) {
  if (!toast) return null;
  return (
    <div className="liber-toast" role="status" aria-live="polite">
      <span>{toast}</span>
      {undoOffer ? (
        <button
          type="button"
          className="liber-toast-undo"
          onClick={() => void onUndo()}
        >
          Отменить
        </button>
      ) : null}
    </div>
  );
}
