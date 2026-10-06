# Southern Melanesia subject and child-contract validation

Retrieved 2026-10-06 via the GitHub REST API. This additive correction addresses two validation defects found after #919 merged: duplicate parent subjects could be reported as unique coverage, and duplicate saved child contracts could conceal an unverified child. It also binds this work item’s declared 25 subjects and owned path to its captured issue contract. The original #919 evidence, source files, results, IDs, and follow-up records remain untouched.

## Exact geographic workload

The current #454 issue contract, its retained original scope, and the immutable ancestor scope agree on 25 unique IDs: Fiji (15), New Caledonia (3), Vanuatu (6), and Solomon Islands / Temotu (1). Every ID maps to exactly one containing feature across the three pinned ancestor geography files. The original row-level reproduction has 25 unique rows matching that same roster. The corrected verifier rejects count/digest agreement when membership is duplicated or substituted; it binds the roster to the live issue contract and original ancestor bytes before writing output.

The four current child contracts are exactly #910–#913. Their unique subject subsets are Fiji (15), New Caledonia (3), Vanuatu (6), and Temotu (1); together they are disjoint and cover all 25 parent subjects. The archived #454 packet records each child as “blocked on parent” on 2026-10-05. The GitHub API snapshot retrieved 2026-10-06 records #454 closed and the four children open/ready. These are dated status observations, not conflicting scope contracts.

## Geographic evidence carried forward

This integrity correction rechecks original source bytes and each row’s source identity against the existing packet. It does not reacquire primary authorities or recompute legal boundaries. The packet’s detailed row evidence remains in the ancestor-linked original `reproduction.json`, `findings.md`, `sources.json`, and `source-acquisition.json`; the new output carries those 25 rows alongside independently rechecked containing-file identity.

| Subjects | Territorial role and neighboring granularity | Source vintage, license, and scope limits |
| --- | --- | --- |
| Fiji, 15 | Fourteen named provinces plus Rotuma; ADM1 Divisions are the coarser neighboring tier. Rotuma’s administrative status is different from the census reporting grouping. | Retained GeoBoundaries province layer is identified as 2007 census geography despite a 2020 catalog vintage; retained bytes do not match the source-registry hash. CC BY 4.0 is recorded for the retained GeoBoundaries release. Census labels do not establish current legal boundaries. The Fiji census report and Prime Minister page/PDF were restoration-only because redistribution terms were not established. |
| New Caledonia, 3 | Nord, Îles Loyauté, and Sud are provinces; Organic Law 99-209 supplies the legal province/commune membership context. | The official GeoReP layer metadata is dated 2024-10-28 and was retrieved 2026-10-05. Its item metadata declares [Licence Ouverte](https://alliance.numerique.gouv.fr/licence-ouverte-open-licence/). The three retained feature partitions preserve the original feature objects from a 45,177,077-byte response; each raw polygon is invalid. Natural Earth is only a generalized fallback. |
| Solomon Islands / Temotu, 1 | The source identifies Temotu as an ADM1 province; the province is not established as equivalent to the whole Santa Cruz Islands geographic-area parent. | Natural Earth 2021 generalized reference, public domain. The Ministry of Provincial Government confirms provincial role and broad geography; it does not establish exact boundary placement, island inclusion, or parent equivalence. |
| Vanuatu, 6 | Six province units at ADM1; OCHA/Pacific Community ADM2 area-council data (66 units in the inherited metadata) is finer neighboring granularity. | Retained 2017 OSM/Wambacher-derived layer is recorded under ODbL 1.0. Government profiles corroborate names and island groupings but not exact polygons. The cited OCHA layer metadata declares no license; no official exact province boundary source was established. |

The inherited geographic assessment has five correction-needed rows (Rotuma’s parent semantics, Lau’s source/hash disagreement, and three invalid New Caledonia polygons) and 20 insufficient-evidence rows. It provides source-name/ID matching and diagnostic geometry screens, not boundary approval. Exact offshore completeness, current legal edge authority, Temotu/Santa Cruz parent meaning, and repair semantics remain unresolved. Counts and topological checks are not evidence of geographic correctness.

## Reproduction and controls

Run twice from the repository root with Node 24:

```sh
node data/regional-review/melanesia-subject-validation-20261006/verify-packet.mjs data/regional-review/melanesia-subject-validation-20261006/run-one
node data/regional-review/melanesia-subject-validation-20261006/verify-packet.mjs data/regional-review/melanesia-subject-validation-20261006/run-two
```

Both full runs produced byte-identical `reproduction.json` (SHA-256 `7648ffcdc15a7c70b4c516356d4183b5e7c28196dddffaec4950414a93caf13a`), `negative-controls.json` (SHA-256 `38e41c1d0e88a85850aceff84a963ffd89bf9e1d1df75c8afecdd9c9dfbc8551`), and `positive-control.json` (SHA-256 `7cf8cfae646c942b2dd0ccaaca84fdd502ad2d79ef7fc4161f2d4d593c092dc7`). The retained run directories preserve both complete outputs. Eleven executed negative controls reject duplicate, missing, fabricated, count-mismatched, or digest-mismatched subjects; duplicate, missing, or unexpected child issues; wrong subsets; overlapping children; and incomplete child coverage. The verifier performs every scope, source-byte, feature-identity, and child-union check before it writes any output.

The manifest binds all changed files, ancestor source/scope inputs, exact subject-to-file mappings, result metrics, and the two-run receipt. This packet does not certify the Melanesia region, approve geography, authorize imports, or resolve any original source or legal-boundary uncertainty.
