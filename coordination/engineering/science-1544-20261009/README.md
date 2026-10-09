# Complete-world scientific validation cost

Refs #1544. This is an engineering optimization, not a geographic correction or approval.

The baseline scope binds the complete retained inputs, validator/imported project
helpers and mandatory test wrappers at the recorded main commit. Original source,
geometry, uncertainty, successful exports and the failed trial are unchanged.
Installed scientific dependency versions are recorded separately.

The baseline profiles identified repeated JSON serialization/parsing, custody
decoding and reconstruction/accounting as substantial costs. Cumulative profile
times overlap; they must not be added together. The exported function profile is
attribution evidence, not a claim about unprofiled or hosted runtime.

The implementation reuses only descriptors of physical bytes captured in the
current custody invocation, distinguishing plain and compressed logical aliases.
Every original alias, generation, descriptor and executed-code binding is still
checked. A subsequent invocation recaptures current bytes. The scientific report
read is separately authenticated before parsing.

Invalid accounting now rejects before reconstruction. Every successful run still
performs the complete connected-component, exact structural geometry and contact
checks. Fully checked parsed accounting objects are retired before reconstruction;
original data is neither mutated nor discarded. The adverse harness's existing
input-keyed reconstruction cache is unchanged; the separate positive proof remains
uncached.

`recorded-comparison-entry.py` preserves the exact measurement driver used at its
recorded staged execution state; it is historical evidence, not a relocated
production entry point. The original before/after stdout and stderr are retained
separately. Its `.cache` scope binding and consumed staged code are described by
`baseline-scope.json` and `staged-code-scope.json`; executing it with different
current code would be a new measurement, not reproduction of the old timing.

`local-measurements.json` contains the observed unprofiled comparison, staged-code
limits, latest real-wrapper proof and focused results. It distinguishes fresh
process/fixture state from warm filesystem state. One local pair does not prove a
universal speedup. The positive comparison alone does not establish a speedup;
sampled RSS differs by phase and does not establish a memory improvement.

`final-mandatory.tap` records the real positive and original complete-world adverse
entry points with their existing deadlines and output caps. `focused-validation.log`
records custody freshness/decoding-mode, exact structure, original fixture/cache
and actual consumed-report drift probes. Independent additional fixtures, final
exact-head review, hosted PR/queue results, actual main and issue reconciliation
remain required. CI selection and package policy are unchanged; source-only
geography/history retain their focused paths.

## Reproduce

Use Node 24 and the pinned scientific Python environment. Allocate a managed sparse
slot with the four original packet directories named by `baseline-scope.json`;
include this evidence directory too. The Git store must contain the original
execution/input commits; the existing integration runner restores those pins.
Run the storage check before reproduction. Use a credential-free environment.

Run the actual wrappers, serially when comparing local costs:

```sh
node scripts/local-workspace.mjs check
node --test --test-concurrency=1 test/physical-component-evidence-controls.test.mjs test/physical-component-evidence.test.mjs
node --test test/physical-component-custody.test.mjs test/physical-component-structure.test.mjs test/physical-component-fixture.test.mjs test/physical-component-report-binding.test.mjs
```

For a profile, use a fresh owned directory under `.cache` and a Python shim selected
by the existing wrappers' `PYTHON` variable. This retains their original timeout,
output checks and required experiment count. The shim invokes the real Python
with a profiling script containing the following logic; supply the wrapper's
original arguments and record the real Python/runtime and actual code scope:

```python
import cProfile, marshal, os, pathlib, runpy, sys

args = sys.argv[1:]
if args[:1] == ['-B']:
    args = args[1:]
allowed = {
    'scripts/validate-physical-component-evidence.py',
    'test/physical-component-evidence-controls.py',
}
if len(args) != 1 or args[0] not in allowed:
    raise ValueError('Only the original scientific entry points are admitted')
folder = pathlib.Path(os.environ['SCIENCE_PROFILE_DIR'])
# The caller allocates this fresh directory inside its managed slot first.
if not folder.is_dir() or any(p.is_symlink() for p in [folder, *folder.parents]):
    raise ValueError('An ordinary fresh owned profile directory is required')
out = folder / (pathlib.Path(args[0]).stem + '.pstats')
if os.path.lexists(out):
    raise ValueError('Preserve existing profile evidence')
sys.argv = args
sys.path.insert(0, str(pathlib.Path(args[0]).resolve().parent))
profile = cProfile.Profile()
try:
    # runpy supplies the actual __main__ module that unittest discovery needs.
    profile.runcall(runpy.run_path, args[0], run_name='__main__')
finally:
    profile.create_stats()
    raw = marshal.dumps(profile.stats)
    if len(raw) > 32 * 1024 * 1024:
        raise ValueError('Profile exceeds unchanged ordinary file limit')
    with out.open('xb') as stream:
        stream.write(raw)
```

Do not overwrite an earlier profile or treat a failed/discovery-only execution as
successful proof. Retain failed attempts with their failure status. Profiling adds
overhead; use the uninstrumented wrappers for runtime comparisons. Before/after
comparisons must bind actual consumed code and complete input bytes, preserve all
original assertions, and report hosted setup/cache/runtime differences honestly.
