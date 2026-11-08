# Water composition

The V8 runner builds named basins and coastal tiles, combines them into a
prefill, then fills and composes the remaining ocean and enclosed water.
Use the [V8 pipeline command](../v7-pipeline/README.md) for a complete rebuild.
[Water stage contracts](DIRECT.md) describe the inputs and outputs of each stage.

## Experimental numeric-column prefill resolver

`build_prefill.py --column-engine` factors layer identity, allowed codes and
explicit override policy once, resolves validated row spans in NumPy columns,
and passes those columns directly into the existing RLE writer. The default
remains the original tuple resolver until complete current-input parity and
separate wall-clock measurements establish a useful gain.

The numeric resolver supports arbitrary layer names, any number of integer
priority levels, gaps and declared multi-level overrides. It retains every
source breakpoint. Internally overlapping priority bands use the original
resolver, preserving duplicate/ambiguous-assignment and undeclared-override
errors. It imposes no geography, current-layer-count, resource or map-policy
threshold. No process, custom compiler or ctypes bridge is used.

Tests compare all numeric boundaries/codes and overlap counts against the
unchanged resolver across 750 deterministic randomized cases, including valid
multi-priority overlays, plus adversarial policy/physical-water cases. A tiny
complete prefill fixture compares both RLE files and every scientific audit
field. These are correctness tests, not global parity or speed evidence.

`../v7-pipeline/benchmark_prefill_columns.py --plan PINNED_PLAN --input-root ROOT
--out NEW_DIR` runs the complete original and numeric producers sequentially
through their Python APIs, forwarding only explicit research opt-ins. It records
all script identities and UTC trial anchors, then checks every RLE byte and
scientific audit field outside the measurement. `--candidate-first` reverses
cache order. The ordinary producer still validates the plan and all input and
lineage pins; this does not manufacture an admission or replace missing layers.

## Experimental shared verified water inputs

`VerifiedWaterInputs` is an optional Python-API context for coast, basin and
coverage-verifier calls. It captures four SHA-pinned physical/final-land streams
in private, unlinked read-only files and builds one existing exact coastal span
index. Consumers must match the role, original path, hash and grid dimensions.
This is immutable data sharing, not a cache that trusts pathnames or timestamps.
Original files and helper code are checked again before successful context exit.
The extra shared-generation provenance records all four input and helper hashes.
The context requires an explicit existing workspace `work_root` for its private
copies, even if Python cached a different temporary directory earlier. Foreign
cached helper modules are rejected before snapshots are made.

Join all consumer threads before leaving the context. Admit/checkpoint results
only after successful context exit; per-job manifests written earlier are not
proof that the complete shared generation passed its final source checks.

Standalone CLI behavior and ordinary pipeline orchestration remain unchanged.
Tiny tests compare exact coastal tiles and all three basin classifiers, check
wrapped crop order, reject mismatched pins, and show that changing an original
file cannot change the snapshot and causes successful-exit validation to fail.
Global matching/current-input timings are still required before orchestration
adopts this path. Include snapshot creation, index construction and final source
checks in any reported full-stage timing; a prebuilt index is not free work.

`--column-engine --arrow-spans` additionally streams canonical assignment JSON
through the existing PyArrow binding. Coordinates stay in numeric buffers;
rule/member Python objects are created only for a reference-policy fallback.
The original reader retains aliases, numeric coercions, duplicate-key behavior,
noncanonical Unicode/newline representations and diagnostics. A partial-stream
fallback resumes after exactly the spans already delivered, without omitting or
duplicating records. Dense/sparse row coverage, duplicate-row continuation,
bounds, ordering and required identities remain validated. No current geography,
layer count or map decision chooses the parser. The default reader is unchanged.

The prefill pair harness accepts `--arrow-spans` for its candidate only. Complete
small fixtures compare all three engines' RLE bytes and scientific audits;
streaming tests cover compressed inputs, legacy forms and late fallback. Global
current-prefill parity and elapsed-time evidence are still required for adoption.
