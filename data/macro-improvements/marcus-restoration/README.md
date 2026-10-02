# Minamitorishima / Marcus Island restoration candidate (issue 506)

Recorded 2026-10-02, America/Los_Angeles. This bounded package stages one complete
named island omitted from geographic release 3. It preserves every existing
location, parent identity, original source, archived footprint and historical
record. It does not install geography or approve regional interiors.

The finite source-backed macro amendment routes **Minamitorishima / Marcus Island
→ Northwestern Pacific → Micronesia → Oceania**, with a reciprocal named exclusion
from Japan. WGSRPD edition 2 explicitly distinguishes Marcus from Bonin/Volcano:
printed page 5 (PDF page 21) retains the low island in the Pacific, and its MCS-OO
table on printed page 30 (PDF page 44) assigns Northwestern Pacific. This botanical
reporting convention is an explicit atlas choice, not a uniquely proven geological
continent. JMA independently describes the detached, low coral island. Modern
Japanese sovereignty and Ogasawara/Tokyo administration remain separate context;
no owner or historical attribute is assigned by this producer.

`proposal.json` defines the exact named-land domain, reciprocal neighboring route,
stable candidate IDs and provisional lower-tier exception. No EEZ, seamount chain,
other Japanese island or shared mainland edge is transferred. The new province
“Marcus Island” contains the local island territory; “Marcus isolated island” is
its detached geographic area. These atlas containers share a footprint because
no sourced intermediate subdivision or wider physical island group was found.
They explicitly remain a single-child, coextensive-tier exception with open
regional-interior review. The island is not assigned to Wake/Mariana units by
proximity or to the Japan macro region by sovereignty.

`original-map.osm.xml.gz` retains the exact OSM API extract, including way 130970566
version 27, dated 2025-12-20. `dry-land.wkb.gz` retains the exact reviewed land after
subtracting its one mapped inland-water polygon. Preparation reconstructs both
coast and water directly from the XML and checks equality with retained WKB. The
WGS84 dry-land area is about 1.456 km²; this source/vintage differs from the rounded
1.51 km² official reference. No geometry is enlarged to match a headline area.
OpenStreetMap contributors receive attribution under ODbL 1.0; extraction and
derivative-database obligations remain applicable.

`routing-research.json` cites each inspected source, exact original byte hash,
vintage, retrieval date, inspected facts and reuse terms. Original JMA pages are
retained under Public Data License 1.0; translations/paraphrases are indicated here.
The peer-reviewed article retains its CC BY 4.0 terms; Wikipedia text retains
CC BY-SA 4.0 contributor/history attribution. No source imagery was imported.
The rights-reserved WGSRPD PDF is **not newly redistributed**. Its exact inspected
original URL/hash and page citations are retained; the prior published macro
source inspection records remain unchanged. The inspected original is retained
locally and can be retrieved again from its hash-pinned public URL for inspection. The MLIT PDF is supplementary citation only
because its exact reuse license was not established. Neither PDF is required to
rerun the geometry or candidate checks.

From a complete checkout with Node 24 and the pinned Python dependencies:

```sh
node data/macro-improvements/marcus-restoration/reproduce.mjs \
  --root=/absolute/path/to/WorldAtlas \
  --output=/absolute/path/to/fresh-marcus-candidate
node data/macro-improvements/marcus-restoration/check.mjs \
  --root=/absolute/path/to/WorldAtlas \
  --stage=/absolute/path/to/fresh-marcus-candidate
node --test test/marcus-restoration.test.mjs
```

The producer accepts only the exact pinned release-3 baseline, preserves original
part bytes, scans every current footprint and both retained geometry archives,
checks original and subsequently registered identities, and rejects existing land,
IDs or unadjudicated exact name/alias matches. Its generic source-backed creation
receipt has no predecessor and transfers no history. Local scans do not establish
absence in the private live registry; publication requires authorized preflight.

`candidate-patch.json.gz` is the exact new feature/groups and macro proposal.
`creation-proof.tar.gz` retains the complete successful generic migration manifest
and source/hierarchy/receipt bytes; `outputs.json` pins each unpacked member.
`identity-review.json.gz`, `geometry-measurements.json` and `grid-report.json` retain
the exhaustive local scan and representation outcomes. The original canonical
lattice represents the island with **74 cell centers**, zero existing owned-cell
conflicts, and approximately **−1.73%** WGS84 area distortion. Only a bounded island
window was rasterized; checked baseline ownership chunks were read and hashed.
No world ownership grid was compiled, changed or uploaded.

`validation.json` records the independent preservation and complete-chain checks.
`release-probe.json` and `identity-proof-sequence.json` retain successful preparation
of a read-only release-4 candidate: original repair geometry → four original macro
metadata receipts → this creation geometry. Every proof is hash pinned; the old
receipts and certificates are immutable. The independently validated reverse
geometry chain remains intact. This single-island probe is not the combined
release that issue 45 will publish alongside other corrections.

Publication stays under issue 45: private identity/claims preflight; the coordinated
named macro amendment and bottom-up envelopes; source-gap and neighboring routes;
new cached global grid and matching ownership/environment products; static/hosted
release checks, package limits and certificate/content-scope revalidation. New
attributes remain unknown unless separately supported. Regional research imports
remain closed until a complete branch certificate is published.
