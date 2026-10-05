# Issue 423: Southeastern Europe interior batch 8, Yugoslavia

Research packet only. This records what was checked for the issue's exact 278 IDs; it does not certify all of Southeastern Europe, all 1,169 Yugoslavia-area members, or authorize edits to core geography.

## Scope and reproduction

- The immutable issue scope is `scope.json`: 278 unique IDs, exact sorted-ID SHA-256 `e5db7702819affa14cb1d75948102332e5c50ec148212ef1e1d7393f2693b471`, area `framework:area:yugoslavia:cff5e9ba6c8e`, region Southeastern Europe.
- `unit-assessments.json` retains one row per scoped ID, exact source shape identity, parent, source role/year/license, current Slovenia municipality crosswalk when possible, and independent identity/name/boundary findings.
- `reproduce_scope.py` reproduces the packet ID hash and source joins. It verifies the issue's 1,169 area count and all 278 IDs against the complete pinned-v5 and current-main inventory. Both inventories contain 1,169 IDs with sorted-ID SHA-256 `ff60a7cfb463a8e5206fadbba78655153d374634d6f4b9f5639fda5f3603312c`. The hierarchy's semantic-review sentence saying 1,162 is stale narrative; it is not supported by either inventory.
- The packet consists of 67 Serbian and 211 Slovenian ADM2 members. This is a bounded sample, not a complete national inventory.

## Territorial meaning and parent tiers

- The Serbian packet's 67 features resolve exactly to retained geoBoundaries SRB ADM2 shapes from upstream commit `9469f09592ced973a3448cf66b6100b741b64c0d` and the 2017 source vintage. Their parent IDs point to 12 Serbian ADM1 district shapes. The official Statistical Office of the Republic of Serbia describes 29 administrative districts and national municipal/city totals. GeoBoundaries SRB ADM1 contains 25 features, including Belgrade, while its SRB ADM2 set contains 145 units. The 67 issue members are therefore a subset of this source hierarchy. Without current RGZ/RZS per-unit geometry retained and crosswalked, the issue cannot establish current boundary equivalence or each feature's present legal/administrative status.
- Slovenia's 211 features resolve to retained geoBoundaries SVN ADM2 shapes from upstream commit `9469f09592ced973a3448cf66b6100b741b64c0d` and the 2017 source vintage. The Government of Slovenia currently reports 212 municipalities; its official statistical geography consists of 12 NUTS3 statistical regions grouped into two NUTS2 cohesion regions (8 east, 4 west). The two large packet parents, `Vzhodna` (147 packet members) and `Zahodna Slovenija` (61), are cohesion-region tier parents, not province/district units. This differs in scale and administrative meaning from Serbian district parents; an explicit model decision is needed if the `province` tier is intended to cover both.
- Three additional one-child parent records named Ankaran / Ancarano, Izola / Isola, and Piran / Pirano each contain the corresponding coastal municipality. Current GURS confirms the municipality names and identities but does not establish these municipality-duplicating parent records as a valid administrative tier. Existing Atlas metadata reports source-geometry incompatibility for these records. Do not reparent or merge them based on this packet; review the intended parent tier and test complete polygon geometry.
- `province-assessments.json` enumerates all 17 scoped parent records and their exact scoped child IDs. It deliberately distinguishes supported source parent identity from unresolved current boundaries, full-parent completeness, or semantic appropriateness.

## Per-feature findings

- All 278 exact Atlas IDs have matching geoBoundaries `shapeID` records in the retained source vintage; all source records report municipal role and 2017 reference year.
- For the 211 Slovenian scoped features, current official GURS provides 212 municipality polygons. The crosswalk identifies 211 distinct official codes: 208 representative points fall in exactly one current municipality polygon; the three coastal bilingual aliases map by explicit alias (`Piran / Pirano` → Piran, `Izola / Isola` → Izola, `Ankaran / Ancarano` → Ankaran) where the source representative point falls outside its current polygon. This is a current identity/name crosswalk, not proof of historical or polygon equivalence.
- 53 Atlas names differ from the matched current official GURS names after case/diacritic/punctuation normalization. `slovenia-name-correction-candidates.csv` gives the stable Atlas IDs, source names, current GURS codes/names, and feature dates. These are review candidates only: check date-specific official records and source vintage before proposing a rename; preserve IDs and record name history if an edit is justified.
- Current official Serbia unit polygons were not included. Serbian identity, role and historic parent source are supported, but current geometry and boundary adjudication remain insufficiently evidenced.
- A simple sample of up to 25 source vertices per Slovenian feature is recorded as a diagnostic only. It is not an area-weighted overlap, Hausdorff distance, topological check, or accuracy score. Boundary finding remains `insufficient-evidence` for every row.

## Area meaning and neighboring scope

The attached area-level source identifies WGSRPD (World Geographical Scheme for Recording Plant Distributions), whose purpose is plant-distribution recording. Its level-3 botanical-country groups may ignore political boundaries, and TDWG lists the standard as Prior. That evidence does not by itself define a present-day country or a coherent modern area called Yugoslavia. The area meaning and historical treatment need explicit integration review; no area membership is certified by this packet.

Hodoš (`gb:SVN:ADM2:79292919B24353346281842`, source name “Hodoj”) is outside #423 and is owned by #424. It appears there as the sole member of a same-name one-member area under Southeastern Europe. `neighboring-context.json` records the handoff to umbrella #415. #423 does not adjudicate or alter that record.

## Engineering handoffs and limits

1. In the existing #415 integration, reconcile Yugoslavia area's modern/historical semantic definition with the WGSRPD purpose, and compare all packets including #424's one-member Hodoš child. Do not equate the botanical unit to a modern state without supporting evidence.
2. A bounded engineering review should evaluate the 53 candidate name crosswalks against date-specific official historical names, and decide whether names/history need a sourced correction while preserving stable IDs.
3. A bounded engineering review should resolve the `province` tier semantics for Serbia districts versus Slovenia cohesion/statistical regions and the three singleton coastal parent records. Any eventual geometry or hierarchy change needs complete-source polygon and neighboring-granularity review.
4. Retain/retrieve an authoritative current Serbia unit geometry/register export with lawful reuse terms, exact vintage, hash and full per-ID join before making current Serbian boundary claims.

No raw evidence outside the declared packet directory was modified. Original geoBoundaries and GURS data retained here are licensed for the stated attribution/reuse. For authoritative web pages whose redistribution terms were not confirmed, this packet retains only facts, URLs, retrieval dates, and explicit restoration directions in `source/source-provenance.json`.
