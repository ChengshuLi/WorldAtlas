#!/usr/bin/env python3
"""Verify the pinned OSM delta graph; this does not select a boundary."""
import argparse, hashlib, json, xml.etree.ElementTree as ET
from pathlib import Path


def sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for block in iter(lambda:f.read(1048576),b''):h.update(block)
    return h.hexdigest()


def one(root, tag, identifier):
    matches=[e for e in root.findall(tag) if e.get('id')==identifier]
    if len(matches)!=1: raise ValueError(f'expected one {tag} {identifier}')
    return matches[0]


def topology(river,coast):
    relation=one(river,'relation','214415')
    if relation.get('version')!='122': raise ValueError('unexpected relation version')
    expected_roles={'22492011':'main_stream','977035398':'main_stream',
                    '22492112':'side_stream','22492166':'side_stream'}
    members=[(m.get('ref'),m.get('role')) for m in relation.findall('member') if m.get('type')=='way']
    for way,role in expected_roles.items():
        if [r for w,r in members if w==way]!=[role]: raise ValueError('unexpected relation role '+way)
    def way(identifier,version):
        w=one(river,'way',identifier)
        if w.get('version')!=version: raise ValueError('unexpected way version '+identifier)
        ids=[n.get('ref') for n in w.findall('nd')]
        if len(ids)<2 or len(ids)!=len(set(ids)): raise ValueError('invalid way nodes '+identifier)
        return ids,{t.get('k'):t.get('v') for t in w.findall('tag')}
    main,main_tags=way('22492011','74');canal,canal_tags=way('977035398','4')
    side,_=way('22492112','20');rejoin,_=way('22492166','10')
    if main_tags.get('waterway')!='river' or canal_tags.get('waterway')!='canal': raise ValueError('unexpected waterway tags')
    if (side[0],side[-1],rejoin[0],rejoin[-1])!=('241461340','241461940','241461940','241462578'):
        raise ValueError('unexpected side-branch topology')
    if main.count(side[0])!=1 or main.count(rejoin[-1])!=1 or main.index(side[0])>=main.index(rejoin[-1]):
        raise ValueError('side branch does not leave and rejoin ordered main way')
    if main[-1]!=canal[0] or canal[0]!='7986845886' or canal[-1]!='241464871': raise ValueError('unexpected canal junction')
    coast_way=one(coast,'way','825215510');coast_tags={t.get('k'):t.get('v') for t in coast_way.findall('tag')}
    if coast_way.get('version')!='8' or coast_tags.get('natural')!='coastline' or canal[-1] not in [n.get('ref') for n in coast_way.findall('nd')]:
        raise ValueError('coastline does not contain the canal terminal')
    current_canal=one(coast,'way','977035398')
    if current_canal.get('version')!='4' or [n.get('ref') for n in current_canal.findall('nd')]!=canal:
        raise ValueError('coastal response canal does not match pinned river')
    return {'relation_id':'214415','relation_version':'122','main_way':'22492011',
            'side_ways':['22492112','22492166'],'branch_node':side[0],'rejoin_node':rejoin[-1],
            'canal_way':'977035398','canal_start_node':canal[0], 'coastal_node':canal[-1],
            'coastline_way':'825215510','source_topology_status':'verified'}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('river');p.add_argument('river_sha256');p.add_argument('coast');p.add_argument('coast_sha256');p.add_argument('output',type=Path);a=p.parse_args()
    paths=[a.river,a.coast];pins=[a.river_sha256,a.coast_sha256]
    if [sha(p) for p in paths]!=pins:raise ValueError('source hash mismatch')
    result=topology(ET.parse(a.river).getroot(),ET.parse(a.coast).getroot())
    if [sha(p) for p in paths]!=pins:raise ValueError('source changed')
    result.update({'schema':'ural-delta-osm-topology-audit-v1','status':'research-not-selected','input_sha256':pins,'code_sha256':sha(__file__),
                   'limitations':['Topology alone does not prove naming, flow proportion, hydrographic correctness or continental boundary convention.',
                                  'Coastline agreement with OSM does not prove agreement with the atlas physical grid.',
                                  'Coastal way capture is a point-in-time research source and must be refreshed for a new selection.']})
    with a.output.open('x') as f:json.dump(result,f,sort_keys=True,indent=2);f.write('\n')
    print(json.dumps(result,sort_keys=True))


if __name__=='__main__':main()
