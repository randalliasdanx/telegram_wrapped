import { useEffect, useState } from "react";
import type { SSEProgress } from "../api/types";

export function useSSE(url: string | null) {
  const [progress, setProgress] = useState<SSEProgress | null>(null);
  const [done, setDone] = useState(false);

  useEffect(() => {
    if (!url) return;
    const source = new EventSource(url);
    source.onmessage = (e) => {
      const data: SSEProgress = JSON.parse(e.data);
      setProgress(data);
      if (data.phase === "done") {
        setDone(true);
        source.close();
      }
    };
    source.onerror = () => source.close();
    return () => source.close();
  }, [url]);

  return { progress, done };
}
