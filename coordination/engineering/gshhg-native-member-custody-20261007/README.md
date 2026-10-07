# Complete original GSHHG native-byte custody (#1376)

This owned engineering producer consumes exactly the twelve originals in
`input-index.json`: all four original ZIP pieces, source catalogue, original
member inventory/report, three distributed terms files, original parser bytes
and the unchanged existing codec. It writes three lossless contiguous native
aliases and a complete native-header/coordinate-byte hash roster. No polygons,
source coordinates, geography, providers or data permissions are changed.

Root freezes the complete six-file execution closure before invoking controls,
input-only and two complete runs with Python3.12.14 and the pinned runtime.
Commands require the actual full immutable commit; branches/short hashes fail.
The intended arguments are:

```
python -B controls.py --repo /absolute/owned/work --commit FULL40HEX --out /absolute/owned/work/.cache/1376/controls
python -B producer.py --repo /absolute/owned/work --commit FULL40HEX --out /absolute/owned/work/.cache/1376/input-only --input-only
python -B producer.py --repo /absolute/owned/work --commit FULL40HEX --out /absolute/owned/work/.cache/1376/run-one
python -B producer.py --repo /absolute/owned/work --commit FULL40HEX --out /absolute/owned/work/.cache/1376/run-two
```

These are future recipes, not executed results. No source getter can read an
undeclared commit/path/mode/OID/body. All twelve originals pass whole-byte
preflight before extraction/output creation. ZIP reconstruction rereads the
four same admitted originals; reports distinguish both actual read passes.

All eighteen actual ZIP directory descriptors are compared with the original
inventory. ONLY `gshhs_f.b` is decompressed and its whole body freshly hashed.
The other seventeen body hashes remain explicitly inherited upstream claims.
No testzip/read-all call quietly decompresses additional members.

`reader.consume_native(index, get_encoded, consumer, scratch_parent)` is the
real downstream API. It accepts no prior passed receipt: it authenticates all
three gzip bodies, offsets, original native bytes and all188,612 native records
into a temporary virtual image, rechecks the whole image/index/code, then and
only then calls the consumer. Source geometry operations cannot see partial
validation yields. No ZIP fallback is present in this reader. Both complete
producer calls exercise this interface and retain `downstream-reader.json`.
The logical95,809,336-byte reconstruction is not an oversized ordinary evidence
descriptor: its three actual inputs each obey32MiB encoded AND decoded limits.

Native record metadata preserves raw header integers, coordinate hashes, byte
positions, flag roles and original int32 bounds. It does not certify geometry
validity, current water/land, political affiliation or a repair. Source2017
release includes heterogeneous older WVS/WDBII observations and uncertain
registration/precision. Preserve actual LICENSE/README wording conflict and
other inherited original limits. The other AntarcticL5/L6 alternatives remain
in native custody, without being relabeled ordinaryL1 land.

Old #1353 runs read an unadmitted118,617,033-byte ZIP dependency. Their original
code/results remain archived unadmitted observations; this genuinely separate
phase does not retroactively admit them. Fresh later #1353 runs must use these
actually merged/admitted native aliases at a new immutable source-provider
vintage, preserving all46/28+18/209 and all45 original numerical products.

Root owns final data generation, actual complete two-run verification,
manifest/ordinary admission, exact-head independent review, normal queue,
actual merged readback and lifecycle. This directory contains no proof of
those future outcomes until actual execution receipts and products exist.
