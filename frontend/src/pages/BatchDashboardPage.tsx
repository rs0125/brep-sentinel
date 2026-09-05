import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ChevronRight } from "lucide-react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { getBatchHistory, runBatch } from "../lib/api";
import type { BatchHistoryEntry, BatchRunResponse } from "../lib/types";
import MetricCard from "../components/MetricCard";
import { COLORS } from "../lib/theme";

function pct(n: number) {
  return `${(n * 100).toFixed(1)}%`;
}

export default function BatchDashboardPage() {
  const navigate = useNavigate();
  const [history, setHistory] = useState<BatchHistoryEntry[]>([]);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [latest, setLatest] = useState<BatchRunResponse | null>(null);

  function loadHistory() {
    getBatchHistory()
      .then(setHistory)
      .catch((e) => setError(e instanceof Error ? e.message : String(e)));
  }

  useEffect(loadHistory, []);

  async function handleRun() {
    setRunning(true);
    setError(null);
    try {
      const res = await runBatch();
      setLatest(res);
      loadHistory();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setRunning(false);
    }
  }

  const m = latest?.evaluation.metrics;

  return (
    <div className="stack" style={{ gap: 24 }}>
      <div className="row" style={{ justifyContent: "space-between" }}>
        <div>
          <h1>Batch pipeline</h1>
          <p className="muted" style={{ margin: 0 }}>
            Corpus generation → perturbations → fixtures → evaluation → report, in one run.
          </p>
        </div>
        <button className="primary" onClick={handleRun} disabled={running}>
          {running ? "Running…" : "Run batch pipeline"}
        </button>
      </div>

      {error && <div style={{ color: "var(--malformed)" }}>{error}</div>}

      {running && (
        <div className="muted">
          Generating corpus, perturbations, and fixtures, then evaluating and reporting…
        </div>
      )}

      {m && (
        <div className="row" style={{ gap: 12, flexWrap: "wrap" }}>
          <MetricCard label="Total files" value={String(latest!.evaluation.counts.total)} />
          <MetricCard
            label="False-positive rate"
            value={pct(m.false_positive_rate)}
            tone={m.false_positive_rate === 0 ? "good" : "bad"}
          />
          <MetricCard
            label="Adjudication recall"
            value={pct(m.adjudication_recall)}
            tone={m.adjudication_recall === 1 ? "good" : "bad"}
          />
          <MetricCard
            label="Layered recall"
            value={pct(m.layered_recall)}
            tone={m.layered_recall === 1 ? "good" : "bad"}
          />
          <MetricCard label="Precision" value={pct(m.precision)} />
        </div>
      )}

      {history.length > 1 && (
        <div className="panel">
          <h2>Trend across runs</h2>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart
              data={[...history]
                .reverse()
                .map((h) => ({
                  label: h.label || h.run_id.slice(0, 6),
                  fp_pct: h.false_positive_rate * 100,
                  recall_pct: h.adjudication_recall * 100,
                }))}
              margin={{ left: -20, right: 10 }}
            >
              <CartesianGrid stroke={COLORS.line} strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="label" stroke={COLORS.inkFaint} fontSize={11} tickLine={false} />
              <YAxis
                stroke={COLORS.inkFaint}
                fontSize={11}
                domain={[0, 100]}
                tickFormatter={(v) => `${v}%`}
                tickLine={false}
              />
              <Tooltip
                contentStyle={{
                  background: COLORS.panelRaised,
                  border: `1px solid ${COLORS.lineStrong}`,
                  fontFamily: "IBM Plex Mono, monospace",
                  fontSize: 12,
                }}
                formatter={(v) => `${Number(v).toFixed(1)}%`}
              />
              <Line type="monotone" dataKey="fp_pct" name="FP rate" stroke={COLORS.malformed} strokeWidth={2} dot={{ r: 3 }} />
              <Line type="monotone" dataKey="recall_pct" name="Recall" stroke={COLORS.clean} strokeWidth={2} dot={{ r: 3 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      <div>
        <h2>Run history</h2>
        {history.length === 0 ? (
          <div className="panel muted">No batch runs yet.</div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Run</th>
                <th>Files</th>
                <th>FP rate</th>
                <th>Recall</th>
                <th>Layered recall</th>
                <th>When</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {history.map((h) => (
                <tr key={h.run_id} className="clickable" onClick={() => navigate(`/batch/${h.run_id}`)}>
                  <td className="muted">{h.label || h.run_id}</td>
                  <td>{h.total_files}</td>
                  <td style={{ color: h.false_positive_rate === 0 ? "var(--clean)" : "var(--malformed)" }}>
                    {pct(h.false_positive_rate)}
                  </td>
                  <td style={{ color: h.adjudication_recall === 1 ? "var(--clean)" : "var(--malformed)" }}>
                    {pct(h.adjudication_recall)}
                  </td>
                  <td>{pct(h.layered_recall)}</td>
                  <td className="faint">{new Date(h.created_at).toLocaleString()}</td>
                  <td>
                    <ChevronRight size={15} color="var(--ink-faint)" />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
