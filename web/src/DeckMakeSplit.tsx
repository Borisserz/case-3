/** Split CTA: generate deck + open style sheet. */

type Props = {
  busy?: boolean;
  ready?: boolean;
  onMake: () => void;
  onOpen?: () => void;
  onStyle?: () => void;
};

export function DeckMakeSplit({
  busy = false,
  ready = false,
  onMake,
  onOpen,
  onStyle,
}: Props) {
  const gear = onStyle ? (
    <button
      type="button"
      className="deck-make-gear"
      onClick={onStyle}
      disabled={busy}
      aria-label="Стиль презентации"
      title="Стиль презентации"
    >
      ⚙
    </button>
  ) : null;
  if (ready && onOpen) {
    return (
      <div className="deck-make-split">
        <button
          type="button"
          className="artifact-card-view deck-make-primary is-accent"
          onClick={onOpen}
        >
          Презентация
        </button>
        {gear}
      </div>
    );
  }
  return (
    <div className="deck-make-split">
      <button
        type="button"
        className="artifact-card-view deck-make-primary is-accent"
        onClick={onMake}
        disabled={busy}
      >
        {busy ? "Презентация…" : "Сделать презентацию"}
      </button>
      {gear}
    </div>
  );
}
