# Southeastern Europe interior batch 5 evidence packet

Review-only work for GitHub issue #420. This packet does not approve a regional branch, a complete region, geographic imports, or a production release.

## Files

- [`findings.md`](findings.md): evidence synthesis, classifications, uncertainties, and engineering/source-restoration handoffs.
- [`scope.json`](scope.json): exact 207-member workload and all ten province scopes.
- [`crosswalk.json`](crosswalk.json): one row for every scoped member, including source identity, Atlas parent/source metadata, component counts, exact geometry hashes, individual classification, and Croatian official-name crosswalk.
- [`reproduce_crosswalk.py`](reproduce_crosswalk.py): offline reproduction from retained scoped evidence and exact source payloads. It verifies every retained source-manifest hash, exact ID coverage, and the Croatian ministry XLS/CSV hashes and 556-row roster before rebuilding the crosswalk.
- [`extract_dgu_scoped.py`](extract_dgu_scoped.py): restores the 127 Croatian official name/role findings from the original large DGU archive. Requires the archive at its documented path and fails unless its SHA-256 matches.
- [`source/`](source/): pinned geoBoundaries source snapshots, original issue/scope snapshots, official metadata/feed, the attributed Croatian name/role extracts, and retrieval-access outcomes.
- [`source-manifest.json`](source-manifest.json): retrieval URLs/dates, byte sizes and SHA-256 hashes for retained evidence and the oversized DGU source/member.

The source feed advertised an archive size of 219,327,549 bytes. The retrieved archive was 208,774,354 bytes and is not committed because it exceeds the repository’s evidence-file guidance. Its GML member was 600,770,112 bytes. The full archive SHA-256 is retained in the source manifest and DGU extract. The scoped name/code/level/county/date extract preserves the relevant official identity evidence, with the DGU attribution and change statement required by its Open Licence. It contains no geometry.

From this directory, run `python3 reproduce_crosswalk.py`. It rewrites `crosswalk.json`; the expected result has 207 unique rows, 206 boundary `insufficient-evidence`, one correction-needed Magdenovac label, and 126 of 127 Croatian identity/role matches supported. To independently rebuild the DGU extract, restore the exact archive from the ATOM URL recorded in the feed and run `python3 extract_dgu_scoped.py`; the script rejects any archive whose SHA differs from the retained pin.
