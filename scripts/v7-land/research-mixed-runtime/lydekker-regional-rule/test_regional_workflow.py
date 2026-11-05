import unittest
from regional_workflow import buffered_bounds

class TestWorkflow(unittest.TestCase):
    def test_conservative_buffer(self):
        w,s,e,n=buffered_bounds([115,-12,145,8],5000)
        self.assertLess(w,115);self.assertLess(s,-12);self.assertGreater(e,145);self.assertGreater(n,8)
        self.assertGreater(115-w,0.05);self.assertGreater(-12-s,0.05)
    def test_no_wrap_or_pole(self):
        with self.assertRaises(ValueError):buffered_bounds([179.99,-10,180,10],5000)
        with self.assertRaises(ValueError):buffered_bounds([0,88,1,89.9],5000)
    def test_boo_component_must_be_wholly_east(self):
        from unittest.mock import patch
        from regional_workflow import require_boo_east
        bounds=[115,-12,145,8]
        east={'total':4,'in_scope':4,'east':4,'west':0,'boundary':0,'outside_latitude':0}
        with patch('regional_workflow.component_at',return_value=123):
            require_boo_east(bounds,{123:east},{},{},{})
            with self.assertRaisesRegex(ValueError,'whole Boo'):
                require_boo_east(bounds,{123:dict(east,east=3,west=1)},{},{},{})
    def test_superseded_line_is_rejected(self):
        from regional_workflow import research
        with self.assertRaisesRegex(ValueError,'unapproved'):
            research({}, {}, {'width':360,'west':-180,'step':1}, [], {}, {}, {}, [], set(), None, None, {}, line_pin={'line_id':'old-v1','geometry_sha256':'0'*64},max_satellite_cells=1,max_gap_m=1)
    def test_end_to_end_research_without_map_write(self):
        import hashlib, importlib.util, json, os, struct, sys, tempfile, zipfile
        from pathlib import Path
        from unittest.mock import patch
        from regional_rule import SOURCE_ID, SOURCE_VERSION, SOURCE_PDF_SHA256
        from regional_workflow import research
        mixed=os.environ.get('MIXED_CLAIMS_PATH'); pair=os.environ.get('RUN_PAIR_PATH')
        if not mixed or not pair: self.skipTest('existing replay and WGS84 modules unavailable')
        def load(name,path):
            spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
        sys.path.insert(0,str(Path(pair).parent))
        try:
            mixed_module=load('mixed_integration',mixed); pair_module=load('pair_integration',pair)
            with tempfile.TemporaryDirectory() as tmp:
                rows=Path(tmp)/'rows';runs=Path(tmp)/'runs'
                rows.write_bytes(struct.pack('<IIIII',0,0,2,2,2))
                runs.write_bytes(struct.pack('<IIIIII',183,184,1,184,187,2))
                pin=lambda p:{'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
                geom={'type':'LineString','coordinates':[[4,1.5],[4,-1.5]]}
                digest=hashlib.sha256(json.dumps(geom,sort_keys=True,separators=(',', ':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()
                obs={'line_id':'test','geometry':geom,'geometry_sha256':digest,'source_id':SOURCE_ID,'source_version':SOURCE_VERSION,'status':'research','provenance':{'source_pdf_sha256':SOURCE_PDF_SHA256}}
                compiled={'revision':'r1','entity_revision':'e1','affiliation_ids':['group'],'affiliation_entry_links':{'group':['e']}}
                snap={'affiliations':[{'affiliation_id':'group','method':'component_intersection_v1','entity_id':5}], 'category_bindings':[{'entity_id':5,'physical_class':'land','code':22}]}
                reports=[{'schema':'source-polygon-component-report-v1','status':'research-only-not-a-build','revision':'r1','entity_revision':'e1','claims':[{'affiliation_id':'group','entity_id':5,'entity_code':22,'method':'component_intersection_v1','component_ids':[2]}]}]
                anchor={2:{'code':22,'source_id':'source','source_feature_id':'island','source_version':'v1','source_sha256':'a'*64,'main_island_evidence':'reviewed source'}}
                with patch('regional_workflow.APPROVED_LINE_ID','test'), patch('regional_workflow.APPROVED_GEOMETRY',digest):
                    out=research(pin(rows),pin(runs),{'width':360,'height':4,'west':-180,'north':2,'step':1},[0,-1,8,1],obs,compiled,snap,reports,set(),mixed_module,pair_module.run_pair,anchor,line_pin={'line_id':'test','geometry_sha256':digest},max_satellite_cells=1,max_gap_m=120000)
                self.assertEqual(out['proposals'][1]['code'],22)
                self.assertEqual(out['proposals'][1]['basis'],'source_anchored_nearest_main_island')
                self.assertEqual(out['proposals'][2]['basis'],'selected_affiliation')
                self.assertIn(2,out['replayed_claims'])
                self.assertEqual(set(Path(tmp).iterdir()),{rows,runs})
                with patch('regional_workflow.APPROVED_LINE_ID','test'), patch('regional_workflow.APPROVED_GEOMETRY',digest):
                    outside=research(pin(rows),pin(runs),{'width':360,'height':4,'west':-180,'north':2,'step':1},[0,-1,3.8,1],obs,compiled,snap,reports,set(),mixed_module,pair_module.run_pair,anchor,line_pin={'line_id':'test','geometry_sha256':digest},max_satellite_cells=1,max_gap_m=120000)
                self.assertEqual(outside['proposals'][1]['code'],22)
                self.assertNotIn(2,outside['proposals'])
                self.assertIn(2,outside['buffer_anchor_claims'])
                archive=Path(tmp)/'islands.zip'
                fields=['99','Main Island','Main Island','','0.5','4.5','T','ISL','ID']+['']*10
                with zipfile.ZipFile(archive,'w') as z: z.writestr('ID.txt','\t'.join(fields)+'\n')
                source={'path':str(archive),'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'source_id':'geonames-country-id','source_version':'test','country':'ID'}
                with patch('regional_workflow.APPROVED_LINE_ID','test'), patch('regional_workflow.APPROVED_GEOMETRY',digest):
                    auto=research(pin(rows),pin(runs),{'width':360,'height':4,'west':-180,'north':2,'step':1},[0,-1,8,1],obs,compiled,snap,reports,set(),mixed_module,pair_module.run_pair,None,line_pin={'line_id':'test','geometry_sha256':digest},max_satellite_cells=1,max_gap_m=120000,anchor_source=source)
                self.assertEqual(auto['proposals'][1]['code'],22)
                self.assertEqual(auto['satellites'][1]['source_feature_id'],'99')
                self.assertEqual(auto['anchor_discovery']['eligible_anchors'],1)
        finally: sys.path.pop(0)
if __name__=='__main__':unittest.main()
