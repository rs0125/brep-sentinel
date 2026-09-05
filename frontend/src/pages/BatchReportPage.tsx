import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getBatchReport } from "../lib/api";
import Markdown from "../components/Markdown";

export default function BatchReportPage() {
  const { runId } = useParams<{ runId: string }>();
  const [markdown, setMarkdown] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!runId) return;
    getBatchReport(runId)
      .then((res) => setMarkdown(res.markdown))
      .catch((e) => setError(e instanceof Error ? e.message : String(e)));
  }, [runId]);

  return (
    <div className="stack" style={{ gap: 16 }}>
      <div>
        <Link to="/batch">← back to batch dashboard</Link>
      </div>
      <h1>Report — {runId}</h1>
      {error && <div style={{ color: "var(--malformed)" }}>{error}</div>}
      {!error && !markdown && <div className="muted">Loading…</div>}
      {markdown && <Markdown text={markdown} />}
    </div>
  );
}
