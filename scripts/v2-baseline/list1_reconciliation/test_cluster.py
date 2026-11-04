import hashlib
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

import numpy as np
import cluster
import match_old_list1


def pin(path):
    return {'path': str(path), 'sha256': cluster.digest(path)}


def write_rle(path, values):
    path.mkdir()
    offsets = [0]
    pairs = []
    for row in values:
        for i in range(1, len(row) + 1):
            if i == len(row) or row[i] != row[i - 1]:
                pairs.append((i, row[i - 1]))
        offsets.append(len(pairs))
    np.array(offsets, dtype='<u4').tofile(path / 'rows')
    np.array(pairs, dtype='<u4').tofile(path / 'runs')
    return pin(path / 'rows'), pin(path / 'runs')


def reports(directory, cfg):
    categories=[{'id':i,'name':f'category-{i}','physical_class':'water' if i==1 else 'land'} for i in (1,17,18,19,20)]
    snapshot=directory/'snapshot.json'
    snapshot.write_text(json.dumps({'schema':'worldatlas-geography-decision-draft-evidence-v1','source':'neon-export','decision_revision':{'id':'d','status':'draft','entity_revision':'e'},'entity_revision':{'id':'e','status':'draft'},'category_bindings':[{'code':x['id'],'entity_id':x['id'],'physical_class':x['physical_class']} for x in categories],'entities':[{'id':x['id'],'name':x['name']} for x in categories]}))
    manifest=directory/'reference.json'
    manifest.write_text(json.dumps({'west':-180,'north':90,'step':cfg['grid']['step'],'categories':categories,'versions':{'v7':{'width':cfg['grid']['width'],'height':cfg['grid']['height'],'local_grid':{'rows_sha256':cfg['reference_rows']['sha256'],'runs_sha256':cfg['reference_runs']['sha256']}}}}))
    physical = directory / 'physical-report.json'
    physical.write_text(json.dumps({'status':'candidate-only','grid':cfg['grid'],'output_sha256':{'rows.u32le':cfg['physical_rows']['sha256'],'runs.u32le':cfg['physical_runs']['sha256']}}))
    candidate = directory / 'candidate-report.json'
    candidate.write_text(json.dumps({'schema':'simple-v2-land-report-v1','status':'research-not-published','grid':cfg['grid'], 'output_rows_sha256':cfg['candidate_rows']['sha256'], 'output_runs_sha256':cfg['candidate_runs']['sha256'], 'decision_snapshot_sha256':pin(snapshot)['sha256'], 'inputs':{'physical_rows':cfg['physical_rows'], 'physical_runs':cfg['physical_runs'], 'physical_report':pin(physical)}}))
    audit = directory / 'reference-audit.json'
    audit.write_text(json.dumps({'schema':'worldatlas-v7-full-grid-composition-audit-v1','status':'staged-not-published', 'grid':{'width':cfg['grid']['width'],'height':cfg['grid']['height'],'angular_step_deg':cfg['grid']['step']},'output':{'rows_sha256':cfg['reference_rows']['sha256'],'runs_sha256':cfg['reference_runs']['sha256']}}))
    cfg['provenance']={'candidate_report':pin(candidate),'physical_report':pin(physical),'reference_audit':pin(audit),'decision_snapshot':pin(snapshot),'reference_manifest':pin(manifest)}
    cfg['minimum_free_bytes']=0


