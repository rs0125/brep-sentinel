// Recharts renders raw SVG and doesn't reliably resolve CSS custom
// properties in every context, so chart code uses these hex constants
// directly. Keep in sync with the --tokens in src/index.css.
export const COLORS = {
  bg: "#060a08",
  panel: "#0d1512",
  panelRaised: "#121d18",
  line: "rgba(255,255,255,0.08)",
  lineStrong: "rgba(255,255,255,0.16)",
  ink: "#eef4f1",
  inkDim: "#9fb3ab",
  inkFaint: "#5f7369",
  accent: "#2ee66b",
  accentGlow: "#39ff6a",
  accentNeon: "#39ff14",
  danger: "#ff3b3b",
  dangerNeon: "#ff1744",
  clean: "#2ee66b",
  flagged: "#ffb020",
  malformed: "#ff3b3b",
  suspect: "#e93de9",
} as const;

export const VERDICT_COLOR: Record<string, string> = {
  clean: COLORS.clean,
  flagged: COLORS.flagged,
  malformed: COLORS.malformed,
  benign_ambiguity: COLORS.suspect,
};

export const VERDICT_LABEL: Record<string, string> = {
  clean: "Clean",
  flagged: "Flagged",
  malformed: "Malformed",
  benign_ambiguity: "Suspect",
};
