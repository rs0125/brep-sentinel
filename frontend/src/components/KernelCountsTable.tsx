import type { Counts } from "../lib/types";

const LABELS: Record<keyof Counts, string> = {
  V: "Vertices (V)",
  E: "Edges (E)",
  F: "Faces (F)",
  S: "Shells (S)",
  R: "Inner loops (R)",
};

export default function KernelCountsTable({
  countsA,
  countsB,
}: {
  countsA: Counts;
  countsB: Counts;
}) {
  const keys = Object.keys(LABELS) as (keyof Counts)[];
  return (
    <table>
      <thead>
        <tr>
          <th>Topology</th>
          <th>Kernel A (tolerant)</th>
          <th>Kernel B (strict)</th>
        </tr>
      </thead>
      <tbody>
        {keys.map((k) => {
          const diff = countsA[k] !== countsB[k];
          return (
            <tr key={k}>
              <td className="muted">{LABELS[k]}</td>
              <td style={{ color: diff ? "var(--flagged)" : "var(--ink)" }}>{countsA[k]}</td>
              <td style={{ color: diff ? "var(--flagged)" : "var(--ink)" }}>{countsB[k]}</td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
