import type { ValidityReport } from "../lib/types";

const INVARIANT_LABELS: Record<string, string> = {
  euler_poincare: "Euler-Poincaré",
  shell_closure: "Shell closure",
  orientation_coherence: "Orientation coherence",
  degeneracy: "Degeneracy",
};

export default function InvariantPanel({
  title,
  report,
}: {
  title: string;
  report: ValidityReport;
}) {
  return (
    <div className="panel stack" style={{ gap: 10 }}>
      <div className="row" style={{ justifyContent: "space-between" }}>
        <h3>{title}</h3>
        <span style={{ color: report.valid ? "var(--clean)" : "var(--malformed)", fontSize: 12 }}>
          {report.valid ? "valid" : "invalid"}
        </span>
      </div>
      <div className="stack" style={{ gap: 6 }}>
        {Object.entries(report.invariants).map(([key, check]) => (
          <div key={key} className="row" style={{ justifyContent: "space-between", fontSize: 12.5 }}>
            <span className={check.holds ? "muted" : ""} style={!check.holds ? { color: "var(--malformed)" } : undefined}>
              {INVARIANT_LABELS[key] ?? key}
            </span>
            <span className="faint" style={{ textAlign: "right", maxWidth: 220 }}>
              {check.detail}
            </span>
          </div>
        ))}
      </div>
      {report.parse_errors.length > 0 && (
        <div className="faint" style={{ color: "var(--malformed)" }}>
          parse errors: {report.parse_errors.join("; ")}
        </div>
      )}
    </div>
  );
}