class ClustersTest(unittest.TestCase):
    def setup_case(self, tmp):
        # Edge/corner adjacency wraps; isolated second cluster; different land/water
        # classifications are excluded. Width is global and height within 180 deg.
        candidate = [[18,17,17,17,17,17,17,19], [17,17,17,17,17,17,18,17], [17,17,20,17,17,17,17,17], [0,17,17,17,17,17,17,18]]
        reference = [[17,17,17,17,17,17,17,17], [17,17,17,17,17,17,17,17], [17,17,17,17,17,17,17,17], [17,1,17,17,17,17,17,17]]
        physical = [[17] * 8, [17] * 8, [17] * 8, [1,17,17,17,17,17,17,17]]
        cr, cu = write_rle(tmp / 'candidate', candidate)
        rr, ru = write_rle(tmp / 'reference', reference)
        pr, pu = write_rle(tmp / 'physical', physical)
        provenance = tmp / 'source'; provenance.mkdir(); (provenance / 'report').write_text('baseline and policy')
        cfg = {'schema':'list1-land-clusters-config-v1','grid':{'width':8,'height':4,'step':45,'west':-180,'north':90}, 'candidate_rows':cr,'candidate_runs':cu,'reference_rows':rr,'reference_runs':ru,'physical_rows':pr,'physical_runs':pu,'provenance':{'baseline_report':pin(provenance/'report')}}
        config = tmp / 'config'; config.mkdir(); reports(config, cfg); (config / 'config.json').write_text(json.dumps(cfg))
        return config / 'config.json'

    def test_exact_connectivity_physical_and_discovery(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); config = self.setup_case(root)
            report = cluster.build(config, root / 'out ?#')
            self.assertEqual(report['counts']['mismatch'], 5)
            self.assertEqual(report['counts']['candidate_land_reference_water'], 1)
            self.assertEqual(report['counts']['candidate_water_reference_land'], 1)
            self.assertEqual(report['clusters'], 3)
            db = sqlite3.connect(root / 'out ?#/clusters.sqlite')
            self.assertEqual(sorted(row[0] for row in db.execute('SELECT cells FROM clusters')), [1,1,3])
            self.assertEqual(sum(b-a for a,b in db.execute('SELECT start,end FROM resolved')), 5)
            self.assertEqual(cluster.digest(root / 'out ?#/clusters.sqlite'), report['database_sha256'])
            db.close()
            index_dir = root / 'index'; index_dir.mkdir()
            index_path = index_dir / 'old.json'
            index_path.write_text(json.dumps({'schema':'old-list1-evidence-discovery-index-v1','grid':{'width':8,'height':4,'step':'45','west':'-180','north':'90'},'items':[{'old_item_id':'wrap','historical_changed_land_extent':{'x_start':7,'x_end':0,'y_start':0,'y_end':0}}, {'old_item_id':'none','historical_changed_land_extent':{'x_start':4,'x_end':4,'y_start':3,'y_end':3}}]}))
            match_old_list1.match(root / 'out ?#', index_path, cluster.digest(index_path), root / 'matches')
            lines = [json.loads(x) for x in (root / 'matches/matches.jsonl').read_text().splitlines()]
            self.assertEqual(len(lines), 3)
            hits = [x for x in lines if x['old_list1_candidates']]
            self.assertEqual(len(hits), 1)
            self.assertEqual(hits[0]['old_list1_candidates'][0]['overlap_with_historical_changed_extent_cells'], 2)
            self.assertEqual(hits[0]['cells'], 3)

    def test_hash_and_mask_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); config = self.setup_case(root)
            cfg = json.loads(config.read_text()); cfg['reference_runs']['sha256'] = '0'*64; config.write_text(json.dumps(cfg))
            with self.assertRaisesRegex(ValueError, 'hash mismatch'): cluster.build(config, root/'bad')
            self.assertFalse((root/'bad').exists())
            cfg['reference_runs'] = pin(root/'reference/runs'); cfg['physical_runs'] = cfg['reference_runs']; config.write_text(json.dumps(cfg))
            with self.assertRaises(ValueError): cluster.build(config, root/'bad2')
            self.assertFalse((root/'bad2/report.json').exists())

    def test_category_physical_provenance_and_space_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); config=self.setup_case(root); cfg=json.loads(config.read_text())
            manifest=Path(cfg['provenance']['reference_manifest']['path']); data=json.loads(manifest.read_text()); data['categories'][-1]['name']='wrong name'; manifest.write_text(json.dumps(data)); cfg['provenance']['reference_manifest']=pin(manifest);config.write_text(json.dumps(cfg))
            with self.assertRaisesRegex(ValueError,'mappings differ'): cluster.build(config,root/'bad-mapping')
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); config=self.setup_case(root); cfg=json.loads(config.read_text())
            physical=Path(cfg['provenance']['physical_report']['path']); data=json.loads(physical.read_text()); data['output_sha256']['runs.u32le']='0'*64;physical.write_text(json.dumps(data));cfg['provenance']['physical_report']=pin(physical)
            candidate=Path(cfg['provenance']['candidate_report']['path']); data=json.loads(candidate.read_text());data['inputs']['physical_report']=pin(physical);candidate.write_text(json.dumps(data));cfg['provenance']['candidate_report']=pin(candidate);config.write_text(json.dumps(cfg))
            with self.assertRaisesRegex(ValueError,'physical report'):cluster.build(config,root/'bad-physical')
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); config=self.setup_case(root);cfg=json.loads(config.read_text());cfg['minimum_free_bytes']=2**63;config.write_text(json.dumps(cfg))
            with self.assertRaisesRegex(OSError,'free disk space'):cluster.build(config,root/'bad-space')
            self.assertFalse((root/'bad-space/report.json').exists())

    def test_randomized_against_dense_bfs(self):
        import random
        from collections import deque
        random.seed(33)
        for case in range(40):
            with tempfile.TemporaryDirectory() as d:
                root = Path(d); w, h = 8, 4
                candidate = [[random.choice([0, 17, 18, 19]) for _ in range(w)] for _ in range(h)]
                reference = [[random.choice([1, 17, 18, 19]) for _ in range(w)] for _ in range(h)]
                physical = [[1 if x == 0 else 17 for x in row] for row in candidate]
                cr,cu=write_rle(root/'candidate',candidate);rr,ru=write_rle(root/'reference',reference);pr,pu=write_rle(root/'physical',physical)
                (root/'inputs').mkdir();(root/'inputs/pin').write_text('fixture')
                cfg={'schema':'list1-land-clusters-config-v1','grid':{'width':w,'height':h,'step':45,'west':-180,'north':90},'candidate_rows':cr,'candidate_runs':cu,'reference_rows':rr,'reference_runs':ru,'physical_rows':pr,'physical_runs':pu,'provenance':{'fixture':pin(root/'inputs/pin')}}
                reports(root/'inputs', cfg); (root/'inputs/config').write_text(json.dumps(cfg));cluster.build(root/'inputs/config',root/'out')
                remaining={(y,x) for y in range(h) for x in range(w) if candidate[y][x] >= 17 and reference[y][x] >= 17 and candidate[y][x] != reference[y][x]}
                expected=[]
                while remaining:
                    start=remaining.pop(); part={start}; todo=deque([start])
                    while todo:
                        y,x=todo.popleft()
                        for dy in (-1,0,1):
                            for dx in (-1,0,1):
                                neighbor=(y+dy,(x+dx)%w)
                                if neighbor in remaining:
                                    remaining.remove(neighbor);part.add(neighbor);todo.append(neighbor)
                    expected.append(frozenset(part))
                db=sqlite3.connect(root/'out/clusters.sqlite'); got={}
                for y,a,b,comp in db.execute('SELECT row,start,end,root FROM resolved'):
                    got.setdefault(comp,set()).update((y,x) for x in range(a,b))
                db.close();self.assertCountEqual(expected, [frozenset(x) for x in got.values()], f'case {case}')

    def test_cluster_id_stable_across_output_path(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); config=self.setup_case(root)
            a=cluster.build(config, root/'a'); b=cluster.build(config, root/'b')
            self.assertEqual(a['comparison_sha256'], b['comparison_sha256'])
            def ids(p):
                db=sqlite3.connect(p); x=db.execute('SELECT cluster_id,membership_sha256 FROM clusters ORDER BY cluster_id').fetchall(); db.close(); return x
            self.assertEqual(ids(root/'a/clusters.sqlite'), ids(root/'b/clusters.sqlite'))

if __name__ == '__main__': unittest.main()
