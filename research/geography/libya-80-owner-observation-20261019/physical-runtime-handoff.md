# LBY80 physical runtime handoff

This records the local isolated Python environment that passed the existing physical producer. It is a local pre-provisioned venv, not a repository dependency; no installation or runtime workaround is part of this handoff.

## Pinned requirements

The repository `requirements.txt` pins:

- `numpy==2.3.5`
- `shapely==2.1.2`
- `pyproj==3.7.2`
- `rasterio==1.4.3`

The retained venv also reports `affine==3.0.1`, `attrs==26.1.0`, `certifi==2026.10.18`, `click==8.5.0`, `click-plugins==1.1.1.2`, `cligj==0.7.2`, `pip==25.0.1`, and `pyparsing==3.3.3` from `pip freeze --all`.

## Isolated import verification

Interpreter:

`/Users/chengshuli/Documents/Codex/2026-10-18/task-3/.selected-audit-103b230/libya-handoff-20261019/runtime/lby80-physical-venv/bin/python`

The following command succeeded with Python `3.12.14`, NumPy `2.3.5`, Shapely `2.1.2`, GEOS `3.13.1`, PyProj `3.7.2`, and Rasterio `1.4.3`:

```sh
/path/to/lby80-physical-venv/bin/python -I -B -c 'import sys,numpy,shapely,pyproj,rasterio; print(sys.executable); print(sys.version); print("numpy",numpy.__version__); print("shapely",shapely.__version__,"GEOS",shapely.geos_version_string); print("pyproj",pyproj.__version__); print("rasterio",rasterio.__version__)'
```

The earlier base-runtime attempt failed because Shapely existed only in the user site-packages, which `-I` excludes. The isolated venv above supplies the exact pinned libraries without changing the producer flags or copying packages.

## Successful producer context

Physical phase command used by the retained run:

```sh
/Users/chengshuli/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node scripts/prepare-delivery-handoff.mjs physical research/geography/libya-80-owner-observation-20261019/physical-config-003.json .cache/delivery-handoff/lby80-physical-20261019
```

The exact input/runtime inventory is in `physical-config-003.json`; the committed execution receipt binds the phase config, producer SHA256 `abc801b9a35d20c9f0dfe3bbc9bb2cb7dc107f1758414970d9cde11380574a18`, and output `whole-target-support.json` SHA256 `4a1837f7977c58456a54713118247ce44014d76f26202fcd575a4844b0138811` (629,965 bytes). The local venv is evidenced by those pins and is not itself committed.

This phase records whole-original source-relative geometry diagnostics. It does not establish cell-level physical qualification, native ownership, source applicability, or accepted repair credit. Outside-Level1 context remains retained, and Benghazi's `extra_reconstruction` remains an open issue.
