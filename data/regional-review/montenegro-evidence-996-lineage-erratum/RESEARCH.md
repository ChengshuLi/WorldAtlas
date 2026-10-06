# Montenegro #1179 lineage erratum

Retrieved and reproduced 2026-10-06 (UTC). This is a metadata-only correction to the lineage selector in the retained #1179 evidence packet. It does not change, rerun, or endorse any geography result, source geometry, parent boundary, or earlier audit outcome. The exact issue contract and subject roster are preserved in `issue-scope-snapshot.json`.

## Question and finding

At the immutable merge `b4e110df5a0a0953e91bf9abc89dccdb0b05e6e1`, the retained #996 evidence manifest selects both `anchored-v10/run-1` and `anchored-v10/run-2` as active. Those same two paths also appear in `reproduction.superseded_runs`, each with the reason that its research note predates final review. Its `superseded_control.path` selects `reproducibility-control-anchored-v10.json`, but the reason says the v9 research note is superseded; the required reproducibility validation row also selects that v10 control. A reader therefore cannot consistently tell which version is authoritative or superseded.

The pinned runner's `finalize()` at the same merge makes the source of the inconsistent labels visible: it explicitly creates the v10 run pair and v10 control, then writes the two v10 paths into the superseded list and labels the v10 control as superseded with a v9 explanation. The v9 run pair/control remains retained. The v9 and v10 controls identify distinct finalizer code commits/hashes, while both retained pairs report comparison SHA-256 `8b5acd06c9d269979287277d498e6e9405543d46a681149a327062abe63f782b`. This establishes a lineage contradiction, not a wrong metric or failed input guard.

The correction in `lineage-correction.json` selects only the anchored-v10 pair and control as authoritative, removes exactly those two paths from the superseded set while preserving the other 18 superseded rows, and identifies the v9 control and v9 pair as historical/superseded. The former contradictory strings are retained verbatim under `historical_contradiction`; the old packet remains immutable. `reproduce.py` verifies all 20 issue-pinned inputs at their declared commit and at the single common baseline, accounts for all 23 issue IDs, checks the recorded parent context without treating it as legal parentage, and runs positive plus two rejection controls. Two output directories are exclusive and their result bytes must match.

## Territorial meaning and source context

The 23 issue subjects are retained Atlas records with `gb:MNE:ADM1` source metadata. Their retained feature attributes call the source role “Municipality,” identify 2017 reference metadata and record ODbL 1.0; the prior #1179 research describes the compared source as OSM/Wambacher-derived. This identifies the lineage of the comparison features. It does not prove an official municipal boundary, legal role, effective date, or current municipality completeness. The source catalog hash ambiguity and the exact capture/effective date remain unresolved.

The pinned records point to 23 distinct Atlas `province`-level framework identities, each carrying `child_count: 1`, `framework_status: retained-reference`, and an open boundary review. These are read-only Atlas parent references with names duplicating their scoped municipality subjects; they do not establish legal parentage or a meaningful approved hierarchy tier. No hierarchy or feature is changed.

The inherited #1179 source review reports a 2017 publication of municipal areas as of December 2015, a 2021 publication with a 24-unit post-Tuzi roster, and a 2025 current local-government roster with 25 entries. The source review reports an unexplained 157 km² excess in the 23-unit 2015 area sum, and says Tuzi's reported 2021 area was temporary/approximate pending demarcation. These dated counts and aggregate areas are not boundary measurements or proof that the 23-source roster is complete today. The reported 2026 Tuzi/Podgorica arbitration referral has no verified outcome in the retained record.

Primary-source restoration findings are inherited from the pinned prior research, not newly retrieved for this issue. The prior source inventory records no retained official 2017/current municipality vectors, complete island/coast/water conventions, settlement-parent hierarchy, comparable historical official snapshot, or established reuse terms. It directs restoration through the Montenegro Water Information System and Cadastre/Spatial Units Register, and documents Monstat PDF restoration URLs and SHA-256 values. Neighboring municipal/settlement granularity, Tuzi/Podgorica and Podgorica/Zeta delimitation, national completeness, and legal boundary equivalence remain unresolved. The 23 records are the exact erratum scope only, not a certified national or current roster.

The prior inventory describes geoBoundaries MNE ADM1 as ODbL 1.0 and requires OpenStreetMap/Wambacher attribution and share-alike compliance; it records the retained comparison payload at `data/regional-review/followup-montenegro-422-boundaries-20261005/source/gb-MNE-ADM1-geoBoundaries-2017.geojson`, SHA-256 `9674292fbc0a50c68c6584a2ae23fae768e76cc796bdb7e3e009c0197aec6ae3`, 610,015 bytes, retrieved 2026-10-05. That source payload is not part of #1207's declared pin set and was not independently rehashed here. The inherited 2025 open-data roster is labeled CC BY (version unspecified) with attribution; its recorded payload SHA-256 is `cd4e94fd3236fc9b3f7bea043fd8dcda6bcbd72d9b3157f3ff1b417650e8a64a`, 4,375 bytes. Monstat publications and official WIS/cadastre/process pages have unknown reuse terms in the prior inventory and remain restoration-only. This erratum copies no third-party geometry or PDF.

## Exact inputs and reproducibility

The accepted issue contract declares 20 exact whole-file pins across `b4e110df5a0a0953e91bf9abc89dccdb0b05e6e1` and `b6cfaada43a1e0472cd833d16733d1fd6065eaec`. All 20 hashes were checked against their named commit and found byte-identical at common evidence baseline `b4e110df5a0a0953e91bf9abc89dccdb0b05e6e1`, allowing the v1 evidence manifest to name one truthful baseline. The complete raw pinned input total, as computed by `reproduce.py`, is retained in `lineage-control.json`. No external downloads or source restoration are part of the run.

Commands from the repository root:

```sh
python3 data/regional-review/montenegro-evidence-996-lineage-erratum/reproduce.py run --output-dir data/regional-review/montenegro-evidence-996-lineage-erratum/runs/2026-10-06/run-1
python3 data/regional-review/montenegro-evidence-996-lineage-erratum/reproduce.py run --output-dir data/regional-review/montenegro-evidence-996-lineage-erratum/runs/2026-10-06/run-2
python3 data/regional-review/montenegro-evidence-996-lineage-erratum/reproduce.py finalize
node scripts/evidence-quality.mjs data/regional-review/montenegro-evidence-996-lineage-erratum/evidence-quality.json
```

The source-level audit confirms only the lineage contradiction. The original #1013 audit remains Incomplete; this packet does not close its primary-source, territorial-boundary, parentage, license, completeness, neighboring-granularity, or publisher findings. It authorizes no geography approval, import, deployment, or production edit.
