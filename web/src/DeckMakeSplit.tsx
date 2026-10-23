/** Split CTA: generate deck + open style sheet. */

type Props = {
  busy?: boolean;
  ready?: boolean;
  /** Outline style under Julius in-chat cards (don't compete with preview). */
  quiet?: boolean;
  onMake: () => void;
  onOpen?: () => void;
  onStyle?: () => void;
};

export function DeckMakeSplit({
  busy = false,
  ready = false,
  quiet = false,
  onMake,
  onOpen,
  onStyle,
}: Props) {
  const splitClass = quiet ? "deck-make-split is-quiet" : "deck-make-split";
  const primaryClass = quiet
    ? "artifact-card-view deck-make-primary is-ghost"
    : "artifact-card-view deck-make-primary is-accent";
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
      <div className={splitClass}>
        <button type="button" className={primaryClass} onClick={onOpen}>
          Презентация
        </button>
        {gear}
      </div>
    );
  }
  return (
    <div className={splitClass}>
      <button
        type="button"
        className={primaryClass}
        onClick={onMake}
        disabled={busy}
      >
        {busy ? "Презентация…" : "Сделать презентацию"}
      </button>
      {gear}
    </div>
  );
}
