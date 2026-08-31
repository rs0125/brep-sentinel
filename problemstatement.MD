PROBLEM STATEMENT: Adversarial Input Detection in CAD/B-rep File Exchange

Background: what a CAD file actually contains

Modern mechanical CAD does not store a 3D object as a picture or a simple list of points. It stores it as a Boundary Representation (B-rep). A B-rep describes a solid by its boundary, split into two coupled layers:

Geometry: the actual mathematical surfaces and curves — planes, cylinders, cones, NURBS/spline patches — each defined by continuous parameters (an axis, a radius, control points).
Topology: how those geometric pieces connect. A shell is made of faces, each face is bounded by edges, each edge meets vertices, and every face carries an orientation (which side is "inside" the solid). Topology is stored as explicit adjacency: this edge belongs to these two faces, this loop bounds this face, and so on.

The reason both layers exist is that geometry alone is ambiguous. Two cylinders touching in space don't tell you whether they form one watertight solid or two separate bodies — the topology is what says so. This is why B-rep is the interchange language between CAD, CAM (manufacturing), and CAE (simulation): it carries enough structure that mass properties, tool paths, and meshes all come out consistent.

The most common neutral file format for exchanging B-rep is STEP (ISO 10303, typically AP242). STEP is a text format: a long list of numbered entity records that reference each other by ID — a face record points to edge records, which point to vertex and curve records. Related binary formats (Parasolid X_B, ACIS SAT) encode the same face/edge/vertex/orientation structure.

A key mathematical fact: a valid solid's topology is not free-form. It must satisfy the Euler-Poincaré relation (V − E + F = 2(S − G) + ... , relating vertices, edges, faces, shells, and genus/holes). If the counts don't satisfy this, the "solid" is not a well-formed solid. This invariant is the closest thing B-rep has to a built-in checksum on its own correctness.

How CAD files get parsed and "repaired"

A STEP/B-rep file is not consumed directly. It is read by a geometric kernel — OpenCASCADE (open source), Parasolid, ACIS, CGM, etc. The kernel parses the text records, rebuilds the geometry and topology in memory, and hands a usable solid to the application.

Two facts about this step are central to the problem:

(a) Kernels are not interchangeable. Different kernels — and even different versions of the same kernel — interpret the same STEP file differently. This is well known enough that an entire industry (CADFix, CADDoctor) exists purely to convert and reconcile files across kernels. The STEP standard has enough ambiguity, and real files enough imperfections, that "the same file" does not reliably mean "the same solid" across tools.

(b) Kernels are deliberately forgiving. Real CAD files arrive with cracks, gaps, tolerance mismatches, overlapping faces, T-connections, tiny sliver faces, and invalid or missing topology — usually as honest byproducts of a failed Boolean operation, a units mismatch, or a lossy export. Because rejecting every imperfect file would make exchange unusable, kernels run model repair / healing: they silently stitch gaps, snap near-coincident vertices, fix orientation, and rebuild missing adjacency to force the input into a usable solid. Healing is designed to be maximally tolerant and to fix-and-continue without alarming the user.

That tolerance is the crux. Healing assumes every defect is accidental. It has no notion that a defect might be there on purpose.

What can be injected, and why the file is an attack surface

Because a CAD file is a structured input to a complex native parser, it is an attack surface — and this is not hypothetical. Vendors ship regular patches for it: maliciously crafted STEP, X_B, CATIA, and related files have produced memory-corruption, out-of-bounds-write, use-after-free, and remote-code-execution vulnerabilities in shipping CAD kernels (multiple 2022–2025 CVEs across major vendors). The file reaches victims through the ordinary channels — emailed project files, shared part libraries, supplier uploads.

The injectable threats fall into distinct classes, each abusing a different property of the format:

