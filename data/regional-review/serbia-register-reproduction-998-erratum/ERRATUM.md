# Guarded reproduction erratum for Serbia issue #998

Research date: 2026-10-06 (America/Los_Angeles). This is an additive reproduction-safety repair for [issue #1175](https://github.com/ChengshuLi/WorldAtlas/issues/1175), which follows the completed crosswalk work in [issue #998](https://github.com/ChengshuLi/WorldAtlas/issues/998). It does not replace or edit the original Serbia packets, source files, crosswalks, or reports.

## What the guard now verifies

The guarded_reproduce.py runner binds its work to the issue's captured 78 ordered subject IDs, its declared evidence path and dependency, the closed live #998 issue, and the 35 exact complete-file inputs listed in source/pinned-inputs.json. The inventory includes the immutable c944e017796005726150abef19763db9ffd07154 baseline and the prior packet at e5393834c715396a60967d366523712edd5d1b65. Before creating any result directory, it checks every whole-file byte count and SHA-256, the pinned prior reproduction code, the full issue contracts, exact 78-subject equality, the complete 145-feature source roster, all 78 source-ID/name matches, 13 parent contexts, and the indexed Atlas containing-file mapping using worldatlas-evidence-preparation-v1.

The runner uses the retained original generator only after those checks. It runs in a private temporary tree, writes into a new exclusive staging directory, validates the complete output set and all original result pins, and atomically publishes only a fully successful run beneath results/run-<id>/. Rejections leave existing output bytes unchanged and publish no partial reports. Python and all direct/transitive spreadsheet dependencies are version-pinned in requirements-reproduction.txt; the runner refuses other versions instead of writing a misleading runtime summary.

Reproduce two fresh runs from the repository root:

    python3 -m pip install -r data/regional-review/serbia-register-reproduction-998-erratum/requirements-reproduction.txt
    python3 data/regional-review/serbia-register-reproduction-998-erratum/guarded_reproduce.py --validate-only
    python3 data/regional-review/serbia-register-reproduction-998-erratum/guarded_reproduce.py --output results/run-YOUR-UNIQUE-ID-A
    python3 data/regional-review/serbia-register-reproduction-998-erratum/guarded_reproduce.py --output results/run-YOUR-UNIQUE-ID-B

The runner verifies the immutable baseline with the repository's shared helper, so it reads all indexed world parts from Git. Each ordinary part remains below 32 MiB and the complete scan stays within the recorded 256 MiB preparation budget. Output paths are exclusive and must be new.

## Reproduction results

Two runs on Python 3.12.14, pandas 2.2.3, xlrd 2.0.2, and openpyxl 3.1.5 produced identical bytes for all eight files. Seven files match the original historical bytes exactly. The new reproduction-summary.json differs only because it truthfully records this run's Python and pandas versions (the old report records its older runtime); all findings are identical after excluding those two version fields. The subject crosswalk remains 78/78 unique 2017 and current name matches, 78/78 same code/name/type/parent outcomes, and zero code/type/parent discrepancies. The 13 scoped parent rosters remain exact (13/13). The current register continues to show 19 urban-municipality rows beneath city features in scope; none is a new #998 subject.

## Failure controls

The retained controls exercise complete-file failures before output, including the exact 919-byte synthetic metadata fixture with a changed boundaryYear, a 77-subject whole-issue fixture, altered baseline/workbook/original-generator bytes, shortened/duplicate/unmatched rosters, and an already-existing output directory containing a sentinel. The fixture bytes are never written over an original. Each rejection is expected to leave no new result directory; the existing-output case must preserve its sentinel unchanged.

## Source scope and geographic limits

The original evidence identifies the 78 scoped Atlas IDs as unique name matches in the retained 145-feature geoBoundaries ADM2 layer and as a candidate name/code/type/parent crosswalk to the SORS 2017 roster and the SORS current-state workbook retrieved 2026-10-05. The geoBoundaries metadata labels boundaryYear 2017 while recording a 2023 source update and build; those fields do not establish legal or effective boundary vintage. The layer is sourced from the pinned geoBoundaries commit in source/pinned-inputs.json; its retained notice states ODbL 1.0 and OSM attribution requirements. The SORS workbook and map terms recorded by the prior packet allow redistribution with changes marked and SORS cited.

This erratum validates preservation and reproducibility of those prior findings, not their territorial truth. No dated RGA/SORS legal polygons, official feature-level join key, legal boundary vintage, or polygon reuse terms were acquired. The 78 name/code rows do not prove source-feature polygon identity, legal boundary accuracy, all-Serbia completeness, or current governance. The 67 other non-scoped source features, 29 Kosovo-and-Metohija statistical primary roster codes, and urban-municipality child geometries are outside this subject scope. SORS's statistical availability statement does not resolve territorial status or the legal meaning of registry groupings.

The Atlas currently models Belgrade as a one-child province parent whose child repeats the city entity; SORS identifies Grad Beograd as a city. This is a sourced engineering handoff requiring a separately authorized hierarchy review. Preserve all current IDs and parent links pending that review. No boundary, hierarchy, source archive, live geography, database, import, release, publication, or regional approval is changed or authorized here.

## Follow-up

- Engineering/hierarchy owner: evaluate Belgrade's parent tier and singleton-child role while preserving the existing member ID and records.
- Geography/source owner: obtain dated RGA/SORS register extracts for the 78 units and 13 parents, including codes, types, parent codes, effective dates, polygons, CRS, data dictionary, and reuse terms; then compare polygons and source-feature identity.
- Geography owner: resolve the boundary vintage and the broader neighboring-granularity/completeness questions only in their separately scoped issues.

These unresolved questions remain explicit. Passing the byte and reproduction controls is not regional completion, geographic approval, publication readiness, or authorization to import historical data.
