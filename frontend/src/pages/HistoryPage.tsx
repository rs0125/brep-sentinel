import { useEffect, useState } from "react";
import { ChevronRight } from "lucide-react";
import { getSingleHistory, getSingleResult } from "../lib/api";
import type { AdjudicateResponse, SingleHistoryEntry } from "../lib/types";
import VerdictBadge from "../components/VerdictBadge";
import ResultView from "../components/ResultView";

export default function HistoryPage() {
  const [entries, setEntries] = useState<SingleHistoryEntry[]>([]);
  const [selected, setSelected] = useState<AdjudicateResponse | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getSingleHistory()
      .then(setEntries)
      .catch((e) => setError(e instanceof Error ? e.message : String(e)))
      .finally(() => setLoading(false));
  }, []);

  async function open(runId: string) {
    setSelected(null);
    setSelectedId(runId);
    try {
      const res = await getSingleResult(runId);
      setSelected(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  return (
    <div className="stack" style={{ gap: 24 }}>
      <div>
        <h1>Single-file history</h1>
        <p className="muted" style={{ margin: 0 }}>
          Every file adjudicated through the upload page, newest first. Click a row to reopen it.
        </p>
      </div>

      {loading && <div className="muted">Loading…</div>}
      {error && <div style={{ color: "var(--danger)" }}>{error}</div>}

      {!loading && entries.length === 0 && (
        <div className="panel muted">No files adjudicated yet. Upload one to see it here.</div>
      )}

      {entries.length > 0 && (
        <table>
          <thead>
            <tr>
              <th>Filename</th>
              <th>Verdict</th>
              <th>Size</th>
              <th>Run at</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {entries.map((e) => (
              <tr
                key={e.run_id}
                className="clickable"
                onClick={() => open(e.run_id)}
                style={
                  selectedId === e.run_id
                    ? { background: "var(--panel-raised)" }
                    : undefined
                }
              >
                <td>{e.filename}</td>
                <td>
                  <VerdictBadge verdict={e.verdict} size="sm" />
                </td>
                <td className="muted">{(e.bytes / 1024).toFixed(1)} KB</td>
                <td className="faint">{new Date(e.created_at).toLocaleString()}</td>
                <td>
                  <ChevronRight size={15} color="var(--ink-faint)" />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {selected && (
        <div className="stack" style={{ gap: 12, marginTop: 12 }}>
          <h2 style={{ margin: 0 }}>{selected.meta?.filename ?? "Result"}</h2>
          <ResultView result={selected} runId={selected.run_id} />
        </div>
      )}
    </div>
  );
}
