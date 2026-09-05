import { useEffect, useState } from "react";

export type ApiStatus = "checking" | "online" | "offline";

export function useApiHealth(intervalMs = 15000): ApiStatus {
  const [status, setStatus] = useState<ApiStatus>("checking");

  useEffect(() => {
    let cancelled = false;
    const base = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

    async function check() {
      try {
        const res = await fetch(`${base}/api/health`);
        if (!cancelled) setStatus(res.ok ? "online" : "offline");
      } catch {
        if (!cancelled) setStatus("offline");
      }
    }

    check();
    const id = setInterval(check, intervalMs);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [intervalMs]);

  return status;
}
