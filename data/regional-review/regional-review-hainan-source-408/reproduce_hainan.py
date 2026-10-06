#!/usr/bin/env python3
"""Reproduce issue #1053's frozen Hainan identity join and vintage edge screen."""
import csv, hashlib, json, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[3]
PACKET = pathlib.Path(__file__).resolve().parent
INPUT = ROOT / 'data/regional-review/regional-review-365cbd6478904888/source/geoBoundaries-CHN-ADM2.geojson'
ATLAS = ROOT / 'data/geography/part-4.json'
CROSSWALK = PACKET / 'findings/hainan-18-crosswalk.csv'
OUT = PACKET / 'findings/reproduction-summary.json'
POSITIVE = PACKET / 'findings/positive-edge-control.json'
NEGATIVE = PACKET / 'findings/negative-point-control.json'
EXPECTED_INPUT = '2b68d8a808742fc6d7acd769584db960d8fc2c25b9f1d20e3e98c72e9f1c4d34'
EXPECTED_ATLAS = 'e204a879e160f8b22ccfff698e8063a79d91cdba5ef7aa87df94661323b0bd3c'
IDS = '''gb:CHN:ADM2:17275852B2295538790743 gb:CHN:ADM2:17275852B38709981190197 gb:CHN:ADM2:17275852B38939963469829 gb:CHN:ADM2:17275852B41190306193582 gb:CHN:ADM2:17275852B42599245130625 gb:CHN:ADM2:17275852B50589627480209 gb:CHN:ADM2:17275852B53008264931106 gb:CHN:ADM2:17275852B70320302334749 gb:CHN:ADM2:17275852B72819681774342 gb:CHN:ADM2:17275852B7979903099841 gb:CHN:ADM2:17275852B80309702523612 gb:CHN:ADM2:17275852B82960244806798 gb:CHN:ADM2:17275852B85583949591367 gb:CHN:ADM2:17275852B86431238150342 gb:CHN:ADM2:17275852B87782309196497 gb:CHN:ADM2:17275852B88042861362346 gb:CHN:ADM2:17275852B93743910489906 gb:CHN:ADM2:17275852B98891327369808'''.split()
IDS = sorted(IDS)
# Current identity/tier values use Hainan Statistical Yearbook 2024, table 1-1 (2023).
# Status concerns administrative crosswalk only; all current boundaries remain unverified.
CURRENT = {
 '17275852B2295538790743': ('Haikou City','Prefecture-level city','Hainan Province','insufficient-evidence','The current city roster lists four city districts; a generic ADM2 county-level source role and present city-envelope fit need source geometry.'),
 '17275852B38709981190197': ('Tunchang County','County','Hainan Province','justified','Current name and county role match the official roster; atlas group purpose remains open.'),
 '17275852B38939963469829': ('Danzhou City','Prefecture-level city','Hainan Province','insufficient-evidence','Current roster classifies Danzhou as a prefecture-level city; generic county-level source role and polygon-to-city scope need primary GIS confirmation.'),
 '17275852B41190306193582': ('Wenchang City','County-level city directly administered by Hainan','Hainan Province','correction-needed','The target feature is assigned Atlas parent framework:province:sansha:0679d6128f7a although the current roster identifies Wenchang City. This is an explicit parent mismatch; request a separate engineering correction.'),
 '17275852B42599245130625': ('Wanning City','County-level city directly administered by Hainan','Hainan Province','justified','Current name and county-level city role match the official roster; atlas group/member purpose remains open.'),
 '17275852B50589627480209': ('Ledong Li Autonomous County','Autonomous county','Hainan Province','justified','Current name and autonomous-county role match the official roster; atlas group purpose remains open.'),
 '17275852B53008264931106': ('Qiongzhong Li and Miao Autonomous County','Autonomous county','Hainan Province','justified','Current identity and autonomous-county role match the official roster; atlas group purpose remains open.'),
 '17275852B70320302334749': ('Baisha Li Autonomous County','Autonomous county','Hainan Province','justified','Current name and autonomous-county role match the official roster; atlas group purpose remains open.'),
 '17275852B72819681774342': ('Lingshui Li Autonomous County','Autonomous county','Hainan Province','justified','Current roster short name is used; autonomous-county identity matches. Atlas group purpose remains open.'),
 '17275852B7979903099841': ('Chengmai County','County','Hainan Province','justified','Current name and county role match the official roster; atlas group purpose remains open.'),
 '17275852B80309702523612': ('Sanya City','Prefecture-level city','Hainan Province','insufficient-evidence','The current roster lists four city districts; generic ADM2 county-level source role and present city-envelope fit need source geometry.'),
 '17275852B82960244806798': ("Ding'an County",'County','Hainan Province','justified','Current name and county role match the official roster; atlas group purpose remains open.'),
 '17275852B85583949591367': ('Baoting Li and Miao Autonomous County','Autonomous county','Hainan Province','justified','Current name and autonomous-county role match the official roster; atlas group purpose remains open.'),
 '17275852B86431238150342': ('Qiongshan District (Haikou)','District of prefecture-level Haikou City','Haikou City','correction-needed','Qiongshan City is historical: the 2002 State Council adjustment abolished the city and established Haikou districts from its territory. Preserve the old identity and propose a record-preserving crosswalk separately.'),
 '17275852B87782309196497': ('Qionghai City','County-level city directly administered by Hainan','Hainan Province','justified','Current name and county-level city role match the official roster; atlas group purpose remains open.'),
 '17275852B88042861362346': ('Changjiang Li Autonomous County','Autonomous county','Hainan Province','justified','Current name and autonomous-county role match the official roster; atlas group purpose remains open.'),
 '17275852B93743910489906': ('Dongfang City','County-level city directly administered by Hainan','Hainan Province','correction-needed','The source name says Li autonomous county but the current roster lists Dongfang City; a current authoritative change record and territory crosswalk are needed.'),
 '17275852B98891327369808': ('Lingao County','County','Hainan Province','justified','Current name and county role match the official roster; atlas group purpose remains open.'),
}

