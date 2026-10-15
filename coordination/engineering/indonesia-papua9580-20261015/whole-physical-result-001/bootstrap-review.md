# Papua physical bootstrap: invocation correction confirmed

The existing virtual environment is intact. The failed first physical launch inherited `__PYVENV_LAUNCHER__=/usr/local/bin/python3` from the system Python3.7 supervisor through Node. On macOS, Python3.12's `site.venv()` uses that launcher override to locate `pyvenv.cfg`, so the child selected the base environment and could not find Shapely. This is an invocation-environment failure before physical input reading, not missing installed scientific dependencies or a scientific result.

Read-only code proof:

- Installed `.../dependencies/python/lib/python3.12/site.py:513–531`: on darwin, `__PYVENV_LAUNCHER__` replaces the executable used to choose the `pyvenv.cfg` search directories.
- Accepted `scripts/prepare-delivery-handoff.mjs:27`: `environment()` spreads `process.env`, preserving this launcher variable.
- Accepted entry:1194–1196 invokes `runtime.python.path` directly with `-I -B`. It does not replace the launch alias with its realpath.
- Accepted entry:1157–1167 resolves realpath for immutable file hashing/identity checks only.
- The configured `venv/bin/python` is a symlink chain to the bundled Python3.12 executable, with an intact adjacent `pyvenv.cfg` and installed NumPy/Shapely paths. Those source/native roles are already in the runtime inventory.

Main supplied matched concrete observations: system-Python3.7 parent → Node → exact configured venv child inherited the launcher, reported system executable/base prefix, reproduced the exec_prefix warning, and could not discover Shapely. Direct bash → Node → the same configured venv child reported the correct venv prefix and found Shapely. This review independently read the same launcher value in its own inherited metadata environment and verified the relevant installed/accepted source branches. It did not duplicate Main's executable probes.

**Supported correction:** launch the same ordinary `/usr/bin/time -l NODE ENTRY physical CONFIG DESTINATION` directly from bash without the system-Python3.7 parent. Keep the configured venv alias, accepted entry/helper bytes, runtime binding, stage/config, ordinary memory/headroom/concurrency checks and scientific guards unchanged. A bash timeout monitor, or the correctly configured venv Python supervisor which consumes the launcher consistently, can own finite supervision; no production code patch, numerical override or shared environment mutation is needed. Direct bash is the already reproduced correction.

Main's inexpensive verification should use that same corrected Node→configured-venv launch context: confirm the expected prefix/module availability or imports, and run the exact helper with `--help`. Successful imports and helper argument-parser startup establish bootstrap readiness only. No full roster rescan or scientific physical work is needed to verify this invocation correction. The actual retry must still pass the stock runtime-version/loaded-module-subset checks and fresh normal resource admission, and preserve any real result or refusal.

No fresh virtual environment or dependency installation is needed. If a later independently observed dependency gap warrants a new environment, the repository supports pinned root `requirements.txt` and immutable environments keyed by lockfile/runtime/architecture with one installation writer; never repair another worker's shared environment in place. That contingency is not triggered by this failure.

The original failed execution remains preserved in `../idn-papua9580-group-physical-preparation-001/execution-001.json` and `time-stderr-001.log`: exit1, approximately0.96s, dependency import failure at helper line598, no physical input read or scientific output. No recovery installation, runtime mutation, metadata launch, physical/source/native execution, fetch or queue action was performed by this recovery worker. No action was denied or has an uncertain outcome; actual retry remains owned by Main.
