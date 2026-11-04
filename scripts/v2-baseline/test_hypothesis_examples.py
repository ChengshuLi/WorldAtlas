import json,unittest
from pathlib import Path
class HypothesisExamples(unittest.TestCase):
 def test_examples_are_explicit_and_portable(self):
  root=Path(__file__).resolve().parent/'hypothesis'
  for name in ('water','arctic','caribbean'):
   c=json.loads((root/(name+'-route.example.json')).read_text());self.assertEqual(c['schema'],'simple-v2-water-route-v1');x0,x1,y0,y1=c['bounds']
   for x,y in (c['start'],c['end']):self.assertTrue(x0<=x<x1 and y0<=y<y1)
   self.assertTrue(all(c[k]['path'].startswith('/path/to/') and len(c[k]['sha256'])==64 for k in ('physical_rows','physical_runs')))
  c=json.loads((root/'regions.example.json').read_text());self.assertEqual(c['schema'],'simple-v2-regions-v1');self.assertEqual(c['join_tolerance_degrees'],0);self.assertEqual({r['id'] for r in c['regions']},{'Europe','North_America'})
  segments=[s for r in c['regions'] for s in r['segments']]
  for s in segments:
   if s['kind']=='feature':self.assertEqual(s['file']['sha256'],'b0401ee291aff8b6b5fdaabb4501e7321cbf6c8e9eba9be19cdca6e7ab846382');self.assertTrue(s['file']['path'].startswith('/path/to/'))
   if s['kind']=='water-route':self.assertEqual(s['report']['sha256'],'REPLACE');self.assertTrue(s['report']['path'].startswith('/path/to/'))
if __name__=='__main__':unittest.main()
