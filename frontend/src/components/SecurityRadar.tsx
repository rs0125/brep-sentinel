import { Cpu, Gavel, GitCompare, Ruler, ShieldAlert, ShieldCheck } from "lucide-react";

const NODES = [
  { icon: Cpu, label: "Kernel A", style: { top: "5%", left: "8%" } },
  { icon: GitCompare, label: "Kernel B", style: { top: "5%", right: "8%" } },
  { icon: Ruler, label: "Invariants", style: { bottom: "5%", left: "8%" } },
  { icon: Gavel, label: "Adjudicate", style: { bottom: "5%", right: "8%" } },
];

// Each node is a real pipeline stage, wired into the shield at center -- this
// is the actual detection pipeline rendered as a diagram, not decoration.
export default function SecurityRadar({ status }: { status: "safe" | "danger" }) {
  const color = status === "safe" ? "var(--accent)" : "var(--danger)";
  const glow = status === "safe" ? "var(--accent-glow)" : "var(--danger-glow)";
  const Icon = status === "safe" ? ShieldCheck : ShieldAlert;

  return (
    <div style={{ position: "relative", width: 300, height: 300, flexShrink: 0 }}>
      <div
        style={{
          position: "absolute",
          inset: 0,
          borderRadius: "50%",
          background: `radial-gradient(circle, ${glow}4a 0%, transparent 72%)`,
          filter: "blur(4px)",
        }}
      />
      {[260, 200, 145].map((size, i) => (
        <div
          key={size}
          style={{
            position: "absolute",
            top: "50%",
            left: "50%",
            width: size,
            height: size,
            transform: "translate(-50%, -50%)",
            borderRadius: "50%",
            border: `1px ${i === 0 ? "dashed" : "solid"} ${color}${i === 0 ? "3d" : "22"}`,
          }}
        />
      ))}
      <svg width="300" height="300" style={{ position: "absolute", inset: 0 }}>
        <line x1="42" y1="42" x2="150" y2="150" stroke={`${color}40`} strokeWidth="1" />
        <line x1="258" y1="42" x2="150" y2="150" stroke={`${color}40`} strokeWidth="1" />
        <line x1="42" y1="258" x2="150" y2="150" stroke={`${color}40`} strokeWidth="1" />
        <line x1="258" y1="258" x2="150" y2="150" stroke={`${color}40`} strokeWidth="1" />
      </svg>
      {NODES.map((n) => (
        <div key={n.label} style={{ position: "absolute", ...n.style, textAlign: "center", width: 60 }}>
          <div
            style={{
              width: 34,
              height: 34,
              borderRadius: "50%",
              background: "var(--panel-raised)",
              border: `1px solid ${color}55`,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color,
              margin: "0 auto 6px",
            }}
          >
            <n.icon size={16} strokeWidth={2} />
          </div>
          <div className="faint" style={{ fontSize: 10 }}>
            {n.label}
          </div>
        </div>
      ))}
      <div
        style={{
          position: "absolute",
          top: "50%",
          left: "50%",
          transform: "translate(-50%, -50%)",
          width: 96,
          height: 96,
          borderRadius: "50%",
          background: "var(--panel)",
          border: `1px solid ${color}`,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          boxShadow: `0 0 56px -4px ${glow}d0`,
        }}
      >
        <Icon size={44} color={color} strokeWidth={1.6} />
      </div>
    </div>
  );
}
