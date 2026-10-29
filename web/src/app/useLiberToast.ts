/** Short Liber toast messages (status + optional clear timer). */

import { useCallback, useRef, useState } from "react";

export function useLiberToast() {
  const [toast, setToast] = useState<string | null>(null);
  const timerRef = useRef<number | null>(null);

  const clearToast = useCallback(() => {
    if (timerRef.current != null) {
      window.clearTimeout(timerRef.current);
      timerRef.current = null;
    }
    setToast(null);
  }, []);

  const showToast = useCallback((message: string, ms = 2800) => {
    setToast(message);
    if (timerRef.current != null) window.clearTimeout(timerRef.current);
    timerRef.current = window.setTimeout(() => {
      timerRef.current = null;
      setToast(null);
    }, ms);
  }, []);

  return { toast, setToast, showToast, clearToast };
}
