#!/usr/bin/env python3
"""Fetch SALB COD attributes without geometry for bounded name/parent crosswalk.

SALB terms limit use to non-commercial, require attribution, and prohibit geometry
or content edits without contributor consent. This script does not request geometry.
"""
import datetime, hashlib, json, pathlib, re, unicodedata, urllib.request

PACKET=pathlib.Path(__file__).resolve().parent
scope=json.loads((PACKET/"issue-scope-pinned.json").read_text())
ids=set(scope["member_location_ids"])
atlas={}
for path in sorted((PACKET.parents[2]/"data/geography").glob("part-*.json")):
    for feature in json.loads(path.read_text())["features"]:
        if feature["id"] in ids: atlas[feature["id"]]=feature
base="https://geoservices.un.org/arcgis/rest/services/Hosted/SALB_COD/FeatureServer"
layer_url=base+"/5?f=pjson"
query_url=base+"/5/query?where=1%3D1&outFields=*&returnGeometry=false&f=json"
def get(url):
    request=urllib.request.Request(url,headers={"User-Agent":"WorldAtlas geography research/1.0"})
    with urllib.request.urlopen(request,timeout=60) as response: return response.read(),response.status
layer_bytes,layer_status=get(layer_url)
query_bytes,query_status=get(query_url)
layer=json.loads(layer_bytes); query=json.loads(query_bytes)
rows=[row["attributes"] for row in query["features"]]
def normalized(value):
    value=unicodedata.normalize("NFKD",value or "").encode("ascii","ignore").decode().lower()
    return re.sub(r"[^a-z0-9]","",value)
def base_unit_name(value):
    value=re.sub(r"\s*\(city\)\s*$","",value or "",flags=re.I)
    return normalized(value)
def source_name_key(value):
    name=base_unit_name(value)
    return {"moanda":"muanda"}.get(name,name)
selected=[]
for location_id in sorted(i for i in ids if i.startswith("gb:COD:")):
    feature=atlas[location_id]; properties=feature["properties"]
    baseline_name=properties["name"]
    parent=properties["parent_id"].split(":")[2]
    hits=[row for row in rows if source_name_key(row.get("adm2nm"))==source_name_key(baseline_name)
          and normalized(row.get("adm1nm"))==normalized(parent)]
    candidates=[]
    for row in hits:
        official_name=row.get("adm2nm") or ""
        candidates.append({"adm2nm":official_name,"adm2cd":row.get("adm2cd"),"adm1nm":row.get("adm1nm"),"adm1cd":row.get("adm1cd"),
                           "label_type":"city-labeled" if re.search(r"\(city\)\s*$",official_name,re.I) else "unmarked"})
    status=("unique named and parent candidate; source uses explicit city label" if len(candidates)==1 and candidates[0]["label_type"]=="city-labeled"
            else "unique normalized name and parent candidate" if len(candidates)==1
            else "multiple current units with same parent; city/territory code unresolved" if len(candidates)>1
            else "no candidate under current Atlas parent")
    selected.append({"location_id":location_id,"baseline_name":baseline_name,"atlas_parent_slug":parent,"salb_candidates":candidates,
                     "match_status":status,"name_rule":"NFKD accent/punctuation normalization; terminal '(City)' ignored for candidate discovery; explicit one-off alias Moanda→Muanda."})
terms_url="https://salb.un.org/sites/default/files/wysiwyg_uploads/docs_uploads/TermsOfUseSALB2021.pdf"
terms_bytes,terms_status=get(terms_url)
output={"drc_salb_2018_2024":{"version":1,"retrieved_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
 "source":"SALB Data, United Nations; validated by Institut Géographique du Congo (IGC)","source_page":"https://salb.un.org/en/data/cod",
 "page_temporal_validity":"2018-05-30 through latest update 2024-06-13","service_layer":layer.get("name"),"service_layer_url":layer_url,
 "service_layer_http_status":layer_status,"service_layer_response_bytes":len(layer_bytes),"service_layer_response_sha256":hashlib.sha256(layer_bytes).hexdigest(),
 "query_url":query_url,"query_http_status":query_status,"query_response_bytes":len(query_bytes),"query_response_sha256":hashlib.sha256(query_bytes).hexdigest(),
 "feature_count":len(rows),"returned_geometry":False,"scope_subject_count":len(selected),
 "unique_candidate_count":sum(len(r["salb_candidates"])==1 for r in selected),"multiple_candidate_count":sum(len(r["salb_candidates"])>1 for r in selected),
 "no_candidate_count":sum(len(r["salb_candidates"])==0 for r in selected),"selected_subjects":selected,
 "terms_of_use":{"url":terms_url,"http_status":terms_status,"response_bytes":len(terms_bytes),"response_sha256":hashlib.sha256(terms_bytes).hexdigest(),
  "restrictions":"Non-commercial use only; copyright retained by UN; no geometry/content changes without contributor consent; derived products credit United Nations and named contributor."},
 "method":"Name and Atlas parent string candidate screen only. The 2019 OCHA source has no matching SALB code; no source ID, geometries, or boundaries were compared. Moanda/Muanda is ambiguous between two same-parent current units.",
 "limits":"SALB geometry was not requested or retained. This non-commercial comparator is not a source for live production geometry or a completeness certificate."}}
(PACKET/"current-crosswalks.json").write_text(json.dumps(output,ensure_ascii=False,indent=2)+"\n")
summary=output["drc_salb_2018_2024"]
print(json.dumps({k:summary[k] for k in ["retrieved_utc","feature_count","unique_candidate_count","multiple_candidate_count","no_candidate_count","query_response_sha256"]}))
