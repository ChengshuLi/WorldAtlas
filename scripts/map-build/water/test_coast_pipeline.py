import copy,json,tempfile,unittest
from pathlib import Path
import numpy as np
import build_coastal_tile as tile
import assemble_coastal_tiles as assemble
from test_coastal_core import snap
from test_helpers import rle

class PipelineTest(unittest.TestCase):
 def test_tile_to_assembled_layer_preserves_inputs_and_ignores_policy_notes(self):
  width,height=360,180;p=np.ones((height,width),dtype=np.uint32);l=np.zeros_like(p)
  p[89,4]=p[89,6]=17;l[89,4]=17;l[89,6]=18
  physical,land=rle(p),rle(l);snapshot=snap();pins={k:'a'*64 for k in ('physical_rows_sha256','physical_runs_sha256',
   'physical_report_sha256','land_rows_sha256','land_runs_sha256','land_report_sha256')}
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);entries=[]
   for i,(a,b) in enumerate(((0,180),(180,360))):
    out=root/f'tile{i}';tile.run(snapshot,'b'*64,physical,land,out,width,height,[a,b,0,height],180,pins,allow_selected_research=True)
    entries.append({'manifest_path':f'tile{i}/manifest.json','manifest_sha256':tile.sha(out/'manifest.json')})
   layer=assemble.assemble(snapshot,'b'*64,entries,root,root/'coast.json',width,height,allow_selected_research=True)
   self.assertTrue(layer['coverage']['complete']);self.assertGreater(layer['assigned_cells'],0)
   self.assertEqual(layer['source']['physical_report_sha256'],pins['physical_report_sha256'])
   self.assertEqual(layer['source']['land_report_sha256'],pins['land_report_sha256'])
   changed=copy.deepcopy(snapshot);changed['policies'][0]['evidence']={}
   result=assemble.assemble(changed,'b'*64,entries,root,root/'notes.json',width,height,allow_selected_research=True)
   self.assertEqual(result['assigned_cells'],layer['assigned_cells'])

if __name__=='__main__':unittest.main()
