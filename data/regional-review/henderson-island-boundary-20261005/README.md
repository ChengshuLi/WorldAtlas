# Henderson Island boundary source investigation

**Issue:** #1060 · **Subject:** `PCN+00?` · **Research date:** 2026-10-05 (America/Los_Angeles)
**Disposition:** research complete with limits; source lineage identified, dedicated current authoritative shoreline source not obtained. No correction is proposed. This packet does not certify coastline accuracy/completeness, approve geography, or authorize an import.

## Finding

The current Atlas footprint for Henderson Island is derived from Natural Earth's four-island Pitcairn Islands Admin-1 geometry. The 2022-06-02 Natural Earth source feature is one four-component MultiPolygon named “Pitcairn Islands”; its third component is Henderson. A deterministic comparison in `reproduce_henderson.py` shows the current 9-position ring matches that component after Natural Earth coordinates are rounded to the Atlas's four decimal places (coordinate order/direction ignored). The other three components are the source's Pitcairn, Ducie, and Oeno island outlines by their positions. This is a lineage match, not evidence that the coordinates are a contemporary surveyed coastline or a legal boundary.

The UK Pitcairn Constitution Order 2010 defines Pitcairn as Pitcairn, Henderson, Ducie and Oeno Islands, supporting a four-island parent relationship but defining no coastline. UNESCO's Henderson World Heritage page identifies Henderson as a remote, uninhabited raised coral atoll in the Pitcairn Islands group (3,700 ha); it explicitly says georeferenced property polygons will be made available after UNESCO receives GIS data. The UNESCO map catalogue lists a 2004 outline map, but the linked document could not be retrieved as bytes during this investigation (HTTP 403). UNESCO syndication terms require prior written authorization to republish its material. The map is therefore restoration-only and is not copied into this packet. A World Heritage property description or image map does not establish the island's complete land-water coastline.

JNCC lists Henderson as a *potential* Ramsar site, not a designated Ramsar site, and its official Ramsar GIS boundaries exclude UK Overseas Territories. The 3,700 ha listed there is not a land-outline dataset. A 2004 Ramsar information sheet located on a third-party host describes a proposed marine boundary at the 50 m depth contour or 1.5 km offshore; it is not an island shoreline. The UK government biodiversity strategy corroborates the four-island archipelago and the raised-atoll distinction, not a boundary.

No dedicated, lawful, current Henderson coastline source was found in the sources inspected. This is a bounded search result, not proof that no such source exists. Natural Earth publishes public-domain generalized cartographic data (1:10m scale here); it is the only retained machine-readable island outline located, and it is a broad administrative group comparator. The baseline Atlas footprint is exactly that island component rounded to four decimals. The parent comparison's intersection-over-union (~0.904) compares Henderson against all four islands together and must not be interpreted as a Henderson completeness score.

## Territorial meaning, parent and neighboring granularity

Henderson is a physical island and UNESCO property within the four-island Pitcairn Islands group. The exact Atlas parent `framework:province:pitcairn-islands:d483df587794` is preserved. Named neighboring islands in the parent are Pitcairn, Ducie and Oeno. Natural Earth's source contains four distinct components under one group feature, while the Atlas has an individual Henderson feature; this difference in granularity is expected and explains why treating the whole Admin-1 polygon as Henderson would be wrong. The legal order establishes group membership but supplies no island delimitation. UNESCO's 3,700 ha describes the World Heritage property; the 2021–2026 marine protected area plan refers to a 42.7 km² island area in a different management context. Those figures have differing purposes and are not substituted for a coastline measurement.

## Reproduction and evidence

From the repository root, run:

```sh
python3 data/regional-review/henderson-island-boundary-20261005/reproduce_henderson.py
node scripts/evidence-quality.mjs data/regional-review/henderson-island-boundary-20261005/evidence-quality.json
```

The Python 3 standard-library reproduction verifies the pinned source bytes and baseline file pins, finds exactly one Pitcairn Admin-1 feature, checks the four source components, matches the Henderson component by its bounded coordinates (not component index alone), canonicalizes the ring independent of winding/start vertex, and compares it to the current Atlas ring at four decimals. It also checks all other source components as negative controls. Generated findings are in `findings/component-lineage.json`, `findings/positive-control.json`, and `findings/negative-controls.json`. Hashes establish byte identity only. This reproduction does not calculate coastline completeness, positional accuracy, shoreline distance, legal boundaries, or survey error.

Natural Earth original source: pinned commit `ca96624a56bd078437bca8184e78163e5039ad19`, commit date 2022-06-02; original full Admin-1 SHA-256 `22d0e3ad85eb3e27f17cabf8ba2d50e554fbc27a87796ff891d958185da62fb5`; exact retained regional extract SHA-256 `dd3f4a5683c713fd89c00b41748d89771f905ef236feaacb7887818085f3d96e`. The regional extract is already retained at the pinned main baseline path in the manifest. Its recorded deterministic filter keeps features whose admin field is Cook Islands, French Polynesia, Pitcairn Islands, or U.S. Minor Outlying Islands. The source is public domain; no new source bytes are redistributed here.

## Engineering handoff and unresolved work

- Keep `PCN+00?`, its name, parent, and historical/release identity unchanged. No sourced evidence justifies altering the current coordinates.
- A future geometry correction requires an island-scale source with documented vintage, positional method, territorial meaning, full source coverage of coastal rocks/islets, reuse terms, and enough detail to assess whether it represents land coastline or a marine/heritage area. Potential primary leads are Pitcairn administration, UK Hydrographic Office charts, and a new UNESCO/state GIS delivery; inspect licensing and access before retaining data.
- Obtain the UNESCO map through an authorized channel if it is needed; do not republish its image or derive/repackage geometry without permission. The currently linked map document returned 403 and has no verified local hash.
- Current complete shoreline and small-islet inclusion remain unresolved. This packet is research-only, not a regional certification, correction PR, or publication request.
