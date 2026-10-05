# Central Africa batch 5: scoped geography evidence

This packet reviews exactly the 21 source IDs in issue [#464](https://github.com/ChengshuLi/WorldAtlas/issues/464): 19 Gabon departments and the two São Tomé and Príncipe island-level features. It preserves the issue's five declared parent groupings and pinned region scope. It proposes no hierarchy, geometry, footprint, history, release, or production changes. These results do not approve the Central Africa region or authorize imports.

## Findings

The 19 Gabon features are present by exact native ID in the geoBoundaries `gbOpen` source at commit `9469f09592ced973a3448cf66b6100b741b64c0d`. Its ADM2 metadata describes 49 features, representative year 2018, canonical type **Department**, source `geoBoundaries, Wikimedia`, update date 2023-01-19, build date 2023-12-12, and CC BY 3.0. The exact original GeoJSON and layer metadata are retained under `sources/` with byte lengths and SHA-256 hashes in `sources-manifest.json`; attribution and source-specific terms are preserved there.

The Gabon Ministry of Interior's 2018 administrative listing names all 11 departments in Haut-Ogooué, four in Ogooué-Ivindo, and four in Ogooué-Lolo. Eighteen of the scoped names match those official lists after accent and punctuation normalization. The remaining source feature `Mouloundou` is not a normalized match for the official listing's `Mulundu`; the alias, identity, and boundary relationship are unresolved. The Ministry's separate territorial-count table cites DGAT May 2016 and reports 48 departments overall, against geoBoundaries ADM2's 49 features. The public ministry pages are official primary context, but no byte-exact page hash could be acquired: direct retrieval timed out; we inspected the government-rendered pages. The names and counts have therefore been transcribed into `official-roster-extract.json`, clearly labeled as a worker transcription rather than original source bytes. The ministry pages do not supply a same-vintage GIS crosswalk or boundary lineage.

For neighboring granularity, the Ministry lists **province → department → commune → district → canton → village group → village**. That supports the administrative role of the department tier in the three scoped provinces. Separate geoBoundaries GAB ADM1 parent polygons are representative of 2005 and are licensed CC BY-SA 3.0; these are not same-vintage authorities for 2018 ADM2. `reproduction/subject-assessments.csv` reports the child area share inside the 2005 ADM1 polygon as a diagnostic for each exact subject. Values are about 0.893–1.000 in this subset. This is cross-vintage screen evidence only and cannot show that an underlying boundary is wrong or establish legal completeness. The federal source has independent ambiguity: the 2018 ministry page lists eight Ngounié departments while the separate aggregate table says nine. The national 49-versus-48 discrepancy and all official cross-vintage mappings remain unresolved.

For São Tomé and Príncipe, geoBoundaries ADM1 has two OSM/Wambacher-derived features (`São Tomé Province` and `Príncipe Province`), but its canonical role is blank and its metadata carries ODbL 1.0. The current INE country page says the 1980 Administrative Division Law defines seven districts: six on São Tomé and one on Príncipe; it describes Príncipe as currently an autonomous region. INE's RGPH 2012 report gives the six São Tomé district names, distinguishes district chambers from the regional government, and says Príncipe has been autonomous since 1996. The official 2017 statistics also list the autonomous region separately from the six São Tomé districts. Thus the source's word “Province” is not support for the current administrative role. The baseline currently nests each island feature under a one-child `province` parent of the same name. An island-level geographic grouping may still be defensible, but source role, tier purpose, and the duplicated same-footprint parent need an engineering decision. Both subjects are classified correction-needed for that role/tier mismatch; neither boundary is certified.

INE's report describes other small islands in addition to the two main islands. The two-feature ADM1 source therefore does not prove completeness of all dry land or associated islets. No authoritative district-level geometry for São Tomé's six districts was found in the inspected source set. INE PDFs and its current web page have no located reuse license; the packet retains restoration URLs, retrieval dates, byte lengths, exact SHA-256 hashes and inspected page/section references, but no PDF or HTML body. Restoration-only records are in `official-context.json`.

## Row-level disposition

`reproduction/findings.json` and its CSV cover all 21 exact issue subjects, with source identity, role, vintage, license, actual current parent, official roster comparison, geometry screen (Gabon), classification, and limitations. `province-assessments.csv` separately classifies each of the five scoped parent groupings. The two area-level assessments in the JSON preserve the issue's partial area coverage: this packet owns 19 of Gabon's 49 current locations and two of the Gulf island area's seven; sibling Central Africa packets #460–#463 own the other area members. They describe current grouping purpose and explicitly leave full-area completeness unresolved. Final location classifications:

- **19 insufficient-evidence:** Gabon source identities and the narrow Department role are supported; the official roster parent/name is supported for 18, while `Mouloundou`/`Mulundu` is unresolved. All 19 exact boundaries and source completeness remain insufficiently evidenced because ADM2 (2018) is compared to ADM1 (2005), the source lineage is not an official same-vintage boundary crosswalk, and the aggregate source count conflicts.
- **2 correction-needed:** the STP “Province” labels and one-child province parents do not match current official administrative roles. This flags role/tier purpose, not a claim that the island footprints themselves are wrong.
- **0 justified:** none of these findings should be read as approval of a whole region, source set, boundary, or national completeness.

Specific bounded follow-ups are [#866](https://github.com/ChengshuLi/WorldAtlas/issues/866) for the exact 19 Gabon IDs and [#865](https://github.com/ChengshuLi/WorldAtlas/issues/865) for the two STP IDs. Both are blocked on this parent packet and are not ready to claim. The Gabon issue seeks same-vintage official boundary/crosswalk evidence, especially for Mouloundou/Mulundu and the count discrepancy. The STP issue seeks official district/island boundary geometry or restoration instructions, source-to-current-role lineage, island completeness evidence, and a tier-purpose recommendation coordinated with the combined regional parent owner.

## Reproduction

Run from the repository root with the pinned Python requirements available:

```sh
python data/regional-review/regional-review-c06ee400da8c0bf6/reproduce.py
```

The script has no network dependency. It reads the exact baseline commit and checks the byte hashes of `data/world-index.json`, `data/hierarchy.json`, and the pinned regional handoffs before it resolves all 21 identities and parent IDs. It checks every retained source byte hash, exact native source shape ID, and required source-vintage role. For Gabon it calls shared `worldatlas-evidence-geometry-v1` WGS84 area helper code on source polygons and measures child overlap with the 2005 parent polygon. Invalid geometry is not silently repaired. The script writes only reproduction outputs inside the declared issue-owned directory: row findings, subject CSV, and five parent-province assessments CSV.

The government pages were recorded as external context with explicit retrieval limits. Reproduction validates the source and atlas identity/mechanical claims; it cannot independently recapture an unavailable government page, prove the government source's legal authority, or convert an area overlay/count into geographic truth.

## Sources and terms

- Gabon administrative roster: Ministry of Interior, [Découpage Administratif](https://www.interieur.gouv.ga/decoupage-administratif), posted 2018-01-06.
- Gabon territorial counts and legal reference: Ministry of Interior, [Découpage Territorial](https://interieur.gouv.ga/decoupage-territorial/), posted 2018-01-06, citing DGAT May 2016 and Law No. 14/96 of 15 April 1996.
- São Tomé and Príncipe current country administration: INE, [Sobre o País](https://ine.st/index.php/o-pais/sobre-o-pais), inspected 2026-10-05.
- Historical administrative and geographic context: INE, [RGPH 2012, Estrutura da População](https://www.ine.st/phocadownload/userupload/Documentos/Recenseamentos/2012/Relat%C3%B3rio%20tem%C3%A1ticos%20%20Recenseamento%20%202012/2_ESTRUTURA%20DA%20POPULA%C3%87%C3%83O%20Recenseamento%202012.pdf), p. 15.
- 2017 comparison for six district areas and Príncipe autonomous region: INE, [São Tomé e Príncipe em Números 2017](https://www.ine.st/phocadownload/userupload/Documentos/STPemNumeros/STPemNumeros%20%202017.pdf), p. 5.
- Original source vintages: geoBoundaries pinned commit `9469f09592ced973a3448cf66b6100b741b64c0d`; see `sources-manifest.json` for per-file attribution, exact bytes, hashes, license and retrieval timestamps.

No PDF or official web page bytes are included because their reuse terms were not identified. The lawful geoBoundaries originals remain unmodified. For ODbL assets, preserve attribution and review share-alike/database obligations before any onward redistribution.
