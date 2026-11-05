"""Derive a scoped divider solely from a captured selected source and rule observation."""
import hashlib,json
from shapely.geometry import LineString,Point,box
from shapely.ops import split

def need(v,msg):
 if not v:raise ValueError(msg)
def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()
def derive(snapshot,observation,current):
 need(current.get('schema')=='neon-current-boundary-selection-attestation-v1' and current.get('retrieved_at_utc'),'invalid current selection attestation');b=[x for x in snapshot['mainland_boundaries'] if x['boundary_id']==current['boundary_id']];c=[x for x in snapshot['routes'] if x['route_id']==current['route_id']];need(len(b)==len(c)==1,'source identity not unique');b=b[0];c=c[0];need(b['geometry_sha256']==digest(b['geometry'])==current['boundary_sha256']==observation['lineage']['selected_boundary_sha256'] and c['geometry_sha256']==digest(c['geometry'])==current['closure_sha256']==observation['lineage']['selected_closure_sha256'],'selected source geometry mismatch');cfg=observation['apply']['config'];bounds=cfg['bounds'];need(isinstance(bounds,list) and len(bounds)==4 and bounds[0]<bounds[2] and bounds[1]<bounds[3],'invalid scope');w,s,e,n=bounds;inside=lambda p:w<p[0]<e and s<p[1]<n;river=b['geometry']['coordinates'];closure=c['geometry']['coordinates'];need(river[-1]==closure[0],'boundary/closure do not join');hits=[i for i,p in enumerate(river) if inside(p)];need(hits and hits[0]>0 and all(inside(p) for p in river[hits[0]:]) and not inside(river[hits[0]-1]),'river does not enter scope once and remain');i=hits[0];need(i==1 or LineString(river[:i]).intersection(box(*bounds)).is_empty,'earlier source line intersects scope');exits=[j for j,p in enumerate(closure[1:],1) if not inside(p)];need(exits,'closure does not leave scope');j=exits[0];need(all(inside(p) for p in closure[:j]),'closure entry invalid');divider=river[i-1:]+closure[1:j+1];path=LineString(divider);need(path.is_simple and not path.is_empty,'derived divider invalid');pieces=split(box(*bounds),path);need(len(pieces.geoms)==2,'derived divider does not split scope');ew=Point(*cfg['europe_witness']);aw=Point(*cfg['asia_witness']);ep=[p for p in pieces.geoms if p.contains(ew)];ap=[p for p in pieces.geoms if p.contains(aw)];need(len(ep)==len(ap)==1 and not ep[0].equals(ap[0]),'invalid side witnesses');return divider,cfg


def authenticate_attestation(current, observation_sha256, project_id, branch_id):
    """Bind an independently authenticated Neon read to these exact local inputs.

    The caller must independently authenticate that the attestation is a fresh
    read of the intended project and branch. The file itself is not a signature.
    """
    if not project_id or not branch_id or current.get('project_id') != project_id or current.get('branch_id') != branch_id:
        raise ValueError('Neon project or branch mismatch')
    if current.get('observation_sha256') != observation_sha256:
        raise ValueError('Neon observation mismatch')


def category_codec(snapshot, report_categories):
    """Resolve semantic continent codes from the pinned selected registry."""
    entities = {x['id']:x['name'] for x in snapshot['entities'] if x.get('level') == 'continent'}
    bindings = [x for x in snapshot['category_bindings'] if x['physical_class']=='land']
    resolved = {str(x['code']):entities[x['entity_id']] for x in bindings}
    need(len(resolved)==len(bindings) and resolved==report_categories, 'selected land categories differ from candidate report')
    def code(name):
        matches=[int(k) for k,v in resolved.items() if v==name]
        need(len(matches)==1, 'continent category is not unique: '+name)
        return matches[0]
    return {'land_codes':sorted(map(int,resolved)), 'europe_code':code('Europe'), 'asia_code':code('Asia')}


def require_reference_categories(candidate_categories, reference_manifest):
    """Raw-code comparisons require the reference to use the same land codec."""
    cats = [x for x in reference_manifest['categories'] if x.get('physical_class')=='land']
    mapping = {str(x['id']):x['name'] for x in cats}
    need(len(mapping)==len(cats) and mapping==candidate_categories, 'reference and candidate land categories differ')
