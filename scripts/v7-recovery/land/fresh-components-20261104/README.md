# In-process physical components

`build_components.py` validates the pinned physical mask, calls `components.py`
in the current Python interpreter, verifies complete physical/component coverage,
and publishes research-only output. No compiler, executable helper, custom native
binding or dense whole-grid mask is used.

The algorithm builds one union/find node per physical land run. Adjacent-row
interval overlaps and longitude seams are joined in the same order, with the
same union-by-size and equal-size tie rule, as the original builder. Diagonal
cells and the north/south edges are not joined. Generation-local root IDs,
row offsets and all output triples therefore remain byte-identical.

The new `single-generation-component-manifest-v2` identifies the Python source
artifact and Python runtime explicitly. Legacy manifests remain readable for
old evidence; new builds do not claim a compiler or binary identity.

## Complete global replay

`evidence/python-components-global.json` records all input, expected-output,
actual-output and algorithm-source SHA-256 values. The reproducible checker is:

```
python benchmark_components.py \
  --width 131072 --height 54614 \
  --physical-rows PHYSICAL_ROWS --physical-runs PHYSICAL_RUNS \
  --expected-rows COMPONENT_ROWS --expected-runs COMPONENT_RUNS \
  --output NEW_OUTPUT_DIRECTORY
```

The complete replay took 20.821 seconds on CPython 3.12.14 and reproduced
13,315,490 runs, 457,893 components and 1,984,469,039 land cells. Both complete
output SHA-256 values match the pinned original. The replay blocks subprocess
launches and custom `ctypes.CDLL` bindings. This is an output-parity measurement,
not a claim that Python is faster than the original component stage.

## Atomic local output publication

The shared `stage2-geodesic-20261104/atomic_move.py` uses only Python filesystem
APIs. POSIX `os.rename` can overwrite an empty directory, so it is not a safe
replacement for native no-replace rename.

Publication instead copies the complete sealed tree into a private durable
sibling payload and atomically creates an exclusive destination symlink. Any
existing destination, including an empty directory or dangling symlink, wins.
Before that commit, the source is intact and no public output exists. After it,
readers see a complete independent tree and source cleanup cannot damage it.
A post-commit durability or cleanup failure is reported as uncertain, never
silently retried or rolled back.

The hidden payload and its receipt are part of the output and must be retained.
Interrupted/unpublished payloads remain available for inspection. The protocol
uses extra temporary disk space for the independent copy. It never uses a
check-then-rename fallback. Checkpoint inventories accept only this exact
sibling-payload protocol, seal its receipt and every file, and still reject
arbitrary or escaping symlinks. Public output names remain stable across resume.

`evidence/python-components-global-driver.json` additionally records complete
source-pin validation, component generation, full physical coverage validation,
truthful Python manifest creation and durable atomic publication, with identical
global output bytes and no process/custom-binding calls. Add `--physical-report
PHYSICAL_REPORT` to the checker command to reproduce that path. Its 37.174-second
elapsed time overlaps another worker's physical trial and must not be used as
an isolated performance comparison. Conservative overlap bounds are
2026-11-08 06:10:40.210664224 UTC through 06:11:17.744322700 UTC.
That report retains its exact original support-source hashes. The subsequent
publication-reader change only canonicalizes parent aliases; the writer and
component algorithm are unchanged, and the alias behavior has a separate test.
