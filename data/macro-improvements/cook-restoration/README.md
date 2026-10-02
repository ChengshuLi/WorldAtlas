# Cook Islands physical identity correction preparation — issue 502

This is a candidate package for the root publisher to combine with the independent omitted-land additions. It does **not** install geography, rewrite history, rebuild the canonical grid, or publish the Site. Regional interior review remains open.

| Existing physical identity | Original reference label | Correct present-day reference | Proposed change |
| --- | --- | --- | --- |
| COK-4951 | Aitutaki | Manuae | Name and existing province label only; exact current footprint and province ID preserved |
| COK-4956 | Palmerston | Aitutaki | Name and existing province label only; exact current footprint and province ID preserved |
| COK-4961 | Manihiki | Manihiki | Existing ID retained; replace generalized water-filled outline with the entire named atoll's sourced dry-land footprint |
| New bcec1e1e5eb00bd49e80 | — | Palmerston | One named atoll location, not 34 island/rock locations; one source-justified remote-atoll province |

The complete location IDs and five adjacent-tier parents are in `prepared/candidate-patch.json`. Existing source aliases are recorded as **erroneous reference labels**, never promoted to historical names or verified aliases. No coordinate swap, reparenting of existing physical IDs, historical label rewrite, ownership inference, or claim transfer is proposed.

## Original-source check

The installed Cook features declare Natural Earth ADM1 fallback, not geoBoundaries. The full pinned Natural Earth file was fetched and SHA-256 checked against `data/sources.json`: `22d0e3ad85eb3e27f17cabf8ba2d50e554fbc27a87796ff891d958185da62fb5`. Its original COK-4951 and COK-4956 feature labels are themselves Aitutaki and Palmerston at the wrong islands. The exact three original feature objects are retained losslessly; their geometry is not altered to make the names fit. The source is public domain. The contemporary geoBoundaries COK ADM1 availability request returned HTTP 404, retained as an availability result rather than geographic evidence.

The modern alternative is the original OpenStreetMap API XML retained in the merged issue-42 package, `../macro-coverage-oceania/`. Its source URL, raw-byte hash, compressed archive hash, way IDs, versions and timestamps accompany each derived footprint. OpenStreetMap data is ODbL 1.0, © OpenStreetMap contributors; retain attribution and derivative database obligations. The correct [Palmerston Island](https://en.wikipedia.org/wiki/Palmerston_Island) gazetteer is archived here under CC BY-SA 4.0. The older issue-42 `Palmerston` page was a disambiguation page and is **not** used to establish atoll identity. Manuae/Aitutaki/Manihiki source names and whole-atoll descriptions remain traceable to the issue-42 gazetteers.

## Dry land and water

The producer assembles directed complete coastline rings by exact source node IDs, uses their orientation to distinguish land and water, and subtracts complete explicitly tagged inland-water polygons. Incomplete nodes/chains, invalid rings, and unimplemented water multipolygons fail preparation; no automatic geometric repair hides source defects. Positive-area conflicts with every other current location are tested using the repository's WGS84 area implementation.

Manihiki comprises 84 coastline land rings, grouped into one territory, with two sourced pond masks removing approximately 0.0218 km². The old generalized 1.8733 km² outline has zero overlap with those dry-land rings and is retained verbatim in the archive; it is not treated as physically lost land. Palmerston's 34 coastline rings remain one atoll; its separately mapped lagoon removes approximately 0.0329 km² of coastline/water-layer overlap. Source layer disagreements are quantified rather than certified as perfect shoreline accuracy. Only modern reference support `[2026,2027)` is claimed; this is not evidence of unchanged coastlines or labels over all historical years.

The exact committed canonical rasterizer finds 229 cell centers on corrected Manihiki dry land and 144 on Palmerston. These are isolated representation checks: current global ownership is neither compiled nor uploaded. Small source islets may still lack their own cell center; the geographic location represents the whole named atoll, and no neighboring water pixel is reassigned.

## Replay and integration

From a fresh checkout with Python shapely/pyproj/numpy available:

```sh
python3 data/macro-improvements/cook-restoration/prepare.py --output /tmp/cook-candidate
python3 data/macro-improvements/cook-restoration/test_prepare.py
```

All replay inputs are committed here or in the merged issue-42 package; no `/tmp` research artifact is needed. `prepared/index.json` pins the deterministic outputs and producer. `originals-and-records.json.gz` preserves all affected installed feature/property objects, exact province objects and matching retained catalog/archive rows. Every retained original archive is inspected for a Palmerston physical predecessor; unrelated Australian Palmerston and erroneously labelled COK-4956 are explicitly distinguished. Private current database records cannot be certified from Git and require the root publisher's live preflight before application.

The source-backed creation proof is explicitly for the state **after the name crosswalk**. It must not be passed directly to the pure-create staging command with the old names or mixed footprint replacements. The root must process retained-ID metadata corrections, retained-ID geometry evidence and genuinely new land using their respective migration contracts. This package does not claim that its candidate JSON alone is a valid geographic release receipt. The separate release chronology blocker must be fixed rather than bypassed.

## Bounded followups

Manuae and Aitutaki whole-atoll source footprints are included as review evidence only: 7 and 28 coastline rings respectively, with explicit inland water masks. Existing COK-4951/COK-4956 geometry stays byte-identical in this proposal. Their additional islet coverage belongs to the existing South-Central Pacific regional interior audit, where the local territorial role can be reviewed properly. No extra scope or new count quota is introduced here.
