# Safe replay for North Macedonia issue #1237

Run the retained 84-subject source-to-source comparison without using mutable imported project helpers or publishing outside this issue's owned prefix:

```sh
python3 data/regional-review/northern-macedonia-method-995-guard-erratum/guarded_reproduce.py \
  data/regional-review/northern-macedonia-method-995-guard-erratum/v1/replay.json
```

The tested environment was Python 3.12.14, Shapely 2.1.2 and pyproj 3.7.2. The runner authenticates all 30 whole-file inputs at the immutable baseline, the old report runner and its pin, and every actual project Python module at the import boundary. The code capsule compiles only authenticated source bytes. It also checks materialized helper bytes before work, resolves output components relative to directory handles with no-follow checks, and creates results exclusively. The exact previous report SHA-256 is `d3d23c61368d3db4fb5acf049cfaff9f3533a1da7c37c5b96d02070d50b3fef3`.

Run all positive and negative controls with:

```sh
python3 data/regional-review/northern-macedonia-method-995-guard-erratum/controls.py
```

This reproduces two distinct outputs and checks traversal, absolute output, symlink-parent escape, existing-output preservation, full helper/reproducer drift at actual loader boundaries, descriptor/input drift, and old/current runner pin failures. `controls/negative-control.json` records rejected paths, outside-prefix sentinels and full synthetic helper fixtures. No network access is used by the runners.

This safeguards reproduction only. Its 84 matched records and eight parent contexts are not a complete regional audit. The exact source vintage, legal effective boundaries, current AKN geometry, parent semantics and upstream source reuse remain unresolved as described in `SOURCES.md`; nothing here changes geography, imports data, or authorizes regional approval.
