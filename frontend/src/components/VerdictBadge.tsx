import { AlertTriangle, CheckCircle2, HelpCircle, XOctagon } from "lucide-react";
import type { Verdict } from "../lib/types";
import { VERDICT_COLOR, VERDICT_LABEL } from "../lib/theme";

const VERDICT_ICON: Record<Verdict, typeof CheckCircle2> = {
  clean: CheckCircle2,
  flagged: AlertTriangle,
  malformed: XOctagon,
  benign_ambiguity: HelpCircle,
};

export default function VerdictBadge({
  verdict,
  size = "md",
}: {
  verdict: Verdict;
  size?: "sm" | "md" | "lg";
}) {
  const color = VERDICT_COLOR[verdict];
  const Icon = VERDICT_ICON[verdict];
  const pad = size === "lg" ? "10px 18px" : size === "sm" ? "2px 8px" : "5px 12px";
  const font = size === "lg" ? "18px" : size === "sm" ? "11px" : "13px";
  const iconSize = size === "lg" ? 18 : size === "sm" ? 12 : 14;

  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 7,
        color,
        background: `${color}1f`,
        border: `1px solid ${color}66`,
        borderRadius: 999,
        padding: pad,
        fontSize: font,
        fontFamily: "var(--font-mono)",
        fontWeight: 600,
        lineHeight: 1,
        boxShadow: size === "lg" ? `0 0 24px -6px ${color}80` : "none",
      }}
    >
      <Icon size={iconSize} strokeWidth={2.25} />
      {VERDICT_LABEL[verdict]}
    </span>
  );
}
