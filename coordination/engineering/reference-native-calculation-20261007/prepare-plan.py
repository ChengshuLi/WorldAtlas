"""Actual immutable whole-input inventory before calculation; no GIS values."""
import gzip
import hashlib
import json
import pathlib
import subprocess
import sys

HERE=pathlib.Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path.insert(0,str(HERE))
from reader import Inputs, gunzip, exact_commit
C='6a47b43025d963daf80915c6d219c75ebcc8cd91'
N='coordination/engineering/reference-source-custody-20261007/'
Q='coordination/engineering/eastern-two-gap-repair-20261007/'


def run():
    inputs=Inputs(C);custody=inputs.json(N+'input-plan.json')
    world=inputs.json(Q+'input-index.json')
    chosen=[a for a in world['aliases'] if a['group']=='complete-current-world']
    paths={N+'input-plan.json',N+'runtime-plan.json',N+'runtime.py',N+'custody.py',
           N+'original-reference-index.json',N+'run-one/report.json',N+'run-two/report.json',N+'reproducibility.json',Q+'input-index.json',
           Q+'run-one/proposed-part-29.json.gz',Q+'run-one/crosswalk.json.gz',Q+'run-one/report.json',Q+'verification/full-proposal-readback.json'}
    fragments=[x for x in custody['original_fragment_inputs'] if '/terrain-original.' in x['path'] or '/resolve-original.' in x['path']]
    paths.update(x['path'] for x in fragments)
    paths.update(x['path'] for x in custody['full_member_outputs'])
    paths.update(x['path'] for x in custody['literal_helpers'])
    paths.add(custody['transport_helper']['path'])
    paths.update(Q+x['ordinary']['path'] for x in chosen)
    refs=subprocess.check_output(['git','-C',str(ROOT),'ls-tree','-r','--name-only',C,'--','data/reference-attributes/'],text=True).splitlines()
    if len(refs)!=93:raise ValueError('All93 original reference files required')
    paths.update(refs)
    old_runtime=inputs.json(N+'runtime-plan.json')
    # Retained runtime inputs remain actual whole baselines, not a claim that
    # this future calculation has used the source-custody operator roster.
    frame_pins=old_runtime.get('frames',old_runtime.get('runtime_frames',[]))
    if not frame_pins:
        frame_pins=[{'path':N+'runtime/part-'+str(j).zfill(3)+'.bin.gz'} for j in range(4)]
    paths.update(x['path'] for x in frame_pins)
    descriptors=[]
    for p in sorted(paths):
        raw=inputs.read(p);d=dict(inputs.pins[p])
        if p.endswith('.gz'):
            # The actual bodies are fixed by complete Git identity. Bound their
            # complete decode before deriving the ordinary descriptor itself.
            import io
            with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream:
                decoded=stream.read(32*1024*1024+1)
                if len(decoded)>32*1024*1024 or stream.read(1):raise ValueError('Decoded ordinary cap')
            d.update(encoding='gzip',decoded_bytes=len(decoded),decoded_sha256=hashlib.sha256(decoded).hexdigest())
        descriptors.append(d)
    plan={'version':1,'stage':'calculation-input inventory only, no scientific execution',
          'actual_original_baseline':C,'subjects':['atlas:physical:CAN-103:QUE','atlas:physical:CAN-114:NFL'],
          'original_source_custody_merge':C,'source_descriptors':descriptors,
          'relevant_original_fragments':fragments,'complete_native_members':custody['full_member_outputs'],
          'original_reference_files':refs,'world_aliases':chosen,
          'ordinary_source_encoded_bytes':sum(d['bytes'] for d in descriptors),
          'current_phase_no_parent_climate_archive_read':True,
          'complete_phase_budget_not_yet_final':'new caller/runtime/operator closure, actual outputs/controls/reports still must be counted',
          'operating_reservation_bytes':1073741824,'complete_original_zip_relation_upstream_only':True}
    target=HERE/'input-plan.json';target.write_text(json.dumps(plan,ensure_ascii=False,separators=(',',':'))+'\n')
    print(json.dumps({'status':'PASS','actual_whole_inputs':len(descriptors),'encoded_bytes':plan['ordinary_source_encoded_bytes'],'path':str(target),'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'no_GIS_calculation':True}))

if __name__=='__main__':run()
