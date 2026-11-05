/** Thumbnail chips for photos attached to the Liber composer. */

import { useEffect, useState } from "react";

export function ComposerPhotoChips({
  files,
  busy,
  onRemove,
}: {
  files: File[];
  busy: boolean;
  onRemove: (index: number) => void;
}) {
  const [urls, setUrls] = useState<string[]>([]);
  useEffect(() => {
    const next = files.map((f) => URL.createObjectURL(f));
    setUrls(next);
    return () => {
      for (const u of next) URL.revokeObjectURL(u);
    };
  }, [files]);
  return (
    <div className="composer-photos" aria-label="Прикреплённые фото">
      {files.map((p, i) => (
        <div key={`${p.name}-${i}-${p.size}`} className="composer-photo-chip">
          <img src={urls[i]} alt="" />
          <button
            type="button"
            className="composer-photo-x"
            aria-label="Убрать фото"
            disabled={busy}
            onClick={() => onRemove(i)}
          >
            ×
          </button>
        </div>
      ))}
    </div>
  );
}
