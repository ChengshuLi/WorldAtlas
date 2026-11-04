import hashlib,json,math,os,subprocess,tempfile,unittest
from pathlib import Path
import numpy as np
import nearest_mainland as n

HERE=Path(__file__).parent

def pin(path): return {'path':str(path),'sha256':n.sha(path)}
def write_rle(prefix,values):
    h,w=values.shape; runs=[]; rows=[0]
    for row in values:
        for x in range(w):
            if x==w-1 or row[x]!=row[x+1]: runs.append((x+1,int(row[x])))
        rows.append(len(runs))
    rp=prefix.with_name(prefix.name+'-rows'); xp=prefix.with_name(prefix.name+'-runs')
    np.asarray(rows,dtype='<u4').tofile(rp); np.asarray(runs,dtype='<u4').tofile(xp)
    return rp,xp

class Distance(unittest.TestCase):
    def test_exact_segment_against_all_pairs(self):
        rng=np.random.default_rng(42); w=24; step=15; north=90
        for _ in range(300):
            y,yy=rng.integers(0,12,2); a=int(rng.integers(w)); b=int(rng.integers(a+1,w+1)); c=int(rng.integers(w)); d=int(rng.integers(c+1,w+1))
            actual=n.segment_distance(y,a,b,[yy],[c],[d],w,step,north)[0]
            p=n.unit(np.full(b-a,north-(y+.5)*step),-180+(np.arange(a,b)+.5)*step)
            q=n.unit(np.full(d-c,north-(yy+.5)*step),-180+(np.arange(c,d)+.5)*step)
            chord=np.linalg.norm(p[:,None,:]-q[None,:,:],axis=2).min(); expected=2*n.R*math.asin(min(1,chord/2))
            self.assertAlmostEqual(actual,expected,places=6)
    def test_index_matches_bruteforce(self):
        rng=np.random.default_rng(22); w=24; step=15; north=90
        segments=[]
        for i in range(80):
            y=int(rng.integers(12)); a=int(rng.integers(w)); b=int(rng.integers(a+1,min(w,a+4)+1)); segments.append((y,a,b,17+i%6))
        idx=n.index_mainlands(segments,w,step,north)
        for _ in range(30):
            y=int(rng.integers(12)); a=int(rng.integers(w)); b=int(rng.integers(a+1,min(w,a+4)+1))
            got=n.nearest_run(y,a,b,idx,w,step,north,1e-5)
            data=np.asarray(segments); ds=n.segment_distance(y,a,b,data[:,0],data[:,1],data[:,2],w,step,north)
            self.assertAlmostEqual(min(got.values()),float(ds.min()),places=6)
            expected={int(code) for code in set(data[ds<=ds.min()+1e-5,3])}
            self.assertEqual({k for k,v in got.items() if v<=min(got.values())+1e-5},expected)

    def test_disk_tiles_match_bruteforce(self):
        rng=np.random.default_rng(45);w=144;step=2.5;north=90;h=72
        rows=[]
        for _ in range(500):
            y=int(rng.integers(h));a=int(rng.integers(w));b=int(rng.integers(a+1,min(w,a+8)+1));rows.append((y,a,b,int(rng.integers(17,23))))
        rows.sort()
        with tempfile.TemporaryDirectory() as tmp:
            idx=n.TileIndex(Path(tmp)/'tiles',w,h,step,north,n.segment_distance,n.unit,n.R,tile_cells=8,cache_bytes=512)
            for row in rows:idx.append(*row)
            idx.finish(); data=np.asarray(rows)
            for _ in range(30):
                y=int(rng.integers(h));a=int(rng.integers(w));b=int(rng.integers(a+1,min(w,a+8)+1))
                got=idx.nearest(y,a,b,1e-5)
                ds=n.segment_distance(y,a,b,data[:,0],data[:,1],data[:,2],w,step,north)
                self.assertAlmostEqual(min(got.values()),float(ds.min()),places=6)
                self.assertEqual({k for k,v in got.items() if v<=min(got.values())+1e-5},{int(x) for x in data[ds<=ds.min()+1e-5,3]})
            self.assertLessEqual(idx.stats()['cache_peak_bytes'],512)

    def test_corrupt_tile_rejected_before_native_kernel(self):
        with tempfile.TemporaryDirectory() as tmp:
            idx=n.TileIndex(Path(tmp)/'tiles',24,12,15,90,n.segment_distance,n.unit,n.R,tile_cells=8,cache_bytes=512)
            idx.append(1,1,2,17);idx.finish();path=idx.path(idx.ids[0])
            np.asarray([[999999,1,2,17]],dtype='<u4').tofile(path)
            with self.assertRaisesRegex(ValueError,'corrupt tile records'):idx.nearest(2,2,3,1e-5)

