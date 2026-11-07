# Exact regional runtime

The mixed/regional handoff keeps every reviewed policy, source, line and WGS84
implementation pin. A separate `regional.request.runtime` inventory selects
`component_index.py`, `satellite_index.py` and `regional_runtime.py`. The hook
hashes those modules before loading and after execution, and reports their pins
and substitution names separately from the geographic evidence. Omitting this
inventory retains the reviewed reference engine.

The component index authenticates and validates the complete global run stream
once. Read-only mappings and vectorized integer counts replace repeated global
Python scans. Window statistics preserve root encounter order, complete global
populations and all four line-side counts. Whole-component runs are reused
within this invocation only. Every query checks generation/file identity, and
the complete input hashes are checked again after the writer finishes.

The satellite index searches row intervals, including wrapped longitudes and
all longitudes near a pole. Its rectangle contains every pair passing the
reviewed spherical lower bound: a spherical path of angular length theta stays
within theta latitude of its start, so integrating cos(latitude) times longitude
change bounds its longitude excursion. The existing lower bounds and scalar
WGS84 solver then run in the same per-parent order with the same incumbents.
Every larger competitor remains eligible; there are no centroid approximations,
new geographic thresholds, memory limits or watchdogs.

Differential tests cover complete/partial counts, root order, sparse IDs, empty
rows, corrupt/mutated streams, full runs, exact solver calls, competing targets,
ties, source groups, protected roots, wrap and polar queries.

## Reproduce a full-stage comparison

Use the original stage's `checkpoints/regional/complete.json` admission and a
fresh persistent output directory. Preserve its interpreter and dependency
environment, set `PROJ_NETWORK=OFF`, and use a persistent workspace `TMPDIR`.
Run sequentially, without other heavy jobs:

```sh
python scripts/v7-pipeline/benchmark_regional.py \
  --admitted /workspace/run/checkpoints/regional/complete.json \
  --out /workspace/benchmarks/regional-reference --profile
python scripts/v7-pipeline/benchmark_regional.py \
  --admitted /workspace/run/checkpoints/regional/complete.json \
  --out /workspace/benchmarks/regional-indexed \
  --producer-root "$PWD"
```

The benchmark reruns all selected-source resolution and the complete writer.
It compares byte hashes of rows, runs and changes, every regional decision and
proposal trace, selected affiliation statistics and the full scientific report.
Only request hashes, timing and explicitly recorded runtime provenance may
differ. `--producer-root` binds the new mixed driver and point resolver, selects
their pinned point/polygon/regional runtimes, and reuses the original Stage 2
report and approval unchanged. It requires an identical validator and identical
reviewed regional algorithm hashes. The report comparison verifies each declared
code/path/request rebinding before normalizing it; it never ignores scientific
claims or arbitrary hashes. `--runtime-root` alone selects just the regional
index while retaining the admitted mixed driver.

`--profile` adds cumulative cProfile results; compare unprofiled wall
times for speed ratios. `--summarize --out DIR` can finish validation of a
completed replay interrupted during analysis, without rerunning the producer.

These outputs remain provisional, non-publishable research. Runtime equivalence
does not complete the pending inventory or approve geography.

## Full local-input replay, 2026-11-07

The retained complete reference stage took about 515 seconds (512.74 seconds
inside the producer). Regional indexing alone replayed in 444.50 seconds.
Combining the point, polygon/Bering and regional runtimes replayed the complete
stage in **239.81 seconds**, including source resolution, validation and writer:
**2.15 times faster, about 53% less wall time**. Its producer measured 238.89
seconds. Inputs were already local; heavy stages ran sequentially.

All three output hashes match exactly:

- Rows: `8922efb4b90021e36e5491ddf65ab1eaa7f6961dfc0f81fadfbfecc45f510674`
- Runs: `c15da5eb03d7c938194ea056cdfaf092d90f18fa4ed604f42466951316ed0b20`
- Changes: `06ef76b8bf097cd65781315ac8bb3123fc55367c99603e5d34706c417643fe77`

Every regional decision, proposal trace, selected affiliation statistic and full
scientific report matched under the strict provenance comparison. GeoNames
selections share 11 source archives, reducing 191 complete archive scans to 11;
122 named-identity requests share one source and now use one isolated interpreter
and one source parse. Reviewed extraction/checking code remains unchanged.
