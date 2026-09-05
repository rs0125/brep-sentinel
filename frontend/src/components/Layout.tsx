import { NavLink, Outlet, useLocation } from "react-router-dom";
import { Gauge, Globe, History as HistoryIcon, Layers, Shield, UploadCloud } from "lucide-react";
import { useApiHealth } from "../hooks/useApiHealth";

const NAV = [
  { to: "/", label: "Overview", end: true, icon: Gauge },
  { to: "/upload", label: "Upload", icon: UploadCloud },
  { to: "/history", label: "History", icon: HistoryIcon },
  { to: "/batch", label: "Batch dashboard", icon: Layers },
  { to: "/real", label: "Real corpus", icon: Globe },
];

const TITLES: Record<string, string> = {
  "/": "Overview",
  "/upload": "Adjudicate a file",
  "/history": "Single-file history",
  "/batch": "Batch pipeline",
  "/real": "Real-corpus demo",
};

function pageTitle(pathname: string): string {
  if (TITLES[pathname]) return TITLES[pathname];
  if (pathname.startsWith("/batch/")) return "Batch report";
  if (pathname.startsWith("/real/")) return "Real-corpus report";
  return "brep-sentinel";
}

function StatusDot() {
  const status = useApiHealth();
  const color =
    status === "online" ? "var(--accent)" : status === "offline" ? "var(--danger)" : "var(--ink-faint)";
  const label = status === "online" ? "API online" : status === "offline" ? "API unreachable" : "Checking…";
  return (
    <div className="row" style={{ gap: 8 }}>
      <span
        style={{
          width: 7,
          height: 7,
          borderRadius: "50%",
          background: color,
          flexShrink: 0,
          boxShadow: status === "online" ? `0 0 10px ${color}` : "none",
        }}
        className={status === "online" ? "pulse-dot" : undefined}
      />
      <span className="faint">{label}</span>
    </div>
  );
}

export default function Layout() {
  const location = useLocation();

  return (
    <div style={{ display: "flex", minHeight: "100vh" }}>
      <div className="ambient-bg" />
      <aside
        style={{
          width: 232,
          flexShrink: 0,
          borderRight: "1px solid var(--line)",
          padding: "22px 16px",
          display: "flex",
          flexDirection: "column",
          gap: 26,
        }}
      >
        <div className="row" style={{ gap: 9 }}>
          <div
            style={{
              width: 32,
              height: 32,
              borderRadius: 9,
              background: "var(--accent-dim)",
              border: "1px solid rgba(46,230,107,0.5)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "var(--accent-neon)",
              flexShrink: 0,
              boxShadow: "0 0 18px -2px rgba(57,255,20,0.55)",
            }}
          >
            <Shield size={16} strokeWidth={2.25} />
          </div>
          <div>
            <div style={{ fontFamily: "var(--font-display)", fontWeight: 800, fontSize: 15.5 }}>
              brep-sentinel
            </div>
            <div className="faint" style={{ fontFamily: "var(--font-body)" }}>
              CAD malware analysis
            </div>
          </div>
        </div>
        <nav className="stack" style={{ gap: 3 }}>
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              style={({ isActive }) => ({
                display: "flex",
                alignItems: "center",
                gap: 10,
                padding: "9px 12px",
                borderRadius: 8,
                fontSize: 13.5,
                fontWeight: 500,
                color: isActive ? "var(--accent-neon)" : "var(--ink-dim)",
                background: isActive ? "var(--accent-dim)" : "transparent",
                boxShadow: isActive ? "inset 0 0 0 1px rgba(46,230,107,0.3)" : "none",
              })}
            >
              <item.icon size={15} strokeWidth={2} />
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="stack" style={{ gap: 10, marginTop: "auto" }}>
          <StatusDot />
          <div className="faint">
            cross-kernel differential parsing +<br />
            invariant-based adjudication
          </div>
        </div>
      </aside>
      <main style={{ flex: 1, display: "flex", flexDirection: "column" }}>
        <header
          style={{
            borderBottom: "1px solid var(--line)",
            padding: "18px 36px",
            fontFamily: "var(--font-display)",
            fontWeight: 700,
            fontSize: 14.5,
            color: "var(--ink-dim)",
          }}
        >
          {pageTitle(location.pathname)}
        </header>
        <div style={{ padding: "32px 36px", maxWidth: 1140 }}>
          <Outlet />
        </div>
      </main>
    </div>
  );
}
