# TGO result follow-up: BEN source families and Fiji failures

Read-only follow-up for frozen TGO result `80cf469d70a68b3ea475ff861d611f297cfcce56`. I located the original result JSON in the author’s local worktree at `/Users/chengshuli/world-atlas-workspace/.worldatlas-workspaces/8c86b01772c1c827/86bc7d6d53b859b8eed3e6a6a0848345b5c8f8d2eb7ecf4e99f672c8cf9b49fb/work/coordination/engineering/togo-original-repair-20261018-worker5/source-review/foreign-bounds-001/complete-foreign-bounds.json`. I verified its byte count and SHA-256 against the retained freeze readback. I also used the result’s actual family/input rows, TGO source catalogue and feature roster, BEN source-review packet, and retained source/periodic observations. I did not acquire sources or rerun a producer, query, geometry operation, or periodic check.

## BEN family scope and source-pin comparison

The frozen TGO result is bound by `result-freeze-readback.json` to 457,291 bytes and SHA-256 `d0ede54cec455302cf50dce6bd593ff1920cfedf289c1c4eba3c7842e2c81e7d`; its method and input are `721dac0bf4722ab2a7e0092746bbf3e17e9daa61` and `2404742bfcc2df26074ad4cc4a1b37a2a04e2c3d`, on corpus/canonical baseline `cddcde8786f038568137d915c8ee8436475f1688`. The retained result summary records complete `gb:BEN:ADM1` as 12 features (6 candidate, 6 disjoint) and `gb:BEN:ADM2` as 77 (11 candidate, 66 disjoint). This is the complete-family count scope: 17 bounds candidates across 89 whole family features. It does not mean the candidate geometries are clipped or that candidate status establishes a boundary relationship.

The retained TGO original-source catalogue identifies these family products at upstream geoBoundaries `9469f09` simplified-source URLs. Its raw family-product pins are:

| Family | TGO raw source SHA-256 | Bytes | Features | Represented-year claim | Recorded license |
|---|---|---:|---:|---|---|
| BEN ADM1 | `455c45033f206f9afdd0f051b1e71f2554738931d8e387a7ced574b239ec2da2` | 56,979 | 12 | 2012 | Public Domain |
| BEN ADM2 | `6a72cc64ed016badd2b80b8474b8c05a7da1132558973a4a93b460d446dff171` | 173,031 | 77 | 2007 | Public Domain |

The corresponding catalogue part-file hashes are `3478d3773100c9c693e6a93e7aee8f20493c1a754e7e2192886d220b9b466635` and `94bccd917f9ed654654ac1d5bb50d4e6d9a00a324f22235e842de7cbeec00fe0`; metadata-record hashes are `812a8d40d612bd68748189d2d10bd1dc158d89deeed9b60fcf7a3882e09d1131` and `11b26211971e446ea5d4e552ff7f51b88222c37548323c8841f967d994d468f7`.

The result’s two family `parts` rows and matching entries in its 374-entry `inputs` list name the same immutable paths, file sizes, SHA-256 hashes and Git blob OIDs as the earlier `ben-readiness/independent-original-and-retained-source-observations.json` `initial_families` records. Both are bound to actual result baseline `cddcde8786f038568137d915c8ee8436475f1688`. The executed input list also pins `coordination/engineering/original-geography-source-corpus-20261006/catalogue.json` at SHA-256 `d3da799558be1fcbe7f3ea90ba7033d312a65690984983cb008f2d72e32765f9`, matching the retained catalogue file byte-for-byte. In particular, the result family original decoded SHA/count/bytes exactly equal each catalogue product original SHA/count/bytes; both compressed part hashes also match. The prior BEN packet’s separate upstream asset pins are different because they refer to the non-simplified GeoJSON resources: ADM1 GeoJSON `f0c544f26a8d7625004123936269b1953cca4a6ef94ee9e716037a4667d073ca` and metadata `0e9362096220907717a21131a709ff128703937fb5f9115e17a4b90bd51872a0`; ADM2 GeoJSON `4489b38747709783884dbc0cbdd12df3874921a7f8a00737c155e4a8b899daec` and metadata `d91ee2c5dbab65623cb5459e133cfd923d20508349c81e8410b2b8ab8791ddc7`. They are distinct source files and not the TGO simplified-product bytes; I do not treat those hashes as the executed family pins. The exact TGO pins match the retained original-source records, which records the same source URLs, represented-year claims and recorded licenses.

I independently joined every BEN candidate row to its corresponding source-feature-roster row. For all 17 rows, family, source ID, one-based index, ordinal and owners match; the 11 ADM2 candidate IDs also all occur in the prior 77-subject BEN source assessment. The six ADM1 rows are ownerless and outside that BEN ADM2 subject assessment, as expected for the 12-feature comparison family. The result itself supplies each candidate’s whole-geometry hash, whole-part bounds and TGO target associations; those are conservative source-relative bounds contacts. This confirms output identity/accounting, not polygon intersection, feature correctness, or legal boundary meaning.

The exact retained candidate subjects are:

