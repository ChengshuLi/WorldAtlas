# Primary sources

Retrieved 2026-10-06 UTC unless otherwise stated. The source files retained in `source/` preserve the exact bytes used. Page captures are not represented as byte-hashed source documents; see the page URLs and concise supported claims below.

| ID | Primary source | Use and limits |
|---|---|---|
| `daf-geo-pf` | [GEO PF dataset record](https://www.data.gouv.fr/datasets/geographie-administrative-de-la-polynesie-francaise) | DAF producer; dataset purpose and three layer/resource descriptions; CC BY license; metadata says updated 2022-02-28. Not proof of survey currency after that date. |
| `daf-geo-pf-assets` | [DAF Section Cadastre-Topographie organization catalogue](https://www.data.gouv.fr/organizations/section-cadastre-topographie-de-la-polynesie-francaise/datasets) | Names the retained island, figurative group-division and commune-limit ZIP resources and download URLs. |
| `daf-topo-method` | [DAF topographic services and data documentation](https://www.service-public.pf/daf/cellule-topo_nosservices/) | DAF says BD Carto is dated, average map update cycle about a decade; high islands and atolls differ in representation; defines `LOC` for islands/administrative boundaries; DAF says BD Carto vector data is open data under local orders. These general methods do not establish the detailed acquisition vintage of every GEO PF feature. |
| `state-subdivision-decree` | [Decree 2005-1611, Article 1](https://www.legifrance.gouv.fr/jorf/id/JORFSCTA000000898677) | Statutory State subdivisions and their commune membership: 13/7/17/6/5 communes. It defines administrative membership via communes, not every uninhabited island coastline. |
| `state-subdivision-counts-2022` | [Decree 2022-1592, annex Tables I–II](https://www.legifrance.gouv.fr/loda/id/JORFTEXT000046768003/) | Current (2022 census) five subdivision roster/counts and commune table, including administrative grouping context. Census rosters are not a coastline data source. |
| `organic-statute` | [Organic Law 2004-192, Article 1](https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000038741644/2026-05-07) | Names the constituent island groups and adjacent maritime spaces. It does not define polygons. |
| `dpam-geography` | [French Polynesia DPAM geographic introduction](https://www.service-public.pf/dpam/presentation-de-la-dpam/) | Official service description places Windward and Leeward within Society and uses Tuamotu-Gambier as an archipelago term; distinguishes physical/sector description from the State's five administrative subdivisions. Not legal boundary geometry. |
| `planning-plans` | [DCA official planning plans](https://www.service-public.pf/dca/plansdamenagement/) | Planning records are grouped under Windward, Leeward, Tuamotu-Gambier, Marquesas etc. This supports planning use only. |

## Retained government source files

The three original source archives are from the DAF GEO PF catalog, license `Creative Commons Attribution` as shown on the dataset record. Attribution: **Section Cadastre-Topographie, Direction des affaires foncières, Polynésie française**, via data.gouv.fr; retain attribution and link the source/license in any reuse. The catalog does not state a CC license version. No attempt is made to apply one to third-party material outside these source records.

1. `loc-ile.zip`, [raw asset](https://static.data.gouv.fr/resources/geographie-administrative-de-la-polynesie-francaise/20220228-205614/loc-ile.zip): DAF island/atoll/bank extents, asset modified 2022-02-28. Feature-level `date_acq` ranges from blank or 1997–2020, with most `last_edite` values in January/February 2022. Contains 128 mapped objects and type, source/acquisition, date, archipelago and area attributes. It is not a statement that every emergent speck is an administrative member.
2. `loc-groupe-ile.zip`, [raw asset](https://static.data.gouv.fr/resources/geographie-administrative-de-la-polynesie-francaise/20220228-205413/loc-groupe-ile.zip): DAF figurative administrative/toponymic groups, asset modified 2022-02-28. The five target rows have `date_acq=2018-09-05`, `last_edite=2020-03-09`, and `type_group=DIVISION_ADMINISTRATIVE`. DAF layer text identifies a “division ou subdivision administrative”; catalog title explicitly calls this division *figurative*.
3. `loc-commune-associee.zip`, [raw asset](https://static.data.gouv.fr/resources/geographie-administrative-de-la-polynesie-francaise/20220228-205331/loc-commune-associee.zip): DAF commune/associated-commune limits and ID/code crosswalk, asset modified 2022-02-28. The `code_subdi`, `id_ile`, commune, associated commune and geographic-name attributes supply a crosswalk for mapped municipal island portions; they do not enumerate all uninhabited islands.

## Baseline pins

The immutable comparator is `0463152556158926681120155ec2e6fd7d0d8c7f` (`origin/main` when claimed). The retained `source/ne-admin1-pyffeatures.json` is an exact byte-for-byte copy of the parent packet extract, not a refreshed download. Exact original file hashes and bytes are in `evidence-quality.json`; the issue's contract supplied these three pins:

- `data/geography/part-28.json`: `2aab2f36aeeb651ee8e6cc656e9541ad14e2ced2ea8160e8700ad4dc950c379d`
- `data/hierarchy.json`: `568301690ef231a85856666b57876a5efe8d8c7c6e671a56d81307b2dc28b80b`
- `data/regional-review/regional-review-14a242c4cb0781a7/source/natural-earth/ne_10m_admin_1_scoped-admin-features.json`: `dd3f4a5683c713fd89c00b41748d89771f905ef236feaacb7887818085f3d96e`

The existing feature geometry and parents are not modified. The five current features are Natural Earth 1:10m generalized Admin1 fallback comparators; their exact extracted source objects remain in the preceding #405 packet. Counts and intersections here are review diagnostics only.
