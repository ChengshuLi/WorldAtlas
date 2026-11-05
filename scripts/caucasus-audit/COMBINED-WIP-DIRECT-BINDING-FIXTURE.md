# Combined sources through the WIP direct core binding

`test_combined_wip_core_source_binding.py` extends the bounded combined
Panama/Caucasus fixture. It runs the actual Caucasus source-gate subprocess,
frozen direct-v2 seed producer, Panama OSM binder, both synthetic water
closures and strict fresh-proof crosswalk. It then passes the **generated** seed
report and request to the disabled WIP `build_stage2.verify_direct_binding`.
That function checks the outer-config and request pins, core input pins,
producer artifacts and the WIP isolated Panama source replay. The fixture
checks fresh-versus-historical seed mode, rejects a substituted archive pin
and request marker, and retains the combined fixture's gate, provenance and
proof-tampering checks. No gate flags are changed.

The two source sets are real; the snapshot and source catalog, 720×360 grid,
physical mask, components, witnesses, outer config, manifest and closures are
synthetic. This invokes individual WIP functions, **not** the outer
orchestrator or a full core run. It does not authenticate a final physical
mask, select a live Neon recipe, promote the WIP or establish geographic or
historical correctness. Historical and fresh closure pins intentionally differ;
selecting fresh-proof mode in an actual outer run still requires authenticated
direct invocation and independently reviewed gating.

To reproduce, start with an isolated copy of the `stage2-rss-runtime-20261105`
baseline as `SCRATCH/runtime`. Apply **only** these paths from the disabled
`direct-stage2-work-in-progress/work-in-progress.patch`:

```sh
cd "$SCRATCH"
git apply --include=runtime/build_stage2.py --include=runtime/contracts.py \
  --include=runtime/direct_seed.py "$REPO/scripts/v7-land/research-mixed-runtime/direct-stage2-work-in-progress/work-in-progress.patch"
cp -R "$REPO/scripts/v7-land/mainland-seed-l2" runtime/seed-producer-direct
```

The fixture requires these exact resulting SHA-256 hashes and fails if they
differ:

- `build_stage2.py`: `79d2d723ecb0fc7ee36647843cca311d4b3098b71179799fc5ba4997530055b6`
- `contracts.py`: `f703e5edcb0f67cc908aa0812e5b194b480ea2916c017464e51d1bfa0066c7f1`
- `direct_seed.py`: `79dff028d83d9fdba6170ccec80d7b9d54ac9ba13ae134683d9b35217cfd0654`

From `scripts/caucasus-audit`, use the source variables listed in
`COMBINED-PANAMA-CAUCASUS-CORE-FIXTURE.md`, with `PYTHONPATH` pointing to
`$SCRATCH/runtime`, then run:

```sh
python3 -m unittest -v test_combined_wip_core_source_binding
```

The bounded test passed 1/1 on macOS arm64, Python 3.11.18, GDAL 3.10.3 and
SciPy 1.17.1. Synthetic rows and runs SHA-256 were respectively
`fa311f33642523204236c02d8f7d23309174347304e8412d76e126643480c9dc`
and `e068228e97fa80bde0f7d937dc62e26c7ae36330604369c22459f1fea5079091`.
No production data, selected Neon data or map was changed.
