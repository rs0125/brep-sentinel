import { useRef, useState } from "react";
import { adjudicateFile } from "../lib/api";
import type { AdjudicateResponse } from "../lib/types";
import ResultView from "../components/ResultView";

export default function UploadPage() {
  const [dragOver, setDragOver] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AdjudicateResponse | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  async function submit(file: File) {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await adjudicateFile(file);
      setResult(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  function onDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) submit(file);
  }

  return (
    <div className="stack" style={{ gap: 24 }}>
      <div>
        <h1>Adjudicate a STEP file</h1>
        <p className="muted" style={{ margin: 0 }}>
          Two independent kernels parse the file, invariants check each interpretation,
          and divergence is adjudicated into a verdict.
        </p>
      </div>

      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
        style={{
          border: `1px dashed ${dragOver ? "var(--accent)" : "var(--line-strong)"}`,
          borderRadius: 16,
          padding: "48px 24px",
          textAlign: "center",
          cursor: "pointer",
          background: dragOver ? "var(--panel-raised)" : "var(--panel)",
        }}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".step,.stp"
          style={{ display: "none" }}
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) submit(file);
          }}
        />
        <div style={{ fontFamily: "var(--font-display)", fontSize: 15, marginBottom: 6 }}>
          Drop a .step file, or click to choose one
        </div>
        <div className="faint">Max 25 MB</div>
      </div>

      {loading && (
        <div className="muted">Running kernel A, kernel B, invariants, adjudication…</div>
      )}

      {error && (
        <div className="panel" style={{ borderColor: "var(--malformed)", color: "var(--malformed)" }}>
          Could not adjudicate this file: {error}
        </div>
      )}

      {result && <ResultView result={result} runId={result.run_id} />}
    </div>
  );
}