def sha(b): return hashlib.sha256(b).hexdigest()
def edge(a,b): return tuple(sorted((tuple(a),tuple(b))))
def exact_shared_edges(records):
    owners={}
    for fid,rings in records:
        for ring in rings:
            for a,b in zip(ring,ring[1:]):
                if tuple(a)!=tuple(b): owners.setdefault(edge(a,b),set()).add(fid)
    pairs={}
    for e,ids in owners.items():
        ordered=sorted(ids)
        for i,left in enumerate(ordered):
            for right in ordered[i+1:]: pairs[(left,right)]=pairs.get((left,right),0)+1
    return pairs

# Positive/negative contact controls: a reversed full edge matches; a point touch does not.
positive=exact_shared_edges([('a',[[[0,0],[1,0]]]),('b',[[[1,0],[0,0]]])]) == {('a','b'):1}
negative=exact_shared_edges([('a',[[[0,0],[1,0]]]),('b',[[[1,0],[1,1]]])]) == {}
assert positive and negative
POSITIVE.write_text(json.dumps({'method_id':'exact-edge-screen','kind':'positive-control','outcome':'passed','case':'same full segment with reversed orientation','observed':positive},indent=2)+'\n',encoding='utf-8')
NEGATIVE.write_text(json.dumps({'method_id':'exact-edge-screen','kind':'negative-control','outcome':'passed','case':'boundaries meet at one endpoint only','observed':negative},indent=2)+'\n',encoding='utf-8')
raw=INPUT.read_bytes(); assert sha(raw)==EXPECTED_INPUT,'Pinned source bytes changed'
atlas_raw=ATLAS.read_bytes(); assert sha(atlas_raw)==EXPECTED_ATLAS,'Pinned Atlas feature bytes changed'
atlas=json.loads(atlas_raw)
atlas_by={f.get('id') or f.get('properties',{}).get('id'):f for f in atlas.get('features',[]) if (f.get('id') or f.get('properties',{}).get('id')) in IDS}
assert set(atlas_by)==set(IDS),'Frozen IDs missing in pinned Atlas part'
source=json.loads(raw); source_by={}
for feature in source.get('features',[]):
    native=feature.get('properties',{}).get('shapeID')
    if native in {x.rsplit(':',1)[1] for x in IDS}:
        assert native not in source_by,'Duplicate source ID'
        source_by[native]=feature
