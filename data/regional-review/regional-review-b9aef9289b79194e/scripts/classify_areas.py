#!/usr/bin/env python3
"""Document each exact area purpose and whether the area's scoped membership is supported."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
scope = json.loads((ROOT / "source/issue-scope.json").read_text())
register = json.loads((ROOT / "findings/source-register.json").read_text())
citations = {row["evidence_id"] for row in register["external_primary_references_not_redistributed"]}
area_results = [
    {
        "id": "framework:area:botswana:9fa5183b68db", "name": "Botswana", "count": 35,
        "purpose": "Country geography. This batch has 22 direct 2015 RCMRD subdistrict/census-like source polygons plus 13 portions derived by intersecting a whole administrative feature with a RESOLVE ecoregion.",
        "assessment": "correction-needed", "source_ids": ["gb:BWA:ADM2", "resolve:47", "resolve:64", "resolve:65", "resolve:73", "resolve:76", "resolve:97"],
        "evidence_ids": ["GB-BWA-2015", "RESOLVE-SCOPED-ECOREGIONS", "BWA-STATSBOTS-2022"],
        "findings": ["Do not count ecological clips as separate administrative subdistricts.", "Statistics Botswana's current 28 census districts include city/town districts and subdivisions of administrative districts; its table explicitly separates census district from Sub-District/Admin Authority."],
    },
    {
        "id": "framework:area:caprivi-strip:8fac8f1da5fe", "name": "Caprivi Strip", "count": 7,
        "purpose": "A historical/geographic scope label anchored to 2007 Namibia records and a current parent named Caprivi; the 2013 legal region was renamed Zambezi and the same proclamation revised constituencies.",
        "assessment": "correction-needed", "source_ids": ["gb:NAM:ADM2"],
        "evidence_ids": ["GB-NAM-2007", "NAM-GAZETTE-2013", "NAM-NSA-2023", "NAM-ARANDIS-ERONGO"],
        "findings": ["Keep the seven IDs and historical relationship; the regional integration must decide whether this area is explicitly historical or represents current Zambezi.", "Arandis is in the current Erongo region according to Namibia government-hosted source material, but Atlas assigns it to Caprivi; its scoped polygon bounds are far from the official Arandis locality coordinates."],
    },
    {
        "id": "framework:area:eastern-cape:44b2e48813ae", "name": "Eastern Cape", "count": 17, "original_full_area_location_count": 33, "partial": True,
        "purpose": "Partial country-specific review of 17 local-municipality features; the sibling #436 source work owns 196 other South African municipality features.",
        "assessment": "correction-needed", "source_ids": ["gb:ZAF:ADM3"],
        "evidence_ids": ["GB-ZAF-2020", "SA-STATSSA-2022", "SA-MDB"],
        "findings": ["The 17 and #436's 196 sets are disjoint and exhaust the 213 features in the pinned geoBoundaries ZAF ADM3 file; this proves package coverage only, not legal boundary completeness.", "Seven included locations have parent Cacadu; Stats SA documents its 2018 rename to Sarah Baartman. Current MDB products post-date this 2020 source."],
    },
    {
        "id": "framework:area:lesotho:fe1db759afaf", "name": "Lesotho", "count": 10,
        "purpose": "Country geography with ten named first-order administrative districts.",
        "assessment": "correction-needed", "source_ids": ["gb:LSO:ADM1"],
        "evidence_ids": ["GB-LSO-2017", "LSO-GOV-2022"],
        "findings": ["A Government of Lesotho report confirms ten districts and the next two levels (80 constituencies, 124 community councils).", "All ten Atlas locations duplicate the exact district name of their immediate parent group; the tier chain repeats a district at adjacent levels. Geometry remains based on OSM/Wambacher 2017 rather than official district boundary data."],
    },
    {
        "id": "framework:area:namibia:db50c43eb62d", "name": "Namibia", "count": 104,
        "purpose": "Country geography, distinct from the seven-member Caprivi historical area; current base source is a 2007 release later affected by 2013 legal restructuring.",
        "assessment": "correction-needed", "source_ids": ["gb:NAM:ADM2", "resolve:94", "resolve:103", "resolve:104"],
        "evidence_ids": ["GB-NAM-2007", "RESOLVE-SCOPED-ECOREGIONS", "NAM-GAZETTE-2013", "NAM-NSA-2023"],
        "findings": ["Fifteen direct Atlas geometries have IoU below 0.95 against their exact pinned 2007 source features; four Atlas geometries are invalid before any repair used for area measurements.", "Six location names exactly duplicate their immediate parent group, including constituency-like features.", "Three additional Atlas subjects are ecological clips of old administrative source features, not new districts/constituencies."],
    },
    {
        "id": "framework:area:swaziland:02c2e32eff24", "name": "Eswatini", "count": 53,
        "purpose": "Country geography whose 2017 ODbL geometry was labelled Inkhundla; government identifies these as local governance/development units within four regions.",
        "assessment": "correction-needed", "source_ids": ["gb:SWZ:ADM2"],
        "evidence_ids": ["GB-SWZ-2017", "SWZ-CURRENT-COUNT-59", "SWZ-CURRENT-COUNT-55", "SWZ-EBC-2017-MAP"],
        "findings": ["Two current Government of Eswatini pages disagree: one states 59 centres (15/18/15/11), while another states 55 (14/16/11/14); the pinned OSM/Wambacher roster has 53.", "Ten Atlas polygons have IoU below 0.95 against the pinned 2017 polygons and six are invalid before the comparison repair.", "The 2017 official EBC map is copyright-marked and has no open redistribution license; do not trace or redistribute its boundaries without a lawful source/permission."],
    },
]
out = ROOT / "findings/area-assessments.jsonl"
out.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in area_results))
print(json.dumps({"areas":len(area_results),"counts":[(r["name"],r["count"],r["assessment"]) for r in area_results]},ensure_ascii=False,indent=2))
