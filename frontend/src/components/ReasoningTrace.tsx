export default function ReasoningTrace({ lines }: { lines: string[] }) {
  return (
    <div
      className="panel"
      style={{ fontSize: 12.5, lineHeight: 1.7, background: "var(--panel-raised)" }}
    >
      {lines.map((line, i) => (
        <div key={i} style={{ display: "flex", gap: 10 }}>
          <span className="faint" style={{ flexShrink: 0, width: 18, textAlign: "right" }}>
            {i + 1}
          </span>
          <span style={{ color: line.startsWith("->") ? "var(--ink)" : "var(--ink-dim)" }}>
            {line}
          </span>
        </div>
      ))}
    </div>
  );
}
