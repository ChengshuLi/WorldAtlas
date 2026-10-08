# Temotu and Santa Cruz Islands parent-scope evidence

This packet evaluates only `gb:SLB:ADM1:17018030B19935783635883` and its present relationship to `framework:area:santa-cruz-is:a2bb7bce4e86`. It does not approve the southwestern Pacific region, certify the Temotu boundary, or change any location, source, ID, release, or parent.

## Reproduce

Use the repository Python 3.12 environment and Node 24. From the repository root:

```sh
PYTHON=/Users/chengshuli/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3
NODE=/Users/chengshuli/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node
$PYTHON data/regional-review/temotu-santa-cruz-parent-scope-20261005/reproduce.py --write --vintage source-review-20261008
$PYTHON data/regional-review/temotu-santa-cruz-parent-scope-20261005/reproduce.py --check --vintage source-review-20261008
$NODE scripts/evidence-quality.mjs data/regional-review/temotu-santa-cruz-parent-scope-20261005/evidence-quality.json
```

Use Python 3.12.14 and Node 24.19.0. The first command writes one fresh, bounded result with the shared immutable-evidence helper. The second recomputes the actual baseline reads and controls and compares canonical output bytes. A repeated `--write` must use a new vintage; it never overwrites an existing result. The script does not execute network operations or alter shared geography.

## Finding

The administrative province is Temotu. The Ministry profile says it was formerly called Santa Cruz Islands Province, describes it as two scattered island chains, and identifies Santa Cruz/Nendo as its largest island. The Provincial Government Act describes Temotu as islands within a broad scheduled boundary. These sources establish administrative context, not that the province is coextensive with the Atlas area.

The name “Santa Cruz Islands” has materially different sourced scopes. Solomon Islands subsidiary legislation names the Santa Cruz Islands archipelago and Duff Islands archipelago separately. The ICOMOS Pacific cultural-landscape account groups Nendö, Utupua, Vanikoro, Reef Islands, and Duff/Taumako under “Reef Santa Cruz Islands” and treats nearby Tikopia separately in its portfolio. Neither source defines the intended perimeter or complete member list of the Atlas area.

The current Atlas ledger assigns the whole Temotu province location to Santa Cruz Islands. Its source-derived metadata records a 44.143% Santa Cruz-area overlap and a 99.7522% administrative-parent overlap; those are reference-screen outputs, not independent proof of the area convention or lawful province extent. The retained Natural Earth-derived ten-feature ADM1 reference is generalized and includes the Capital Territory (Honiara) alongside nine province-named units. It cannot resolve which geographic meaning the Atlas intended.

**Disposition: unresolved parent scope; no whole-province reparent is supported.** Keep the current row and geometry unchanged. Geography integration/Main should define the intended Santa Cruz Islands area membership, including Duff/Taumako and other Temotu groups. If that scope excludes part of Temotu, a separately scoped source-backed geographic-portion design is needed; do not infer new boundaries from province overlaps or historic naming. Engineering should act only after that scope decision.

The legal copies and government pages have no reuse terms established here and are restoration-only. Exact retrieval hashes, URLs, retrieval dates, versions, inspected passages, source scale, and limits are recorded in `source-acquisition.json` and `sources.json`. The evidence manifest pins the exact issue baselines and actual subject file. Passing reproduction and byte checks does not establish geographic truth.
