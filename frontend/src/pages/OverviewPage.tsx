import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowRight, LayoutGrid } from "lucide-react";
import {
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { getOverview } from "../lib/api";
import type { ActivityEntry, OverviewResponse, Verdict } from "../lib/types";
import { COLORS, VERDICT_COLOR, VERDICT_LABEL } from "../lib/theme";
import MetricCard from "../components/MetricCard";
import VerdictBadge from "../components/VerdictBadge";
import SecurityRadar from "../components/SecurityRadar";

const tooltipStyle = {
  background: COLORS.panelRaised,
  border: `1px solid ${COLORS.lineStrong}`,
  borderRadius: 8,
  fontFamily: "IBM Plex Mono, monospace",
  fontSize: 12,
  color: COLORS.ink,
};

function activityLabel(entry: ActivityEntry): string {
  if (entry.kind === "single") return (entry.filename as string) ?? "adjudication";
  if (entry.kind === "batch") return (entry.label as string) || "batch run";
  if (entry.kind === "real") return (entry.label as string) || "real-corpus demo";
  return "real_corpus ingest";
}

function activityLink(entry: ActivityEntry): string | null {
  if (entry.kind === "batch") return `/batch/${entry.run_id}`;
  if (entry.kind === "real") return `/real/${entry.run_id}`;
  return null;
}

export default function OverviewPage() {
  const [data, setData] = useState<OverviewResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    getOverview()
      .then(setData)
      .catch((e) => setError(e instanceof Error ? e.message : String(e)));
  }, []);

  if (error) return <div style={{ color: "var(--danger)" }}>{error}</div>;
  if (!data) return <div className="muted">Loading…</div>;

  const totalSingle = data.counts_by_kind.single ?? 0;
  const totalBatch = data.counts_by_kind.batch ?? 0;
  const totalReal = data.counts_by_kind.real ?? 0;
  const totalFlagged =
    (data.verdict_distribution.flagged ?? 0) + (data.verdict_distribution.malformed ?? 0);
  const radarStatus: "safe" | "danger" = totalFlagged > 0 ? "danger" : "safe";

  const pieData = Object.entries(data.verdict_distribution).map(([verdict, count]) => ({
    verdict,
    count,
  }));

  const trendData = data.batch_metrics_series.map((p) => ({
    ...p,
    fp_pct: p.false_positive_rate * 100,
    recall_pct: p.adjudication_recall * 100,
  }));

  return (
    <div className="stack" style={{ gap: 32 }}>
      {/* --- hero ------------------------------------------------------- */}
      <div
        className="panel-neon row"
        style={{ justifyContent: "space-between", padding: "36px 44px", gap: 24 }}
      >
        <div className="stack" style={{ gap: 18, maxWidth: 460, position: "relative", zIndex: 1 }}>
          <span className={`pill ${radarStatus === "safe" ? "pill-safe" : "pill-danger"}`}>
            <LayoutGrid size={13} />
            {radarStatus === "safe" ? "No active threats" : `${totalFlagged} file(s) need review`}
          </span>
          <div>
            <h1 className={radarStatus === "safe" ? "glow-text" : "glow-text-danger"} style={{ fontSize: 32 }}>
              Catch malformed CAD before it ships
            </h1>
            <p style={{ margin: 0 }}>
              Two independent kernels parse every file. When their interpretations diverge,
              validity invariants decide which one is wrong — before manufacturing, with no
              golden model and no exploit signature required.
            </p>
          </div>
          <div className="row" style={{ gap: 10 }}>
            <button className="primary" onClick={() => navigate("/upload")}>
              Adjudicate a file
              <ArrowRight size={15} />
            </button>
            <button onClick={() => navigate("/batch")}>Run batch pipeline</button>
          </div>
        </div>
        <div style={{ position: "relative", zIndex: 1 }}>
          <SecurityRadar status={radarStatus} />
        </div>
      </div>

      <div className="row" style={{ gap: 12, flexWrap: "wrap" }}>
        <MetricCard label="Files adjudicated" value={String(totalSingle)} />
        <MetricCard
          label="Flagged / malformed"
          value={String(totalFlagged)}
          tone={totalFlagged > 0 ? "bad" : "good"}
        />
        <MetricCard label="Batch pipeline runs" value={String(totalBatch)} />
        <MetricCard label="Real-corpus demo runs" value={String(totalReal)} />
      </div>

      <div className="row" style={{ gap: 20, alignItems: "stretch", flexWrap: "wrap" }}>
        <div className="panel" style={{ flex: "1 1 320px" }}>
          <h2>Verdict distribution</h2>
          {pieData.length === 0 ? (
            <div className="muted">No single-file adjudications yet.</div>
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie
                  data={pieData}
                  dataKey="count"
                  nameKey="verdict"
                  innerRadius={55}
                  outerRadius={85}
                  paddingAngle={2}
                >
                  {pieData.map((entry) => (
                    <Cell key={entry.verdict} fill={VERDICT_COLOR[entry.verdict]} stroke={COLORS.bg} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={tooltipStyle}
                  formatter={(value, name) => [value, VERDICT_LABEL[String(name)] ?? String(name)]}
                />
                <Legend
                  formatter={(value) => (
                    <span style={{ color: COLORS.inkDim, fontSize: 12, fontFamily: "Inter" }}>
                      {VERDICT_LABEL[String(value)] ?? String(value)}
                    </span>
                  )}
                />
              </PieChart>
            </ResponsiveContainer>
          )}
        </div>

        <div className="panel" style={{ flex: "2 1 420px" }}>
          <h2>Batch detector performance over time</h2>
          {trendData.length === 0 ? (
            <div className="muted">
              No batch runs yet. Run the pipeline from the{" "}
              <Link to="/batch">batch dashboard</Link> to see a trend here.
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={trendData} margin={{ left: -20, right: 10 }}>
                <XAxis dataKey="label" stroke={COLORS.inkFaint} fontSize={11} tickLine={false} />
                <YAxis
                  stroke={COLORS.inkFaint}
                  fontSize={11}
                  domain={[0, 100]}
                  tickFormatter={(v) => `${v}%`}
                  tickLine={false}
                />
                <Tooltip contentStyle={tooltipStyle} formatter={(v) => `${Number(v).toFixed(1)}%`} />
                <Legend wrapperStyle={{ fontSize: 12, color: COLORS.inkDim, fontFamily: "Inter" }} />
                <Line
                  type="monotone"
                  dataKey="fp_pct"
                  name="False-positive rate"
                  stroke={COLORS.malformed}
                  strokeWidth={2}
                  dot={{ r: 3 }}
                />
                <Line
                  type="monotone"
                  dataKey="recall_pct"
                  name="Adjudication recall"
                  stroke={COLORS.accent}
                  strokeWidth={2}
                  dot={{ r: 3 }}
                />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      <div>
        <h2>Recent activity</h2>
        {data.recent_activity.length === 0 ? (
          <div className="panel muted">Nothing has been run yet.</div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Run</th>
                <th>Type</th>
                <th>Result</th>
                <th>When</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {data.recent_activity.map((entry) => {
                const link = activityLink(entry);
                return (
                  <tr
                    key={entry.run_id}
                    className={link ? "clickable" : undefined}
                    onClick={() => link && navigate(link)}
                  >
                    <td>{activityLabel(entry)}</td>
                    <td className="muted">{entry.kind}</td>
                    <td>
                      {entry.kind === "single" ? (
                        <VerdictBadge verdict={entry.verdict as Verdict} size="sm" />
                      ) : entry.kind === "batch" ? (
                        <span className="faint">
                          FP {((entry.false_positive_rate as number) * 100).toFixed(0)}% · recall{" "}
                          {((entry.adjudication_recall as number) * 100).toFixed(0)}%
                        </span>
                      ) : entry.kind === "real" ? (
                        <span className="faint">
                          {String(entry.baseline_clean)}/{String(entry.real_solids_tested)} clean
                        </span>
                      ) : (
                        <span className="faint">refreshed</span>
                      )}
                    </td>
                    <td className="faint">{new Date(entry.created_at).toLocaleString()}</td>
                    <td>{link && <ArrowRight size={14} color="var(--ink-faint)" />}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
