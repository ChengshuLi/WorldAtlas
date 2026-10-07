"""Complete recorded-diagnostic aggregation; performs no new geometry operations."""
import argparse,collections,gzip,json,pathlib,sys
P=pathlib.Path(__file__).resolve().parent;R=P.parents[2];sys.path.insert(0,str(R/'scripts'))
from evidence.immutable import canonical_json as canon,deterministic_gzip
from reader import SHA

def summarize(run):
    report=json.loads((run/'report.json').read_bytes());families={};family_refs={};records=[];statuses=collections.Counter();matrix=collections.Counter();groups={};illustrations={}
    def rows(pin):
        b=(run/pin['path']).read_bytes();raw=gzip.decompress(b)
        if len(b)!=pin['bytes']or SHA(b)!=pin['sha256']or len(raw)!=pin['decoded_bytes']or SHA(raw)!=pin['decoded_sha256']:raise ValueError('Changed complete scientific aggregation input')
        data=json.loads(raw)
        if len(data)!=pin['records']:raise ValueError('Changed complete aggregation roster')
        return data
    for pin in report['family_outputs']:
        for index,f in enumerate(rows(pin)):
            fid=f['family']['id'];families[fid]=f;family_refs[fid]={'path':pin['path'],'index':index}
    for pin in report['component_outputs']:
        for index,r in enumerate(rows(pin)):
            statuses[r['status']]+=1
            if not r['status'].startswith('unknown-'):continue
            f=families[r['family']];source_ids=sorted({s['source_id']for s in f['family']['source_families']});products=sorted({s.split(':')[0]for s in source_ids});ix=r.get('intersection');diff=r.get('difference');area=r.get('area_arithmetic_delta')
            def area_kind(v):return 'unmeasured'if v is None else('zero'if v['planar_area_coordinate_units_squared']==0 else'positive'if v['planar_area_coordinate_units_squared']>0 else'negative')
            key=(r['status'],r['source_union_reference']['status'],area_kind(ix),area_kind(diff),'absent'if area is None else'zero'if area==0 else'positive'if area>0 else'negative')
            matrix[key]+=1;fid=r['family'];g=groups.setdefault(fid,{'family':fid,'component_ids':[],'source_ids':source_ids,'product_groups':products,'full_family_component_count':f['family']['component_count'],'counts':collections.Counter(),'record_reference':family_refs[fid]});g['component_ids'].append(r['component']);g['counts'][r['status']]+=1
            ref={'component':r['component'],'family':fid,'source_ids':source_ids,'status':r['status'],'source_union_status':r['source_union_reference']['status'],'intersection_area_kind':area_kind(ix),'difference_area_kind':area_kind(diff),'area_arithmetic_delta':area,'partition_equals_original':r.get('partition_equals_original'),'complete_row_reference':{'path':pin['path'],'index':index},'complete_component_geometry_sha256':r['component_geometry_sha256'],'intersection':ix,'difference':diff,'source_union_reference':r['source_union_reference']}
            records.append(ref)
            product='+'.join(products)
            if product not in illustrations or (diff and diff['planar_area_coordinate_units_squared']>illustrations[product]['difference']['planar_area_coordinate_units_squared']):illustrations[product]=ref
    if dict(statuses)!=report['counts']or sum(statuses.values())!=20032:raise ValueError('Complete recorded status aggregation mismatch')
    for g in groups.values():g['counts']=dict(g['counts']);g['component_ids'].sort()
    result={'version':1,'method':'aggregate-all-recorded-fields-no-new-geometric-inference','actual_producer_commit':report['code_commit'],'actual_report_sha256':SHA((run/'report.json').read_bytes()),'complete_components':sum(statuses.values()),'complete_families':len(families),'all_status_counts':dict(statuses),'unknown_components':len(records),'unknown_families':len(groups),'reason_matrix':[{'status':k[0],'source_union_status':k[1],'intersection_area_kind':k[2],'difference_area_kind':k[3],'area_arithmetic_delta_sign':k[4],'count':v}for k,v in sorted(matrix.items())],'complete_unknown_family_groups':sorted(groups.values(),key=lambda x:x['family']),'complete_unknown_records':sorted(records,key=lambda x:x['component']),'illustrative_recorded_geometry_references':list(illustrations.values()),'limits':['Every unknown remains unclassified; no invalid-source, numeric-overlay cause, water or owner inference.','Areas and arithmetic differences use stored planar coordinate units, not physical square metres.','Next engineering work must independently diagnose retained exact overlay/equality disagreements before any changed numeric policy or repair.']}
    return result

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--run',required=True);a.add_argument('--output',required=True);x=a.parse_args();v=summarize(pathlib.Path(x.run));raw=canon(v);p=pathlib.Path(x.output);p.write_bytes(deterministic_gzip(raw));print(json.dumps({k:v[k]for k in ['complete_components','unknown_components','unknown_families','reason_matrix']}))
