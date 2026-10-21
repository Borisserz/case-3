/** Compact source / long-intent chip (composer + sent request). */

type Props = {
  title: string;
  subtitle?: string;
  onOpen: () => void;
  /** Composer only — omit in chat history (attached doc). */
  onDismiss?: () => void;
  disabled?: boolean;
};

export function ContextPlaque({
  title,
  subtitle,
  onOpen,
  onDismiss,
  disabled = false,
}: Props) {
  const tip = subtitle ? `${title} · ${subtitle}` : title;
  return (
    <div className="context-plaque" role="region" aria-label="Контекст источника">
      <button
        type="button"
        className={`context-plaque-main${onDismiss ? "" : " is-solo"}`}
        onClick={onOpen}
        disabled={disabled}
        title={tip}
      >
        <span className="context-plaque-icon" aria-hidden>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
            <path
              d="M7 3h7l5 5v13a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1z"
              stroke="currentColor"
              strokeWidth="1.7"
            />
            <path
              d="M14 3v5h5"
              stroke="currentColor"
              strokeWidth="1.7"
              strokeLinejoin="round"
            />
          </svg>
        </span>
        <span className="context-plaque-title">{title}</span>
      </button>
      {onDismiss ? (
        <button
          type="button"
          className="context-plaque-x"
          aria-label="Скрыть"
          disabled={disabled}
          onClick={(e) => {
            e.stopPropagation();
            onDismiss();
          }}
        >
          ×
        </button>
      ) : null}
    </div>
  );
}
