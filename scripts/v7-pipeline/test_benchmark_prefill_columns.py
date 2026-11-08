import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

import compose_full_water_grid as c
from benchmark_prefill_columns import run_pair


class PrefillPairTests(unittest.TestCase):
    def test_complete_pair_both_orders_exact_and_new_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);inputs=root/'inputs';inputs.mkdir()
            rows=inputs/'rows';rows.write_bytes(np.asarray([0,1,2],dtype='<u4').tobytes())
            sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
            rles={}
            for name,values in [('physical',[4,1,4,17]),('v6',[4,8,4,18])]:
                runs=inputs/name;runs.write_bytes(np.asarray(values,dtype='<u4').tobytes())
                rles[name]={'rows_path':'rows','rows_sha256':sha(rows),'runs_path':name,'runs_sha256':sha(runs)}
            plan=inputs/'plan';plan.write_text(json.dumps({'schema':'worldatlas-v7-full-grid-composition-plan-v1',
                'grid':{'width':4,'height':2},'rle_inputs':rles,'water_layers':[]}))
            checkout=Path(__file__).resolve().parents[2]
            with patch.object(c,'W',4),patch.object(c,'H',2),patch.object(c,'GRID',{'width':4,'height':2}):
                for first in (False,True):
                    out=root/('candidate-first' if first else 'reference-first')
                    result=run_pair(plan,inputs,out,checkout,options=('--allow-unverified-snapshot','--allow-historical-v6'),candidate_first=first)
                    self.assertEqual(result['comparison']['status'],'all-prefill-rle-bytes-and-audit-identical')
                    self.assertEqual(result['candidate_first'],first)
                    self.assertEqual(result['execution_mode'],'in-process-python-api')
                    timings=result['timings']
                    self.assertEqual(list(timings),['column-candidate','tuple-reference'] if first else ['tuple-reference','column-candidate'])
                    self.assertGreater(timings['column-candidate']['stage_wall_seconds'],0)
                    with self.assertRaises(FileExistsError):run_pair(plan,inputs,out,checkout)
                result=run_pair(plan,inputs,root/'arrow-reader',checkout,
                    options=('--allow-unverified-snapshot','--allow-historical-v6'),arrow_spans=True)
                self.assertEqual(result['candidate_span_reader'],'pyarrow-columns')
                self.assertEqual(result['comparison']['status'],'all-prefill-rle-bytes-and-audit-identical')
                with self.assertRaises(ValueError):run_pair(plan,inputs,root/'bad',checkout,options=('--anything',))
                self.assertFalse((root/'bad').exists())


if __name__=='__main__':unittest.main()
