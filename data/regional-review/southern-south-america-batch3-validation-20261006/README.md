# Southern South America batch 3 provenance and cross-field validation — issue #1122

Evidence vintage: current `main` at `0799920a604df931acaf4e32c3234da16d665ab5` and GitHub REST pointer lookups on 2026-10-06. The packet is additive under the exact #1122 owned path. It preserves every original #444/#940 file and does not change geography.

## What this verifies

The issue’s pinned ten-file contract matches the exact immutable main blobs. The exact 230 subjects resolve through the pinned world-index to 53 Argentina ADM2 departments and 177 Chile ADM3 communes. Every comparison and assessment row is checked against the actual baseline feature ID, name, parent ID, source ID, source role, reference year, administrative level, parent level, geometry type, validity and component count. Parent names and child counts are also checked against the pinned hierarchy and the frozen scope. The packet recomputes the old match, unmatched-ID, type-change, IoU-threshold, disposition and parent-summary bindings from the retained rows; these are internal consistency checks only.

The audit found two baseline component counts absent from the preserved comparison rows: `gb:ARG:ADM2:61730980B63808307170695` and `gb:ARG:ADM2:61730980B85851407891039`. The pinned baseline feature has one component for each. The new 230-row baseline binding output records those recomputed values and marks the two omissions; the original #940 packet is untouched. Other recorded baseline fields match the pinned feature rows.

The old checker’s false-parent acceptance was reproduced without modifying its files: an in-memory candidate changes `gb:ARG:ADM2:61730980B10000603471831` from `framework:province:rio-negro:1609a338a963` to `country-SPI`, recomputes the comparison file byte count/SHA-256 in the retained source inventory, and intercepts those reads. The old checker still passes its 230-subject and disposition checks. The new cross-field validator rejects the altered parent. Nine additional negative controls test wrong source ID/level, geometry type, assessment source role, LFS source vintage, duplicate/foreign IDs, inconsistent summary and a new missing component field. Candidate fixture byte lengths and SHA-256 values are recorded in `adversarial-controls.json`.

## Corrected source provenance

The preserved source inventory asserted these geoBoundaries raw-object hashes at commit `9469f09592ced973a3448cf66b6100b741b64c0d`:

| Exact upstream object | Prior asserted SHA-256 | Commit’s LFS pointer SHA-256 | Declared bytes |
|---|---|---|---:|
| `releaseData/gbOpen/ARG/ADM2/geoBoundaries-ARG-ADM2.geojson` | `cedee8710e49d9017327fc1d4b2dc536e95a82317dc94c3bac8d9404af6bf771` | `f35dae5a257302dea5bd1549ae135baf82e7ee7491918854c3db9bbdec890177` | 69,702,323 |
| `releaseData/gbOpen/CHL/ADM3/geoBoundaries-CHL-ADM3.geojson` | `f6852723bc6d44d4813086fe9df750e7228e1925a72284e3d2b65ed44e2aa99a` | `f3833ce1965394ae705e3793b50bdd007775b43da604251871deffed04f3bffd` | 171,783,952 |

Authenticated GitHub REST Contents responses at that exact commit returned pointer blobs whose Git SHA-1, byte length, pointer SHA-256, LFS object OID and declared size are retained under `source/`. The two prior sizes agree, but both prior raw SHA-256 assertions are wrong. The LFS metadata JSON/text pointer identities are recorded as well. These are pointer bytes, not the raw geometry assets: no oversized object was downloaded, so its declared OID/size are authenticated but its payload bytes were not independently rehashed.

For a future separately reviewed and lawful reconstruction, use only the exact `geoBoundaries` commit and path shown above; in a clone pinned to that commit, check out the named path, fetch its LFS object, and verify the full downloaded bytes against the corrected OID and size before using them. Do not use a current/default branch object as a substitute. These assets exceed this packet’s 32 MiB evidence-file limit and are not to be restored by this task.

## Limits and neighboring scope

The prior packet records geoBoundaries as CC BY 3.0 IGO and the Atlas feature metadata carries that assertion; this packet did not hydrate the upstream metadata payload or independently revalidate those terms. IGN ANIDA comparison bytes, Subdere DPA archive and license, Law 1186 text, change log and name-variant sources were not re-retrieved. The retained measurements and location dispositions are observed old results; their IGN/Subdere matching, geometry IoUs, legal meaning and completeness were not reproduced from source bytes. The 2020 geoBoundaries identities/parents and exact issue subjects were checked against pinned Atlas data, not certified against current statutory boundaries.

Issue #1122 covers only 53 of 54 Argentina South members and 177 of 252 Chile Central members. The Argentina country-SPI member remains in #928; the other 75 Chile Central members remain in #445. This packet does not settle territorial meaning, neighboring granularity, cross-border treatment, region envelopes, regional approval or history-import readiness. Two original component-count omissions and the incorrect legacy raw hashes remain documented follow-ups; no boundary or core geography edits are proposed here.

## Reproduction

From the repository root, use Python 3.12 with Shapely 2.1.2 and run:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 data/regional-review/southern-south-america-batch3-validation-20261006/validate_batch3.py
node scripts/evidence-quality.mjs data/regional-review/southern-south-america-batch3-validation-20261006/evidence-quality.json .
```

The validator reads the immutable baseline through the shared evidence helper, plus retained issue/API-pointer snapshots. It writes generated JSON results and separate positive-control, negative-control and reproducibility receipts only inside this owned directory. Run it twice and compare the whole-file SHA-256 values recorded in `reproducibility.json`. The evidence audit is expected to be `limited`; neither check establishes the underlying current-source geometry or legal geography.