class Build(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory(); self.base=Path(self.t.name); inp=self.base/'input'; inp.mkdir()
        w,h=12,6; self.physical=np.ones((h,w),dtype=np.uint32); self.seed=np.zeros((h,w),dtype=np.uint32)
        for i,x in enumerate([0,2,4,6,8,10]): self.physical[0,x]=17; self.seed[0,x]=17+i
        self.physical[2,0]=17
        pr,px=write_rle(inp/'physical',self.physical); mr,mx=write_rle(inp/'mainland',self.seed)
        subprocess.run(['g++','-std=c++17','-O2',str(HERE.parent/'build_components.cpp'),'-o',str(inp/'builder')],check=True)
        cr,cx=inp/'component-rows',inp/'component-runs'
        subprocess.run([str(inp/'builder'),str(w),str(h),str(pr),str(px),str(cr),str(cx)],check=True,capture_output=True)
        rows=np.fromfile(cr,dtype='<u4'); runs=np.fromfile(cx,dtype='<u4').reshape(-1,3)
        self.mainroots=[int(x[2]) for x in runs[rows[0]:rows[1]]]; self.island=int(runs[rows[2],2])
        self.cfg={'schema':'nearest-mainland-build-v1','grid':{'width':w,'height':h,'step':30,'west':-180,'north':90},'physical_rows':pin(pr),'physical_runs':pin(px),'component_rows':pin(cr),'component_runs':pin(cx),'mainland_rows':pin(mr),'mainland_runs':pin(mx)}
        self.snap={'schema':'worldatlas-geography-decision-draft-evidence-v1','source':'neon-export','decision_revision':{'id':'d1','status':'draft','entity_revision':'e1'},'entity_revision':{'id':'e1','status':'draft'},'entities':[{'id':i+1} for i in range(6)],'category_bindings':[{'entity_id':i+1,'physical_class':'land','code':17+i} for i in range(6)],'land_mainland_policy':{'execution_status':'selected_for_research','method':'nearest_mainland_v1','distance':'minimum_spherical_cell_center','tie':'fail','precedence':'mainland_then_reviewed_component_then_nearest','component_algorithm_sha256':n.sha(HERE.parent/'build_components.cpp'),'mainland_component_ids':self.mainroots,'reviewed_component_claims':[],'source_cut_feature_ids':[],'grid':self.cfg['grid'].copy(),'chunk_columns':2,'tolerance_metres':1e-5}}
        for k in ('physical_rows','physical_runs','component_rows','component_runs','mainland_rows','mainland_runs'): self.snap['land_mainland_policy'][k+'_sha256']=self.cfg[k]['sha256']
        self.cp=inp/'config.json'; self.sp=inp/'snapshot.json'; self.save()
    def tearDown(self): self.t.cleanup()
    def save(self):
        self.sp.write_text(json.dumps(self.snap)); self.cfg['snapshot']=pin(self.sp); self.cp.write_text(json.dumps(self.cfg))
    def runbuild(self): return n.build(self.cp,self.base/'out',True)
    def test_nearest_and_reviewed_override(self):
        result=self.runbuild(); self.assertEqual([(v['component_id'],v['code']) for v in result['nearest_claims']],[(self.island,17)])
    def test_parallel_matches_serial(self):
        self.cfg['workers']=2; self.save()
        result=self.runbuild(); self.assertEqual([(v['component_id'],v['code']) for v in result['nearest_claims']],[(self.island,17)]); self.assertEqual(result['query_workers'],2)
    def test_reviewed_override(self):
        self.snap['land_mainland_policy']['reviewed_component_claims']=[{'rule_id':'reviewed','component_id':self.island,'entity_id':4}]; self.save()
        result=self.runbuild(); self.assertEqual(result['nearest_claims'],[]); self.assertEqual(result['reviewed_claims'][0]['entity_id'],4)
    def test_unverified_snapshot_requires_opt_in(self):
        with self.assertRaisesRegex(ValueError,'snapshot authenticity is unverified'): n.build(self.cp,self.base/'out')
        self.assertFalse((self.base/'out').exists())
    def test_no_policy_fails_before_output(self):
        del self.snap['land_mainland_policy']; self.save()
        with self.assertRaisesRegex(ValueError,'missing reviewed mainland policy'): self.runbuild()
        self.assertFalse((self.base/'out').exists())
    def test_incomplete_mainland_partition_fails(self):
        self.seed[0,0]=0; mr,mx=write_rle(self.base/'input'/'otherseed',self.seed)
        self.cfg['mainland_rows']=pin(mr); self.cfg['mainland_runs']=pin(mx)
        for k in ('mainland_rows','mainland_runs'): self.snap['land_mainland_policy'][k+'_sha256']=self.cfg[k]['sha256']
        self.save()
        with self.assertRaisesRegex(ValueError,'mainland seed missing'): self.runbuild()
        self.assertFalse((self.base/'out'/'claims.json').exists())
    def test_unknown_override_fails(self):
        self.snap['land_mainland_policy']['reviewed_component_claims']=[{'rule_id':'bad','component_id':999999,'entity_id':1}]; self.save()
        with self.assertRaisesRegex(ValueError,'unknown mainland or reviewed'): self.runbuild()
    def test_invalid_component_hash_fails(self):
        self.cfg['component_runs']['sha256']='0'*64; self.save()
        with self.assertRaisesRegex(ValueError,'input digest mismatch'): self.runbuild()
    def test_tie_fails_closed_during_build(self):
        from unittest.mock import patch
        with patch.object(n.TileIndex,'nearest',return_value={17:100.0,18:100.0}):
            with self.assertRaisesRegex(ValueError,'ambiguous nearest mainland'): self.runbuild()
        self.assertFalse((self.base/'out'/'claims.json').exists())
    def test_unselected_policy_fails(self):
        self.snap['land_mainland_policy']['execution_status']='candidate'; self.save()
        with self.assertRaisesRegex(ValueError,'unsupported or incomplete mainland policy'): self.runbuild()
        self.assertFalse((self.base/'out').exists())
    def test_accepted_snapshot_rejected(self):
        self.snap['schema']='worldatlas-geography-decision-export-v1';self.snap['decision_revision']['status']='accepted';self.snap['entity_revision']['status']='accepted';self.save()
        with self.assertRaisesRegex(ValueError,'requires draft snapshot'):n.build(self.cp,self.base/'out',True)
        self.assertFalse((self.base/'out').exists())
    def test_grid_mismatch_fails(self):
        self.snap['land_mainland_policy']['grid']['north']=89; self.save()
        with self.assertRaisesRegex(ValueError,'policy grid mismatch'): self.runbuild()
    def test_tie_fails(self):
        # Deliberately place reviewed mainland seeds symmetrically at +/-30 degrees
        # from the extra island on a global grid, and use a large tolerance only
        # in the distance-level test rather than invent a priority.
        idx=n.index_mainlands([(2,0,1,17),(2,2,3,18)],12,30,90)
        d=n.nearest_run(2,1,2,idx,12,30,90,1e-5)
        self.assertAlmostEqual(d[17],d[18],places=6)

if __name__=='__main__': unittest.main()
