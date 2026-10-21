/** Quiet thinking strip above composer — Mary placement, Liber stages. */

import { useEffect, useState } from "react";

type Props = {
  active: boolean;
  label?: string;
};

export function ThinkingBar({ active, label = "Liber думает…" }: Props) {
  const [sec, setSec] = useState(0);

  useEffect(() => {
    if (!active) {
      setSec(0);
      return;
    }
    setSec(0);
    const t = window.setInterval(() => setSec((s) => s + 1), 1000);
    return () => window.clearInterval(t);
  }, [active]);

  if (!active) return null;

  return (
    <div className="thinking-bar" role="status" aria-live="polite">
      <span className="thinking-dots" aria-hidden>
        <i />
        <i />
        <i />
      </span>
      <span className="thinking-label">{label}</span>
      <span className="thinking-timer">{sec} сек</span>
    </div>
  );
}
