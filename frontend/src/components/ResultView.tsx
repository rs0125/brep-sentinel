import type { AdjudicateResult } from "../lib/types";
import VerdictBadge from "./VerdictBadge";
import ReasoningTrace from "./ReasoningTrace";
import KernelCountsTable from "./KernelCountsTable";
import InvariantPanel from "./InvariantPanel";

export default function ResultView({
  result,
  runId,
}: {
  result: AdjudicateResult;
  runId?: string;
}) {
  return (
    <div className="stack" style={{ gap: 20 }}>
      <div className="panel row" style={{ justifyContent: "space-between" }}>
        <div>
          {runId && (
            <div className="faint" style={{ marginBottom: 8 }}>
              run {runId}
            </div>
          )}
          <VerdictBadge verdict={result.verdict} size="lg" />
        </div>
        <div className="faint" style={{ textAlign: "right" }}>
          {result.adjudication.convergent ? "convergent" : "divergent"} · healing ops{" "}
          {result.adjudication.healing_ops}
        </div>
      </div>

      <div>
        <h2>Adjudication reasoning</h2>
        <ReasoningTrace lines={result.adjudication.reasoning} />
      </div>

      <div>
        <h2>Topology (kernel A vs kernel B)</h2>
        <div className="panel">
          <KernelCountsTable countsA={result.kernel_a.counts} countsB={result.kernel_b.counts} />
        </div>
      </div>

      <div className="row" style={{ alignItems: "flex-start", gap: 16 }}>
        <div style={{ flex: 1 }}>
          <InvariantPanel title="Kernel A — tolerant/healing" report={result.validity_a} />
        </div>
        <div style={{ flex: 1 }}>
          <InvariantPanel title="Kernel B — strict/literal" report={result.validity_b} />
        </div>
      </div>

      {result.kernel_a.healing_log.length > 0 && (
        <div>
          <h2>Healing performed by kernel A</h2>
          <div className="panel faint" style={{ lineHeight: 1.8 }}>
            {result.kernel_a.healing_log.map((op, i) => (
              <div key={i}>{op}</div>
            ))}
          </div>
        </div>
      )}

      <div>
        <h2>Geometric advisory</h2>
        {result.advisory.any ? (
          <div className="stack" style={{ gap: 8 }}>
            {result.advisory.flags.map((f, i) => (
              <div key={i} className="panel" style={{ borderColor: "var(--flagged)" }}>
                <div style={{ color: "var(--flagged)", fontWeight: 600, marginBottom: 4 }}>
                  {f.type.replace(/_/g, " ")}
                </div>
                <div className="muted" style={{ fontSize: 12.5 }}>
                  {f.detail}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="panel muted">No geometric weakening flags on this file.</div>
        )}
      </div>
    </div>
  );
}
