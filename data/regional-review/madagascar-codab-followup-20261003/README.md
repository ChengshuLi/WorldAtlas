# Madagascar COD-AB follow-up (#632)

## Scope and disposition

This is additive source-history and boundary-comparison evidence for all 120 OCHA COD-AB Madagascar v01 ADM2 units and 24 ADM1 units, compared with the 119 current Madagascar location IDs and 22 current parent groups pinned at `b765c34077b6d7c5745c7285f08e954edd62144a`. It does not edit shared hierarchy, geography, production data, source archives or history. It does not certify any region, authorize an import, or decide legal boundaries.

The current OCHA layer is a reviewed but old-vintage reference: its metadata says review 2026-07-06, boundaries created 2009-08-01, `valid_on=2018-08-10`, `valid_to=null`, version `v01`; the source package was modified 2026-08-14. Per the OCHA specification, `valid_on` describes a dataset version update, not a legal effective date. Its 120-district/24-region roster therefore cannot by itself establish the current legal administration.

## Reproduction

Run the script with Python 3 and the already available `pyproj` and Shapely dependencies from the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 data/regional-review/madagascar-codab-followup-20261003/reproduction/reproduce_codab.py --run-id YYYY-MM-DD-v1-run-N
```

`--run-id` is a new lowercase token. Each run reads Git blobs at the immutable baseline listed in `input-pins.json`; it refuses to overwrite existing or partial output. It never invokes the inherited comparison script that writes into the parent packet. `completion.json` is written last. EPSG:6933 is used for equal-area comparisons. Invalid shapes, if any, are repaired only in memory with Shapely `make_valid`; source geometry bytes remain unchanged. The 5% ADM2 threshold is a triage flag, not a legal tolerance. The component screen retains each source ADM2 polygon part above 0.01 km² with under 1% overlap against the union of every current Madagascar location. Neither that screen nor a GSHHG non-hit proves physical land presence or absence.

For two-run reproducibility, create a full first run, then invoke the same script with a fresh run ID and `--compare-to FIRST_RUN_ID`. The second invocation recomputes every product in memory and compares all output bytes, sizes and hashes to the retained first run; it writes only `reproducibility.json`, avoiding a duplicate copy of the 528-row intersection matrix. The accepted first run is `vintages/2026-10-07-v1-run-12/`; the second-run control is `vintages/2026-10-07-v1-run-13/reproducibility.json`. Both product-bundle hashes equal `40741de6a374fc0ade72b2f96943541303e9291a7c443f629fb4d21d6a2fa2d8`. Earlier draft failures identified a nationwide duplicate-name assumption and source-registry key path; they produced no accepted outputs and are not included. An adverse collision check confirms the first result is left intact when its run ID is reused.

`controls.json` provides source-backed positive control Tsihombe (`MG52514` in 2018 COD-PS and COD-AB, joining one current ID), level-aware negative control Antanimora Atsimo (COD-AB ADM2 does not join the 2018/current ADM2 roster while the same 2018 name is ADM3 Commune `MG52516130` under `MG52516`), a repeated-name control (two distinct nationwide Ambohimanambola ADM3 rows), and a negative parent-mutation control: changing the actual source parent name and code together from Antananarivo Avaradrano to Betafo changes the unique selected commune code from `MG11102050` to `MG12109250`. Synthetic identical/disjoint geometry controls check metric arithmetic only; no control validates Madagascar boundaries.

## Findings

### District crosswalk and boundaries

- The retained COD-AB ADM2 roster has 120 unique p-codes and 120 unique normalized names. All 119 current Atlas IDs join one-to-one by normalized exact name; the sole unmatched source unit is Antanimora Atsimo, `MG52519`, parent Androy `MG52`. This is a name crosswalk, not a determination that all 119 name matches are legally identical units.
- The 2018 COD-PS source has 119 ADM2 rows, 1,579 ADM3 rows and 17,465 ADM4 rows. It is older population/admin-code evidence, not boundary geometry. 105 of the 119 name-joined current rows retain the same ADM2 p-code in COD-AB; the remaining 14 code differences need vintage-aware treatment and must not be silently interpreted as unit changes.
- 15 name-matched ADM2 geometry rows exceed 5% symmetric difference divided by union area: 1er, 2e, 3e, 4e, 5e and 6e Arrondissement; Antsirabe I; Fianarantsoa I; Toamasina I; Sainte Marie; Mahajanga I; Toliary-I; Ambovombe-Androy; Antsiranana I; and Nosy-Be. The row-by-row percentages, overlaps, area changes, p-codes, IDs and validity/repair flags are in `vintages/2026-10-07-v1-run-4/adm2-crosswalk-and-geometry.csv`.
- Antanimora Atsimo is not the same source-level observation in each vintage. 2018 COD-PS lists it as Commune `MG52516130` (ADM3) under Ambovombe-Androy `MG52516`; 41 retained ADM4/fokontany rows point to that commune. COD-AB v01 lists it as a new ADM2 record `MG52519` under Androy. The 2020 INSTAT errata confirms the page-81 column is Commune/Arrondissement and corrects its name to Antanimora Atsimo; it does not show a 2018 district. Decree 2024-480 schedules Antanimora Sud under Ambovombe prefecture with eight communes, but an INSTAT 2026 operational notice lists four. The promulgation/date of the decree is not the exact radio/TV publication date needed for its effective date. Neither commune roster supplies verified district polygons, and the predecessor code/territory continuity remains unresolved.
- Antanimora `MG52519` has 3,974.299 km² in its retained COD-AB geometry. Equal-area overlays assign 99.534% of it to the current Ambovombe-Androy polygon, 0.204% to Bekily, 0.148% to Amboasary-Atsimo, 0.071% to Beloha, and 0.043% to Tsihombe. This exactly addresses the named neighbor screen but is not an adjudication of legal adjacency, land status, or boundary correctness. Full values and current parent context are in `antanimora-neighbor-intersections.csv`.
- The full COD-AB ADM2 union intersects 99.928% of the current 119-location union, with 0.149% symmetric difference and +0.005% relative area. This supports near agreement of the overall source/current envelope, not internal assignment, settlement completeness or legal boundaries.
- The source ADM2 polygons contain 202 components; 55 candidates pass the stated disconnected-component screen (64.588 km² total). Every candidate and any current-location intersection is retained in `disconnected-components.csv`. Their physical status stays unresolved. The inherited GSHHG L1 non-intersection screen is inconclusive.

### Region and parent reconciliation

The analysis compares all 24 COD-AB ADM1 geometries with all 22 current parent-group unions in the 528-row `adm1-parent-intersections.csv`. Most source regions overlap their like-named current group at over 99%; those measurements are source/current overlay evidence only.

- Law 2021-012 establishes Vatovavy from Mananjary, Nosy Varika and Ifanadiana, and Fitovinany from Manakara, Ikongo and Vohipeno. Current Atlas still has one `Vatovavy-Fitovinany` parent group. COD-AB Vatovavy overlaps that group 99.73%; Fitovinany overlaps it 84.37% and Atsimo-Atsinanana 15.48%. Source hierarchy, present parent arrangement and spatial overlay do not fully reconcile. Preserve all existing IDs and send any sourced parent/geometry proposal through the engineering cross-region review; no local reparenting is performed here.
- Law 2023-012 establishes Ambatosoa from Mananara Nord and Maroantsetra. Current Atlas still places these districts in Analanjirofo; COD-AB Ambatosoa geometry overlaps the current Analanjirofo union 99.53%. This is a clear administrative-source versus current-parent mismatch requiring an engineering hierarchy/geometry proposal with exact district identities and stable-ID treatment. Do not promote the current polygon overlay into a correction by itself.
- OCHA COD-AB lists 24 regions. The government portal currently accessible during research lists 23 regions/119 districts, gives older Vatovavy-Fitovinany context, and omits Antanimora; it has no visible update date and conflicts with the later laws/decree. The portal is retained as contradictory, potentially stale evidence, not controlling authority.
- COD-AB names Haute Matsiatra and the current group name Matsiatra Ambony. Their source geometry overlaps 99.74%, so this is a strong naming/lineage match but not proof that an alias or renaming date is settled.

## Engineering and research handoffs

1. Engineering should assess a sourced cross-region hierarchy correction for the 2021 Vatovavy/Fitovinany split, retaining district/location identities and reviewing all affected province parent assignments together.
2. Engineering should assess Ambatosoa's 2023 creation and the complete Mananara Nord/Maroantsetra member transfer from Analanjirofo, with preserved IDs, a dated legal source and matched boundaries before changing parentage.
3. Restore/inspect official current district/commune boundary sources for Antanimora Sud, resolve the decree eight-versus-INSTAT four commune list and publication/effective date, restore the exact BNGRC predecessor source and compare its codes/geometry to COD-PS and COD-AB. A district-level replacement/split or reparenting must be a separate engineering decision after this evidence.
4. Review each of the 15 flagged ADM2 geometry rows and all 55 component candidates against authoritative source scale, neighboring boundaries, offshore/island coverage and source vintage. The retained measurements identify review targets; they do not state corrections.

## Sources, license and integrity

`source-restoration.json` records the inspected primary source URLs, retrieval date, exact bytes/SHA-256 for official PDFs, source interpretations and license limits. Those PDFs are not redistributed because no explicit reuse license was located on the inspected copies. It also documents CC BY-IGO attributions and restoration facts for the inherited OCHA sources. The exact retained COD-AB member hashes are recomputed against the inherited registry by every run. Every input's Git blob ID, size and SHA-256 is pinned in each vintage's `input-pins.json`; the 2018 CSV hashes and source restoration URLs remain in the inherited parent registry. Current feature IDs, source pins and prior evidence are read-only inputs. The 2022 MapAction mapbook is a secondary code-history lead only; its stated BNGRC/GADM/OSM inputs are not a substitute for original BNGRC evidence.

## Explicit limitations

No exact legal effective date is established for laws whose effect is contingent on broadcast/publication. No OCHA `valid_on` value is treated as a legal date. The COD-AB and 2018 COD-PS statistical products do not prove every current legal boundary. Gazetteer/operational lists are not geometry. No new source bytes were sourced for the full 2024 commune-to-district polygons, predecessor BNGRC layer, or a definitive present-day administrative directory. Coastal/offshore disconnected components, local geometry displacements, overlapping claims and source completeness are not closed by counts, joins, metric thresholds or green reproduction. No hierarchy or production geographic decision is approved by this packet.
