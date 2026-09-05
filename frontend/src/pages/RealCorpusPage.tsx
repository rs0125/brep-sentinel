import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ChevronRight } from "lucide-react";
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { getRealHistory, ingestRealCorpus, runRealDemo } from "../lib/api";
import type { RealHistoryEntry, RealRunResponse } from "../lib/types";
import MetricCard from "../components/MetricCard";
import { COLORS } from "../lib/theme";

export default function RealCorpusPage() {
  const navigate = useNavigate();
  const [history, setHistory] = useState<RealHistoryEntry[]>([]);
  const [ingesting, setIngesting] = useState(false);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [latest, setLatest] = useState<RealRunResponse | null>(null);

  function loadHistory() {
    getRealHistory()
      .then(setHistory)
      .catch((e) => setError(e instanceof Error ? e.message : String(e)));
  }

  useEffect(loadHistory, []);

  async function handleIngest() {
    setIngesting(true);
    setError(null);
    try {
      await ingestRealCorpus();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setIngesting(false);
    }
  }

  async function handleRun() {
    setRunning(true);
    setError(null);
    try {
      const res = await runRealDemo();
      setLatest(res);
      loadHistory();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setRunning(false);
    }
  }

  const s = latest?.result.summary;

  return (
    <div className="stack" style={{ gap: 24 }}>
      <div className="row" style={{ justifyContent: "space-between" }}>
        <div>
          <h1>Real-corpus demo</h1>
          <p className="muted" style={{ margin: 0 }}>
            Baseline + infect + detect on real, third-party STEP files.
          </p>
        </div>
        <div className="row" style={{ gap: 8 }}>
          <button onClick={handleIngest} disabled={ingesting}>
            {ingesting ? "Fetching…" : "Refresh real_corpus/"}
          </button>
          <button className="primary" onClick={handleRun} disabled={running}>
            {running ? "Running…" : "Run demo"}
          </button>
        </div>
      </div>

      <p className="faint" style={{ margin: 0 }}>
        Refreshing real_corpus/ fetches files from upstream sources and needs outbound network
        access. The repo already ships a small committed set, so you can run the demo without
        refreshing first.
      </p>

      {error && <div style={{ color: "var(--malformed)" }}>{error}</div>}

      {s && (
        <div className="row" style={{ gap: 12, flexWrap: "wrap" }}>
          <MetricCard label="Real solids tested" value={String(s.real_solids_tested)} />
          <MetricCard
            label="Baseline clean"
            value={`${s.baseline_clean}/${s.real_solids_tested}`}
            tone={s.baseline_false_positives === 0 ? "good" : "bad"}
          />
          <MetricCard
            label="Baseline false positives"
            value={String(s.baseline_false_positives)}
            tone={s.baseline_false_positives === 0 ? "good" : "bad"}
          />
          <MetricCard label="Negative controls" value={String(s.controls)} />
        </div>
      )}

      {s && (
        <div className="panel">
          <h2>Detection by infection class</h2>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart
              data={Object.entries(s.detection_by_class).map(([cls, rate]) => {
                const [caught, total] = rate.split("/").map(Number);
                return { cls, pct: total ? (caught / total) * 100 : 0, rate };
              })}
              margin={{ left: -20, right: 10 }}
            >
              <CartesianGrid stroke={COLORS.line} strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="cls" stroke={COLORS.inkFaint} fontSize={11} tickLine={false} />
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
                formatter={(_v, _n, entry) => [String(entry.payload.rate), "detected"]}
              />
              <Bar dataKey="pct" radius={[3, 3, 0, 0]}>
                {Object.entries(s.detection_by_class).map(([cls], i) => (
                  <Cell key={cls} fill={i % 2 === 0 ? COLORS.accent : COLORS.suspect} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      <div>
        <h2>Run history</h2>
        {history.length === 0 ? (
          <div className="panel muted">No real-corpus demo runs yet.</div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Run</th>
                <th>Solids tested</th>
                <th>Baseline clean</th>
                <th>False positives</th>
                <th>When</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {history.map((h) => (
                <tr key={h.run_id} className="clickable" onClick={() => navigate(`/real/${h.run_id}`)}>
                  <td className="muted">{h.label || h.run_id}</td>
                  <td>{h.real_solids_tested}</td>
                  <td>
                    {h.baseline_clean}/{h.real_solids_tested}
                  </td>
                  <td style={{ color: h.baseline_false_positives === 0 ? "var(--clean)" : "var(--malformed)" }}>
                    {h.baseline_false_positives}
                  </td>
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