Parser-exploit entities: a topological reference or a length/count field crafted so that when the kernel parses it, it overflows a buffer or corrupts memory — leading to a crash or code execution. Critically, a healing pass may itself be the thing that touches the malformed entity and detonates it, because healing actively rewrites topology.
Kernel-divergent structures (a B-rep "polyglot"): a file deliberately built around a specification ambiguity so that Kernel A heals it into one solid and Kernel B heals it into a different solid. The displayed/approved model and the manufactured/downstream model are then not the same object. This is the CAD analogue of the parser-differential attacks already documented for URLs, HTTP, ZIP, and PDF — but for solid geometry, where "two interpretations" can mean two different physical parts.
Topology-encoded payload: data hidden not in the coordinates but in the topological layer — the ordering of face/edge adjacency, redundant or degenerate entities, or superfluous Euler operations that a display kernel ignores but a matching extractor can read back out. (Note: the existing academic field of 3D steganalysis targets meshes and vertex coordinates; it does not cover payloads hidden in B-rep topology.)
Structure-weakening edits: a topologically valid, clean-parsing file whose geometry has been subtly altered to degrade the physical part — an internal void, a local wall-thickness reduction, a stress-concentrating notch on a load path — so the printed/machined part fails in service while the file looks fine.
The gap

Three separate communities each see part of this and miss the rest:

CAD model repair / healing treats every invalid B-rep as accidental noise and is built to silently fix it. It asks "is this model broken?" — never "is it broken in a way that indicates an attack rather than an accident?" Its tolerance is exactly what an adversarial file exploits.
Security tooling (signature scanners, sandboxes, polyglot detectors, LangSec/parser-differential work) understands malformed input and parser divergence, but operates on document, executable, and web/protocol formats. It has no model of B-rep geometry or topology, so a well-formed file describing a sabotaged or kernel-divergent solid passes straight through.
Additive-manufacturing security detects the physical attack, but almost entirely during or after printing (acoustic, power, and side-channel monitoring), and/or relies on signing the file. By then the vulnerable kernel has already parsed the input, and signing does nothing about tampering that occurs before the signature or about a file that heals differently across kernels.

Nobody sits at the point where the file is parsed and connects (a) a bit/structure-level anomaly to (b) its geometric-topological legitimacy to (c) its physical consequence — before manufacturing, without a trusted reference model, and without needing to know the specific CVE in advance.

Problem statement

Design a static, pre-manufacturing analysis stage, positioned at the point where an untrusted CAD/B-rep file is ingested, that distinguishes adversarially malformed input from the ordinary accidental imperfections that CAD healing is meant to absorb — and does so reference-free (no trusted golden model) and exploit-agnostic (not dependent on a signature of a known CVE).

The central technical idea to be validated: because a valid B-rep must satisfy mathematical validity invariants (Euler-Poincaré / topological consistency / orientation coherence), a divergence between independent kernel interpretations of the same file can be adjudicated — not merely observed. That is, the system can determine which interpretation, if any, violates the invariants, and use the pattern of that violation to classify the input as accidental or adversarial. Plain parser-differential techniques (known for text/web formats) only tell you the parsers disagree; B-rep's invariants let you say who is wrong and whether the disagreement bears the signature of deliberate construction.

The load-bearing question

Everything rests on one thing: can adversarial invalidity be reliably separated from accidental invalidity using topological invariants, and does that separation catch real crafted inputs (parser-exploit entities, kernel-divergent polyglots, topology-encoded payloads) that a single forgiving kernel would silently accept? If yes, the approach is a genuine detection method. If the adjudication is fuzzy, it degrades to ordinary differential parsing applied to CAD, which is far less novel.

Proposed way to test it, minimally: take clean STEP parts; run them through two independent kernels (e.g., OpenCASCADE plus a second open parser) and confirm benign files converge to topologically valid, mutually consistent solids. Then plant each attack class — a malformed topology reference that one kernel silently "heals" into a different solid, a degenerate-entity payload, a structure-weakening edit — and measure whether an invariant check flags the divergence AND identifies which side violates B-rep validity, while clean variants pass. Convergence of benign files and correct adjudication of planted ones is the whole result.
