// Mirrors the JSON shapes produced by brep_sentinel's dataclasses (common.py,
// adjudicate.py, invariants.py, advisory.py, evaluate.py) as passed through
// unchanged by api/services/pipeline.py. Kept loosely typed in a few nested
// spots (rows, confusion_matrix, files/controls) rather than re-declaring
// every field of a shape the API doesn't guarantee to freeze.

export type Verdict = "clean" | "benign_ambiguity" | "flagged" | "malformed";

export interface Counts {
  V: number;
  E: number;
  F: number;
  S: number;
  R: number;
}

export interface VertexD {
  id: number;
  xyz: [number, number, number];
}

export interface EdgeD {
  id: number;
  curve_type: string;
  vertex_ids: number[];
  length: number;
  face_ids: number[];
}

export interface FaceD {
  id: number;
  surface_type: string;
  orientation: boolean;
  outer_loop_edges: number[];
  inner_loops: number[][];
  area: number;
  normal: number[];
}

export interface ShellD {
  id: number;
  kind: "outer" | "void" | string;
  face_ids: number[];
  closed: boolean;
}

export interface Descriptor {
  source_file: string;
  file_sha256: string;
  kernel_name: string;
  kernel_version: string;
  healing_enabled: boolean;
  schema_version: string;
  vertices: VertexD[];
  edges: EdgeD[];
  faces: FaceD[];
  shells: ShellD[];
  healing_log: string[];
  parse_errors: string[];
  edge_uses: Record<string, unknown>;
  counts: Counts;
}

export interface InvariantCheck {
  holds: boolean;
  detail: string;
  [extra: string]: unknown;
}

export interface ValidityReport {
  kernel_name: string;
  kernel_version: string;
  source_file: string;
  file_sha256: string;
  counts: Counts;
  invariants: {
    euler_poincare: InvariantCheck;
    shell_closure: InvariantCheck;
    orientation_coherence: InvariantCheck;
    degeneracy: InvariantCheck;
  };
  failures: string[];
  valid: boolean;
  parse_errors: string[];
}

export interface Adjudication {
  source_file: string;
  verdict: Verdict;
  convergent: boolean;
  a_valid: boolean;
  b_valid: boolean;
  count_diffs: Record<string, { kernel_a: number; kernel_b: number }>;
  structural_diffs: Array<Record<string, unknown>>;
  a_failures: string[];
  b_failures: string[];
  healing_ops: number;
  reasoning: string[];
}

export interface AdvisoryFlag {
  type: string;
  detail: string;
}

export interface AdvisoryResult {
  any: boolean;
  flags: AdvisoryFlag[];
  bbox_diag: number;
}

export interface AdjudicateResult {
  verdict: Verdict;
  adjudication: Adjudication;
  kernel_a: Descriptor;
  kernel_b: Descriptor;
  validity_a: ValidityReport;
  validity_b: ValidityReport;
  advisory: AdvisoryResult;
}

export interface AdjudicateResponse extends AdjudicateResult {
  run_id: string;
  meta?: SingleHistoryEntry;
}

export interface SingleHistoryEntry {
  run_id: string;
  kind: "single";
  created_at: string;
  filename: string;
  verdict: Verdict;
  file_sha256: string;
  bytes: number;
}

export interface BatchMetrics {
  valid_files: number;
  false_positives: number;
  false_positive_rate: number;
  crafted_invalid: number;
  adjudication_recall: number;
  precision: number;
  weakening_total: number;
  weakening_caught_by_advisory: number;
  layered_recall: number;
}

export interface BatchCounts {
  clean: number;
  benign_perturbations: number;
  weakening_perturbations: number;
  adversarial_fixtures: number;
  total: number;
}

export interface BatchEvaluation {
  env: Record<string, unknown>;
  counts: BatchCounts;
  confusion_matrix: Record<string, Record<string, number>>;
  metrics: BatchMetrics;
  per_invariant_hits_on_crafted: Record<string, number>;
  false_positive_files: string[];
  rows: Array<Record<string, unknown>>;
}

export interface BatchRunResponse {
  run_id: string;
  out_dir: string;
  corpus_parts: number;
  perturbed_parts: number;
  fixture_parts: number;
  evaluation: BatchEvaluation;
  report_markdown: string;
}

export interface BatchHistoryEntry {
  run_id: string;
  kind: "batch";
  created_at: string;
  label?: string | null;
  total_files: number;
  false_positive_rate: number;
  adjudication_recall: number;
  layered_recall: number;
}

export interface RealRunSummary {
  real_solids_tested: number;
  baseline_clean: number;
  baseline_false_positives: number;
  detection_by_class: Record<string, string>;
  controls: number;
}

export interface RealRunResponse {
  run_id: string;
  out_dir: string;
  result: {
    source: string;
    files: Array<Record<string, unknown>>;
    controls: Array<Record<string, unknown>>;
    summary: RealRunSummary;
  };
}

export interface RealHistoryEntry extends RealRunSummary {
  run_id: string;
  kind: "real";
  created_at: string;
  label?: string | null;
}

export interface PipelineStage {
  stage: number | null;
  name: string;
  module: string;
  description: string;
}

export interface BatchMetricsPoint {
  run_id: string;
  label: string;
  created_at: string;
  false_positive_rate: number;
  adjudication_recall: number;
  layered_recall: number;
}

export interface ActivityEntry {
  run_id: string;
  kind: "single" | "batch" | "real" | "ingest";
  created_at: string;
  [extra: string]: unknown;
}

export interface OverviewResponse {
  counts_by_kind: Record<string, number>;
  verdict_distribution: Record<string, number>;
  batch_metrics_series: BatchMetricsPoint[];
  recent_activity: ActivityEntry[];
}
