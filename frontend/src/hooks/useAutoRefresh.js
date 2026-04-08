import { useEffect } from "react";

function useAutoRefresh(refresh, options = {}) {
  const {
    enabled = true,
    intervalMs = 30000,
  } = options;

  useEffect(() => {
    if (!enabled) {
      return undefined;
    }

    refresh();

    const handleVisibilityChange = () => {
      if (document.visibilityState === "visible") {
        refresh();
      }
    };

    const handleFocus = () => {
      refresh();
    };

    const intervalId = window.setInterval(() => {
      if (document.visibilityState === "visible") {
        refresh();
      }
    }, intervalMs);

    document.addEventListener("visibilitychange", handleVisibilityChange);
    window.addEventListener("focus", handleFocus);

    return () => {
      window.clearInterval(intervalId);
      document.removeEventListener("visibilitychange", handleVisibilityChange);
      window.removeEventListener("focus", handleFocus);
    };
  }, [enabled, intervalMs, refresh]);
}

export default useAutoRefresh;
