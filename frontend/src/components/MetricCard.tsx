export default function MetricCard({
  label,
  value,
  tone = "default",
}: {
  label: string;
  value: string;
  tone?: "default" | "good" | "bad";
}) {
  const color =
    tone === "good" ? "var(--accent)" : tone === "bad" ? "var(--danger)" : "var(--ink)";
  return (
    <div className="panel" style={{ minWidth: 160, borderTop: `2px solid ${tone === "default" ? "var(--line)" : color}` }}>
      <div className="faint" style={{ marginBottom: 8, fontFamily: "var(--font-body)", fontSize: 12.5, textTransform: "none" }}>
        {label}
      </div>
      <div style={{ fontFamily: "var(--font-display)", fontSize: 28, fontWeight: 800, color }}>
        {value}
      </div>
    </div>
  );
}
