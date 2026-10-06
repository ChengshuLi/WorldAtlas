# Bulgaria EKATTE member vintage erratum (#1191)

## Finding

The retained EKATTE ZIP is one 2026-10-05 export containing separate table members with different data-reference dates. The municipality member `ek_obst.json` has 265 data records and final metadata `Данните са актуални към: 12/12/2023`; the district member `ek_obl.json` has 28 data records and `05/10/2015`. Parsed explicitly as day/month/year, these mean **2023-12-12** and **2015-10-05**. Their final metadata export timestamps are **2026-10-05 03:00** and **2026-10-05 03:28**, respectively. The archive specifies no timezone. A common ZIP/export date does not make the two reference vintages contemporaneous.

The old packet manifest and README associate the combined municipality/district crosswalk with one 2023 reference date. The crosswalk’s municipality values come from the 2023-12-12 member while district names/codes come from the 2015-10-05 member. The row/name/code crosswalk still reproduces as before, but its parent-name comparison is historical register correspondence, not proof of current district membership.

## Geography meaning and neighboring granularity

NSI describes EKATTE as the Unified Classifier of Administrative-Territorial and Territorial Units. The retained ZIP has distinct municipality and district tables. NSI’s 2025 administrative-territorial publication reports 265 municipalities and 28 administrative districts at 2025-12-31; it distinguishes NUTS1/NUTS2 statistical regions from administrative units and says NUTS3 corresponds to the 28 districts. The same publication lists mayoralties and settlements as finer levels. These counts establish institutional context and tier distinctions, not the geometry or legal parent assignment of the 213 scoped Atlas IDs.

The 213 scoped rows are the exact earlier #417 subject roster and retain their original stable IDs. The 2019 GeoBoundaries layer has 265 features but only 264 unique municipality-code matches in the original full-roster diagnostic; it reports two Zlatitsa candidates and no source candidate for Sarnitsa. Those cases remain owned separately by #1030. The exact historical name/code crosswalk for the 213 subjects was independently reproduced twice with the original output hashes. It does not verify Atlas-parent-ID to EKATTE-district-code linkage, present-day district boundaries, or that all 213 source polygons are correct/current.

## Reproduction and controls

`reproduce_vintages.py` verifies the exact issue pins against their declared Git commits, the complete 213-ID roster, the retained ZIP hash, every one of its 12 decoded member hashes/lengths (4,712,618 decoded bytes total), and the complete two consumed table members. It parses the two members independently; a synthetic district member with date `01/02/2011` remains `2011-02-01`, and a missing member date remains unknown rather than inheriting the municipality date.

It also executes the unchanged original #417 `reproduce.py` twice in memory with only the three product destinations redirected to ignored scratch inside this owned packet. The original destination strings remain in the generated summary so the historical products match exactly. Only lengths and SHA-256 digests are saved; row-level joined CSVs/JSON are deleted after each run and are not part of this change. Both runs reproduce the retained hashes: scoped CSV 94,358 bytes (`8e16f596cc7805d8841a77d40ef202efe7c34f60acbaa5d6c66d19cd0a61a6c9`), full-source CSV 61,666 bytes (`9bf598322c17f5cbf0be86e859bb126533e6e8685f0748df047c391ed459eb94`), and summary 2,539 bytes (`a915b4478bcd822bae51576c16c0a65f5a136157c6a1ad6d1a5369b21e34a928`). The three original output files and all original evidence remain unchanged.

Run from the repository root:

```sh
python3 data/regional-review/bgr-register-vintage-417-erratum/reproduce_vintages.py --output-dir evidence
```

The chosen directory must not already exist. This script checks the source bytes and creates only aggregate metadata/hash records. Its local reproduction outputs are temporary and ignored. Evidence is tied to immutable source pins, not to a live NSI download.

## Limits and unresolved work

The source record uses EKATTE names/codes and does not contain current municipal boundary polygons. This erratum does not validate geometry, update the 2015 district table, identify an authoritative district-to-Atlas-parent mapping, or adjudicate municipal identity. The 2019 polygon layer versus later register information remains a mixed-vintage crosswalk; per-unit legal/geometry verification is outside this issue. NSI’s posted license page states attribution conditions and excludes derivative or composite works; this packet retains only the original archive in the prior packet and reports compact member metadata, hashes and provenance. It does not redistribute row-level joins or claim legal clearance for any broader reuse. Verify exact database rights and source attribution before any later redistribution or production use.

The earlier #1031 audit remains incomplete for current authoritative municipal and district boundaries, rights of underlying geometry, the two Zlatitsa candidates, missing Sarnitsa source candidate and Atlas parent-code linkage. This packet corrects only the interpretation of reference/export dates. It certifies neither the full Southeastern Europe region nor the 213 polygons.