| Family | Source index / ordinal | Source ID | Owners |
|---|---:|---|---|
| BEN ADM1 | 2217 / 2 | `gb:BEN:ADM1:11314189B98234112011604` | none |
| BEN ADM1 | 2218 / 3 | `gb:BEN:ADM1:11314189B13023113934095` | none |
| BEN ADM1 | 2219 / 4 | `gb:BEN:ADM1:11314189B64147716128567` | none |
| BEN ADM1 | 2221 / 6 | `gb:BEN:ADM1:11314189B15837635829289` | none |
| BEN ADM1 | 2223 / 8 | `gb:BEN:ADM1:11314189B98727282609866` | none |
| BEN ADM1 | 2226 / 11 | `gb:BEN:ADM1:11314189B32238589455429` | none |
| BEN ADM2 | 2236 / 9 | `gb:BEN:ADM2:17685819B24804117588339` | 9157 |
| BEN ADM2 | 2240 / 13 | `gb:BEN:ADM2:17685819B31481778008604` | 9164 |
| BEN ADM2 | 2241 / 14 | `gb:BEN:ADM2:17685819B94511677610410` | 9217 |
| BEN ADM2 | 2246 / 19 | `gb:BEN:ADM2:17685819B99804537894120` | 9221 |
| BEN ADM2 | 2247 / 20 | `gb:BEN:ADM2:17685819B4092451643280` | 9173 |
| BEN ADM2 | 2249 / 22 | `gb:BEN:ADM2:17685819B95850649576266` | 9218 |
| BEN ADM2 | 2255 / 28 | `gb:BEN:ADM2:17685819B67930032483199` | 9200 |
| BEN ADM2 | 2259 / 32 | `gb:BEN:ADM2:17685819B53348586225757` | 9183 |
| BEN ADM2 | 2274 / 47 | `gb:BEN:ADM2:17685819B25851007312804` | 9158 |
| BEN ADM2 | 2284 / 57 | `gb:BEN:ADM2:17685819B6734193751411` | 9199 |
| BEN ADM2 | 2301 / 74 | `gb:BEN:ADM2:17685819B2600041724770` | 9160 |

For source role and vintage, the retained BEN packet describes BEN ADM2 as 2007 Map Maker Ltd./Stanford communes, with Stanford item `stanford-rq343zx0554`, and records Public Domain in geoBoundaries metadata; its role is supported by the retained Stanford/UT Austin item and INStaD 2011 context, not inferred from ADM2. The packet describes BEN ADM1 as 2012 departments, used as a later comparison/reference layer rather than a same-vintage commune authority. It reports its metadata source as geoBoundaries and Wikimedia Commons. The retained native BEN ADM1 meta likewise says `Boundary Representative of Year: 2012`, `Boundary Type: ADM1`, canonical type `Departments`, sources geoBoundaries/Wikimedia Commons, license `Public Domain`, and points to the Wikimedia file. The retained PRJ declares geographic WGS 1984 in degrees; XML processing lineage shows 2022 feature-class creation/export and does not change the stated 2012 represented vintage. The archived Commons image is consistent with a public-domain declaration for the displayed map. These records support preservation of the recorded terms, roles, vintage, attribution/provenance and declared CRS; they do not independently establish dataset-specific permission for the TGO corpus bytes, current legal boundaries, or any blanket rights conclusion. The TGO result itself is a historical inclusive-bounds screen only.

## Fiji unsupported records and guard

The TGO result summary and retained global roster agree on the following literal records:

| Subject | One-based source index | Ordinal | Owners | Raw result reason | Geometry SHA-256 |
|---|---:|---:|---|---|---|
| `gb:FJI:ADM1:53030831B91072554514863` | 33012 | 0 | none | `Invalid/nonfinite coordinate` | `b2a64c08388d0578bdfb597cadc36943f62df252302805dd99c78423239a0a20` |
| `gb:FJI:ADM2:14151628B95966095088914` | 33024 | 8 | 19904 | `Invalid/nonfinite coordinate` | `c4a1fe7200429f88423bee1b6815e8c1712ae3a1ac1069f0e9aa16b8151db31c` |
| `gb:FJI:ADM2:14151628B42533076410957` | 33028 | 12 | 19894 | `Invalid/nonfinite coordinate` | `43a5f0054991e614aede52923a6f81ae95ab2f5756922015dc01f8bfac31ca83` |

The method body retained with the actual run calls the existing `coordinateBounds` function on the complete raw feature geometry. Its `catch` path records the subject, source index, ordinal, owner list, thrown reason and whole-geometry hash in `unsupported`/`failures`, then continues; it does not convert an invalid frame into a disjoint result or repair coordinates. The raw coordinate tuples themselves are not retained in the summary, and this review did not inspect or normalize them. The exact failure classification and hashes are preserved as the actual result reported them.

The earlier retained periodic-observation file lists these same three source IDs and matching raw-geometry hashes, along with its own exact prior proof result/method pins. That is only an identity observation here. I do not assert that proof applies to TGO: no fresh check of the complete TGO target/interval enclosure or proof-to-current-scope binding was performed, and the TGO result still reports three unresolved unsupported features. No periodic proof, periodic execution, or negative-scope completion is claimed.

## Limits

This note accepts neither source fitness nor legal-boundary conclusions. It does not pre-clear processing, licensing, publication or reuse. The supported conclusion is limited to the TGO frozen result's recorded BEN family totals and raw Fiji failure identities/guard behavior, with the source-body distinction and rights, attribution, role and vintage limits above. No files outside this note were changed.