assert set(source_by)=={x.rsplit(':',1)[1] for x in IDS},'Frozen issue scope does not join exactly'
assert set(CURRENT)==set(x.rsplit(':',1)[1] for x in IDS),'Assessment mapping differs from issue scope'
records=[]; per_feature=[]; total_vertices=holes=0; csv_rows=[]
for fid in IDS:
    native=fid.rsplit(':',1)[1]; feature=source_by[native]; props=feature['properties']; geom=feature['geometry']
    assert geom and geom['type'] in ('Polygon','MultiPolygon')
    name,role,parent,status,finding=CURRENT[native]
    polys=[geom['coordinates']] if geom['type']=='Polygon' else geom['coordinates']
    rings=[ring for polygon in polys for ring in polygon]
    assert rings
    for ring in rings:
        assert len(ring)>=4 and ring[0]==ring[-1],f'Ring not closed: {fid}'
        for point in ring: assert len(point)>=2 and -180<=point[0]<=180 and -90<=point[1]<=90,f'Coordinate out of range: {fid}'
    vertices=sum(len(poly[0])-1 for poly in polys); interior=sum(len(poly)-1 for poly in polys)
    total_vertices+=vertices; holes+=interior
    records.append((fid,rings))
    per_feature.append({'id':fid,'source_name':props['shapeName'],'geometry_type':geom['type'],'polygon_components':len(polys),'exterior_vertices':vertices,'interior_rings':interior})
    atlas_feature=atlas_by[fid]; atlas_props=atlas_feature.get('properties',{})
    csv_rows.append({'location_id':fid,'source_name_2017':props['shapeName'],'source_role_claim':'ADM2; County Level (Atlas source metadata)','current_official_identity':name,'current_official_role':role,'current_official_government_parent':parent,'current_model_parent':atlas_props.get('parent_id',''),'assessment':status,'identity_tier_parent_finding':finding,'boundary_finding':'No current official GIS boundary bytes retrieved; pinned 2017 candidate only. Current line, island/fragment, coastal completeness and legal fit remain unresolved.','neighboring_granularity':'','source_vintage':'2017 reference (source metadata)','license_reuse':'Unknown upstream provenance/reuse terms; embedded repository source metadata claims ODbL/PDDL; no new source copy redistributed.','source_byte_sha256':EXPECTED_INPUT,'identity_evidence_source_ids':'hainan-yearbook-2024;geoboundaries-2017','boundary_source_status':'No current official GIS bytes retrieved; exact 2017 candidate geometry only'})
pairs=exact_shared_edges(records)
name_by={r['location_id']:r['source_name_2017'] for r in csv_rows}
for (left,right),count in sorted(pairs.items()):
    for row in csv_rows:
        if row['location_id'] in (left,right):
            neighbor=name_by[right if row['location_id']==left else left]
            row['neighboring_granularity']+=('; ' if row['neighboring_granularity'] else '')+neighbor+f' ({count} exact source edge segments; vintage clue only)'
for row in csv_rows:
    if not row['neighboring_granularity']: row['neighboring_granularity']='No exact full-edge contact detected among the 18 frozen features; absence is not evidence of no current neighbor.'
columns=list(csv_rows[0])
with CROSSWALK.open('w',newline='',encoding='utf-8') as f:
    writer=csv.DictWriter(f,fieldnames=columns,lineterminator='\n'); writer.writeheader(); writer.writerows(csv_rows)
pair_rows=[{'left_id':a,'right_id':b,'exact_shared_segments':n} for (a,b),n in sorted(pairs.items())]
result={'version':1,'issue':1053,'scope_ids':IDS,'input':{'path':str(INPUT.relative_to(ROOT)),'sha256':sha(raw),'vintage':'geoBoundaries gbOpen CHN ADM2 2017, repository-retained snapshot'},'crosswalk_rows':len(csv_rows),'unique_source_joins':len(source_by),'geometry_structure':{'features':len(per_feature),'polygon_components':sum(x['polygon_components'] for x in per_feature),'exterior_vertices':total_vertices,'interior_rings':holes,'all_exterior_rings_closed':True,'coordinate_range_checks_passed':True,'per_feature':per_feature},'exact_shared_edge_screen':{'method':'Exact equality of full adjacent coordinate pairs, orientation-insensitive; does not detect subdivided/near-coincident segments or assess validity/coverage.','neighbor_pairs_detected':len(pair_rows),'shared_segments':sum(x['exact_shared_segments'] for x in pair_rows),'pairs':pair_rows,'controls':{'reversed_full_edge_detected':True,'point_only_contact_not_counted':True}},'official_roster_reconciliation':{'current_units_listed_in_2023_official_yearbook':19,'scope_current_identity_candidates':17,'current_unit_absent_from_scope':'Wuzhishan City','historical_scope_member':'Qiongshan City, abolished/merged into Haikou in 2002; current Qiongshan is a Haikou district','other_current_unit_outside_scope':'Sansha City; not part of this frozen 18-ID subject set'},'limits':['Roster/identity evidence does not identify contemporary boundary coordinates.','No current official redistributable GIS source bytes were retrievable; the provincial statistics PDF returned HTTP 403, and the official map download service did not expose bytes during this review.','A single Polygon/no-interior-ring representation is a geometry-structure fact, not evidence that all islands, fragments, coast, or legally defined area are complete.','Exact-edge pairs describe the pinned 2017 source only; they do not validate neighboring boundary correctness, gaps, overlaps, or 2026 administrative adjacency.','No spatial area, distance, coastline, completeness, or legal topology measurement was performed.','Wenchang parent and Qiongshan historical identity require a separate sourced engineering migration; no shared geography was edited.']}
OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(f"scope={len(csv_rows)} joins={len(source_by)} components={sum(x['polygon_components'] for x in per_feature)} vertices={total_vertices} holes={holes} exact_neighbor_pairs={len(pair_rows)} exact_segments={sum(x['exact_shared_segments'] for x in pair_rows)}")
