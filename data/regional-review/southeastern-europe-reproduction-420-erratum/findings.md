# #420 Crosswalk Reproduction Erratum

**Work item:** #1161, claimed by GEO 0 on 2026-10-06.

**Reviewed input baseline:** #1004 merge `96f2a6d201236ba62f471535db240b123de60c09`.

**Research status:** bounded reproduction and integrity controls complete; no geography approval, boundary correction, or source-authority finding.

## Reproduction result

This packet preserves the original #420 packet and adds a separate runner. Before each run, the runner rereads all 61 issue-pinned whole-file inputs directly from the immutable #1004 commit, confirms byte counts and SHA-256 values, checks the exact 207 issue subjects and their occurrence counts in the complete source layers and Atlas parts, and stages copies in a fresh private directory. It relocates the original `crosswalk.json` outside the legacy runner's fixed output path, executes the legacy reproduction script byte-for-byte, and writes the result with exclusive creation under a unique run directory.

Two independent staged executions (`run-author-b` and `run-author-c`) produced 536,887-byte outputs, both SHA-256 `5c231dddec6314f50dbf18df3a55f5bd2fe0d74b7ddd51189650d2914fe749ec`, byte-identical to the original retained crosswalk. The original historical result and all 61 source/baseline inputs remain unchanged. Each receipt records the exact script/input hashes, UTC execution times, source retrieval date carried forward from the inherited packet, and the uncompressed release hash.

The whole-file inventory is 236,953,157 bytes. The separately decompressed pinned release is 536,565 bytes; with the 2,097,152-byte output reserve, total admitted phase bytes are 239,586,874, below the 268,435,456-byte (256 MiB) phase ceiling. Every individual pinned input and the decompressed release are below 32 MiB. The retained original crosswalk SHA-256 is unchanged.

## Integrity controls

`verify-negative-controls.py` records nine passed rejection controls in `negative-controls.json`: altered Atlas geometry, altered source metadata, altered source geometry bytes, altered legacy code, a wrong baseline, duplicate Atlas subject identity, duplicate source subject identity, a duplicated native source feature ID, and attempting to reuse an existing output directory. Existing output bytes were compared before and after that refusal and remained unchanged.

These controls exercise the guards used by the runner. The reproduction only establishes that the declared historical procedure can be repeated from its pinned inputs without overwriting retained evidence. It does not establish that those inputs are authoritative, complete, legally reusable, territorially correct, or correctly assigned in the Atlas.

## Scope and structural results

- The issue's exact native-ID roster contains 80 `gb:GRC:ADM3:*` subjects and 127 `gb:HRV:ADM2:*` subjects. The runner checks each occurs once in its corresponding retained GeoBoundaries layer and once in the complete 34-part Atlas input set. The source layers contain 326 GRC ADM3 and 560 HRV ADM2 features, matching their own pinned metadata counts.
- The ten original province workloads remain 127 Croatia and 80 Greece locations in the inherited issue scope. The runner checks the existing native IDs, parent IDs, full child counts, two area contexts, and hierarchy rows against pinned files. Those are preservation/reproduction checks only; they do not establish administrative equivalence or validate boundaries.
- The Atlas world index also contains two non-`part-*.json` additions. The 34 geometry part files named by the issue pin table are the exact subset consumed by the historical crosswalk script; both additions remain outside that script's declared 61-file input inventory.
- No core geography, source packet, release pin, issue roster, ID, result or prior evidence was edited. The only files added or amended for this work are inside this issue's declared owned directory.

## Source vintage, licensing and completeness limits

The inherited #420 source manifest records retrieval on 2026-10-05 and retains the complete geoBoundaries GRC 2010 ADM3 and HRV 2021 ADM2 layers and metadata, plus Croatian DGU/Ministry extracts and the Hellenic catalog response. The source metadata identifies GRC as municipality-level, with 326 units, a CC0 field, and a separate CC BY 3.0 attribution detail; HRV is described as 2021 municipalities and towns, with 560 units and CC BY-SA 2.0. These declarations conflict or have limited lineage detail; this reproduction makes no license determination.

The Greek catalog identifies the Kallikratis dataset as a corrected 2010 release and declares CC-BY-3.0, but the advertised geometry download returned HTTP 404 on 2026-10-05. The cited Ministry PDF and regional roster page returned HTTP 403, and a GEODATA catalog request timed out. These are recorded endpoint outcomes, not evidence that an official source does not exist. No official same-vintage Greek geometry was independently inspected here.

The original DGU archive and full GML were not retained because of their size. The inherited packet retains the scoped extract, extraction/restoration instructions, advertised and observed counts, and hashes. It reports 50,192 returned GML members against a 10,000 `numberReturned` header and a 50,192 `numberMatched` count, with a next-page URL. This inconsistency remains unresolved; the extract is not an independent completeness certificate. The original Croatia Ministry XLS and its prior CSV conversion are retained with inherited retrieval/provenance information; this erratum draws no new licensing conclusion from their metadata.

The original #420 findings also identify source-vintage and neighboring-granularity concerns, including source/Atlas geometry hash differences, overlap diagnostics, source multipart geometry, Greek source count/name duplication outside the 80-member issue roster, and a Croatian spelling handoff. Hash differences and multipart topology are not boundary-error findings. The prior packet's specific follow-ups (#1002, #1003, regional integration, and the separate Oraiokastro count investigation) remain unresolved and are not closed by this reproduction.

## What remains unresolved

This work item is limited to hardening and reproducing the #420 crosswalk procedure. It does not research all 207 territorial claims or certify the completeness, role, parent relationships, boundaries, licenses, or neighboring granularity of those subjects. The evidence remains insufficient for a regional or location-level approval. Continue the explicit source-restoration and engineering/research handoffs in the original #420 findings; do not use this packet to authorize imports, publication, boundary changes, or historical approval.

## Reproduction

From the repository root on the claimed branch:

```sh
python3 data/regional-review/southeastern-europe-reproduction-420-erratum/reproduce-crosswalk.py --run-id RUN-NAME
python3 data/regional-review/southeastern-europe-reproduction-420-erratum/verify-negative-controls.py
```

Run IDs must be new `run-*` names. The runner verifies its SHA-256 against `runner-pin.json`; the negative-control receipt binds to that same runner hash. The issue scope and claim receipt are preserved in this packet to make the exact owned scope and worker identity reviewable.
