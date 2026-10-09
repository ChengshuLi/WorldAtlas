# Portugal–Spain validator preservation erratum

Issue [#1348](https://github.com/ChengshuLi/WorldAtlas/issues/1348) documents a bounded preservation defect in the control CLI retained by PR #1123. The original entry point writes `positive-control.json` and `negative-control.json` before it compares the retained run-09/run-10 reports, then writes `reproducibility.json`. Those three paths already contain historical receipts. A mismatch can therefore replace two receipts before failing, while a successful rerun can replace all three with a different execution-vintage record.

This erratum leaves that original packet and its outputs untouched. The bounded runner reads the exact issue-pinned Git blobs from baseline `777b082b0a3447c39205255312ec69f453e85e7a`, copies only the validator, analysis module and two retained reports to a disposable repository, and invokes the original validator unchanged there. It performs two fresh successful runs, checks the actual positive half-gap and disjoint negative controls, and exercises a different-byte run-report failure. For the failure case, the legacy CLI creates only private partial controls and rejects the report pair before creating its completion receipt. No private output is promoted. A complete published vintage contains the six successful receipts, an explicit byte-identical cross-run comparison, the failure observation and fresh-output admission controls; the shared `NewVintage` writer admits the entire output set and writes its completion receipt last.

Run once with a new vintage name from the repository root, using Python 3.12 and the installed Shapely, GEOS and PyProj dependencies recorded in `admission-controls.json`:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B research/geography/prt-esp-control-preservation-1123-erratum/scripts/reproduce-preservation.py UNIQUE-VINTAGE-NAME
```

The runner uses a deterministic temporary Git commit solely because the unchanged legacy CLI records `git rev-parse HEAD`. It is a commit of the exact copied code and reports, not an Atlas release or new source vintage. Original issue pins are checked both before sandboxing and after all runs. Outputs from this run are evidence about control execution and preservation; they do not refresh or replace the historical PR #1123 receipts.

## Subject and geographic limits

The exact seven original subjects are three Atlas Spanish districts (Brozas, Valencia de Alcántara and Coria) and four Portugal geoBoundaries ADM2 units (Nisa, Idanha-a-Nova, Castelo Branco and Vila Velha de Ródão). Their identity bindings are checked against the complete baseline part-28 and part-19 files. The retained #1123 packet describes their administrative roles, parent context, neighboring granularity, source vintages and source-specific reuse statements. This erratum neither repeats external source acquisition nor recalculates the regional comparison.

The earlier packet is explicit that current IGN/CAOP municipal polygons are administrative reference geometry, not a mutually authoritative international line. The selected IGN line records do not by themselves establish bilateral authority; linked product records and coordinate annexes were not retained. The CAOP2025 collection metadata conflicts with its 2000–2007 temporal extent. Physical land/water, channel movement, datum/registration history, territorial assignment and a complete legal seam remain unresolved. The seven IDs are a bounded reproduction scope, not a claim that the whole region or gap is geographically certified.

No external source bytes were added here. The original packet retains exact source hashes, retrieval receipts, dates and source-specific terms; see its README and evidence manifest at `research/geography/shared-seam-prt-esp-20261006/`. Its uncertainty and licensing limits continue to apply. The erratum provides no boundary approval, map correction, live import, deployment or publication authorization.
