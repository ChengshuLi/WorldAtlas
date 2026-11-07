import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

import cluster
import reconcile
import test_cluster as fixtures
pin, write_rle = fixtures.pin, fixtures.write_rle


class ReconcileTest(unittest.TestCase):
    def fixture(self, root):
        original=fixtures.ClustersTest().setup_case(root)
        initial=cluster.build(original, root/'initial')
        orig=json.loads(original.read_text())
        post=[[17,17,17,17,17,17,17,19],[18,17,17,17,17,17,19,17],[17,17,17,17,17,17,17,17],[1,17,17,17,17,17,17,17]]
        rows,runs=write_rle(root/'post',post)
        directory=root/'post-inputs';directory.mkdir()
        snapshot=directory/'snapshot.json';snapshot.write_text(Path(orig['provenance']['decision_snapshot']['path']).read_text())
        report=directory/'report.json';report.write_text(json.dumps({'schema':'direct-neon-land-stream-build-report-v1','status':'unverified-research-not-published','snapshot_sha256':pin(snapshot)['sha256'],'decision_revision':'d','entity_revision':'e','decision_revision_asserted_status':'draft','decision_summary':[{'affiliation_id':'aff1'}],'compiler_report':{'output_rows_sha256':rows['sha256'],'output_runs_sha256':runs['sha256'],'input_sha256':{n:orig[n]['sha256'] for n in ('physical_rows','physical_runs')}}}))
        render=directory/'render.json';render.write_text(json.dumps({'schema':'worldatlas-new-list1-draft-v1','status':'research-not-published','decision_revision':'d','snapshot_sha256':pin(snapshot)['sha256'],'build_report_sha256':pin(report)['sha256'],'entries':[{'entry_id':'entry1','decisions':[{'affiliation_id':'aff1'}]}]}))
        db=sqlite3.connect(root/'initial/clusters.sqlite');cid=db.execute('SELECT cluster_id FROM clusters ORDER BY cells DESC LIMIT 1').fetchone()[0];db.close()
        links=directory/'links.json';links.write_text(json.dumps({'schema':'list1-cluster-links-v1','comparison_sha256':initial['comparison_sha256'],'links':[{'cluster_id':cid,'entry_ids':['entry1'],'decision_ids':['aff1'],'rationale':'reviewed mapping'}]}))
        cfg={'schema':'list1-land-reconciliation-config-v1','post_rows':rows,'post_runs':runs,'post_report':pin(report),'post_snapshot':pin(snapshot),'list1_render':pin(render),'cluster_links':pin(links),'minimum_free_bytes':0}
        config=directory/'config.json';config.write_text(json.dumps(cfg))
        return original,config

    def test_accounting_and_attribution(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); original,config=self.fixture(root)
            report=reconcile.reconcile(root/'initial',original,config,root/'out')
            self.assertEqual(report['counts'],{'initial_mismatches':5,'explained_cells':3,'unresolved_cells':2,'extra_changed_shared_land_cells':1,'post_mismatches':3})
            self.assertFalse(report['numerical_acceptance'])
            lines=[json.loads(x) for x in (root/'out/clusters.jsonl').read_text().splitlines()]
            self.assertEqual(sum(x['explained_cells'] for x in lines),3)
            self.assertEqual(sum(x['unresolved_cells'] for x in lines),2)
            self.assertEqual(sum(x['decision_ids']==['aff1'] for x in lines),1)

    def test_randomized_dense_accounting(self):
        import random
        random.seed(71)
        for case in range(30):
            with tempfile.TemporaryDirectory() as d:
                root=Path(d);w,h=8,4
                base=[[random.choice([0,17,18,19]) for _ in range(w)] for _ in range(h)]
                ref=[[random.choice([1,17,18,19]) for _ in range(w)] for _ in range(h)]
                post=[[1 if base[y][x]==0 else random.choice([17,18,19]) for x in range(w)] for y in range(h)]
                physical=[[1 if n==0 else 17 for n in row] for row in base]
                cr,cu=write_rle(root/'candidate',base);rr,ru=write_rle(root/'reference',ref);pr,pu=write_rle(root/'physical',physical)
                inp=root/'inputs';inp.mkdir()
                orig={'schema':'list1-land-clusters-config-v1','grid':{'width':w,'height':h,'step':45,'west':-180,'north':90},'candidate_rows':cr,'candidate_runs':cu,'reference_rows':rr,'reference_runs':ru,'physical_rows':pr,'physical_runs':pu,'provenance':{},'minimum_free_bytes':0}
                fixtures.reports(inp,orig);oc=inp/'config';oc.write_text(json.dumps(orig));initial=cluster.build(oc,root/'initial')
                ar,au=write_rle(root/'post',post); snap=inp/'post-snapshot';snap.write_text(Path(orig['provenance']['decision_snapshot']['path']).read_text())
                report=inp/'post-report';report.write_text(json.dumps({'schema':'direct-neon-land-stream-build-report-v1','status':'unverified-research-not-published','snapshot_sha256':pin(snap)['sha256'],'decision_revision':'d','entity_revision':'e','decision_revision_asserted_status':'draft','decision_summary':[],'compiler_report':{'output_rows_sha256':ar['sha256'],'output_runs_sha256':au['sha256'],'input_sha256':{'physical_rows':pr['sha256'],'physical_runs':pu['sha256']}}}))
                render=inp/'render';render.write_text(json.dumps({'schema':'worldatlas-new-list1-draft-v1','status':'research-not-published','decision_revision':'d','snapshot_sha256':pin(snap)['sha256'],'build_report_sha256':pin(report)['sha256'],'entries':[]}))
                links=inp/'links';links.write_text(json.dumps({'schema':'list1-cluster-links-v1','comparison_sha256':initial['comparison_sha256'],'links':[]}))
                pc=inp/'post-config';pc.write_text(json.dumps({'schema':'list1-land-reconciliation-config-v1','post_rows':ar,'post_runs':au,'post_report':pin(report),'post_snapshot':pin(snap),'list1_render':pin(render),'cluster_links':pin(links),'minimum_free_bytes':0}))
                got=reconcile.reconcile(root/'initial',oc,pc,root/'out')['counts']
                expected={'initial_mismatches':0,'explained_cells':0,'unresolved_cells':0,'extra_changed_shared_land_cells':0,'post_mismatches':0}
                for y in range(h):
                    for x in range(w):
                        a,b,c=base[y][x],ref[y][x],post[y][x]
                        if a==0 or b==1:continue
                        if a!=b:
                            expected['initial_mismatches']+=1
                            expected['explained_cells' if c==b else 'unresolved_cells']+=1
                        elif c!=b:expected['extra_changed_shared_land_cells']+=1
                        if c!=b:expected['post_mismatches']+=1
                self.assertEqual(got,expected,f'case {case}')

    def test_numerical_success_does_not_hide_missing_attribution(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);original,config=self.fixture(root);cfg=json.loads(config.read_text())
            post=[[17,17,17,17,17,17,17,17],[17,17,17,17,17,17,17,17],[17,17,17,17,17,17,17,17],[1,17,17,17,17,17,17,17]]
            cfg['post_rows'],cfg['post_runs']=write_rle(root/'perfect-post',post)
            report=Path(cfg['post_report']['path']);j=json.loads(report.read_text());j['compiler_report']['output_rows_sha256']=cfg['post_rows']['sha256'];j['compiler_report']['output_runs_sha256']=cfg['post_runs']['sha256'];report.write_text(json.dumps(j));cfg['post_report']=pin(report)
            render=Path(cfg['list1_render']['path']);j=json.loads(render.read_text());j['build_report_sha256']=cfg['post_report']['sha256'];render.write_text(json.dumps(j));cfg['list1_render']=pin(render);config.write_text(json.dumps(cfg))
            result=reconcile.reconcile(root/'initial',original,config,root/'out')
            self.assertTrue(result['numerical_acceptance']);self.assertEqual(result['counts']['unresolved_cells'],0)
            self.assertEqual(result['unattributed_clusters'],2);self.assertEqual(result['unattributed_initial_cells'],2)

    def test_reject_unknown_decision_and_changed_mask(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);original,config=self.fixture(root);cfg=json.loads(config.read_text());links=Path(cfg['cluster_links']['path']);j=json.loads(links.read_text());j['links'][0]['decision_ids']=['unknown'];links.write_text(json.dumps(j));cfg['cluster_links']=pin(links);config.write_text(json.dumps(cfg))
            with self.assertRaisesRegex(ValueError,'attribution'):reconcile.reconcile(root/'initial',original,config,root/'bad')
            self.assertFalse((root/'bad/report.json').exists())
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);original,config=self.fixture(root);cfg=json.loads(config.read_text());post=Path(cfg['post_runs']['path']);data=bytearray(post.read_bytes());data[4:8]=(1).to_bytes(4,'little');post.write_bytes(data);cfg['post_runs']=pin(post);rp=Path(cfg['post_report']['path']);j=json.loads(rp.read_text());j['compiler_report']['output_runs_sha256']=cfg['post_runs']['sha256'];rp.write_text(json.dumps(j));cfg['post_report']=pin(rp);render=Path(cfg['list1_render']['path']);j=json.loads(render.read_text());j['build_report_sha256']=cfg['post_report']['sha256'];render.write_text(json.dumps(j));cfg['list1_render']=pin(render);config.write_text(json.dumps(cfg))
            with self.assertRaisesRegex(ValueError,'physical mask changed'):reconcile.reconcile(root/'initial',original,config,root/'bad')
            self.assertFalse((root/'bad/report.json').exists())

if __name__=='__main__': unittest.main()
