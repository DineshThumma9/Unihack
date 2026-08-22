import { useEffect } from "react";
import { useJobStore } from "../stores/job.store";
import type { JobEvent } from "../types/job";

export function useJobEvents(jobId: string | null) {
  const handleEvent = useJobStore((state) => state.handleEvent);

  useEffect(() => {
    if (!jobId) return;

    const baseURL = import.meta.env.VITE_API_URL || "http://localhost:8000";
    const url = `${baseURL}/api/jobs/${jobId}/events`;
    const es = new EventSource(url);

    const parseAndDispatch = (e: MessageEvent) => {
      try {
        const data: JobEvent = JSON.parse(e.data);
        handleEvent(data);
        if (data.type === "job.completed" || data.type === "job.failed") {
          es.close();
        }
      } catch (err) {
        console.error("Failed to parse SSE event", err);
      }
    };

    es.onmessage = parseAndDispatch;
    es.addEventListener("job.started", parseAndDispatch);
    es.addEventListener("product.started", parseAndDispatch);
    es.addEventListener("product.completed", parseAndDispatch);
    es.addEventListener("product.failed", parseAndDispatch);
    es.addEventListener("job.completed", parseAndDispatch);
    es.addEventListener("job.failed", parseAndDispatch);

    es.onerror = (err) => {
      console.warn("SSE connection error/reconnecting...", err);
    };

    return () => {
      es.close();
    };
  }, [jobId, handleEvent]);
}
