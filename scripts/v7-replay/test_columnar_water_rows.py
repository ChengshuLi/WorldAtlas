import gzip
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

import columnar_water_rows as columns
import compose_full_water_grid as reference
from prefill_columns import LayerPolicy


def record(row=0,start=1,stop=4,**extra):
    span={'start':start,'end':stop,'code':3,'rule_id':'r','member_id':'member'}
    span.update(extra)
    return {'row':row,'spans':[span]}


class ColumnarWaterTests(unittest.TestCase):
    def compare(self,data,*,rows=(0,4),sparse=True,cols=None,compressed=False,block_size=128):
        if isinstance(data,list):data=('\n'.join(json.dumps(r,ensure_ascii=False) for r in data)+'\n').encode()
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/('tile.gz' if compressed else 'tile')
            path.write_bytes(gzip.compress(data) if compressed else data)
            tile={'_path':path,'_rows':rows,'_cols':cols}
            try:expected=list(reference.tile_spans(tile,0,rows[1],'water',sparse))
            except Exception as expected_error:
                with self.assertRaises(type(expected_error)) as actual:
                    list(columns.tile_rows(tile,0,rows[1],sparse,block_size=block_size))
                self.assertEqual(str(actual.exception),str(expected_error))
                return None
            batches=list(columns.tile_rows(tile,0,rows[1],sparse,block_size=block_size))
            actual=[span for row,batch in batches for span in batch.reference_records(row)]
            self.assertEqual(actual,expected)
            return batches

    def test_canonical_plain_and_gzip_defer_python_metadata(self):
        for compressed in (False,True):
            batches=self.compare([record(0),{'row':1,'spans':[]},record(2,4,7)],compressed=compressed)
            self.assertTrue(all(batch.arrow is not None for _,batch in batches))
            policy=LayerPolicy([{'layer_id':'arbitrary','manifest_path':'m','priority':2}])
            with patch.object(columns.ColumnSpans,'reference_records',side_effect=AssertionError('must keep columns')):
                for row,batch in batches:
                    resolved=policy.resolve([(0,batch)],row,np.asarray([128]),np.asarray([1]))
                    self.assertFalse(resolved.used_reference)
                    self.assertEqual(resolved.columns[2].tolist(),[3])

    def test_aliases_coercions_missing_metadata_and_duplicate_keys(self):
        cases=[b'{"row":"0","spans":[{"x_start":"1","x_end_exclusive":"4","to_code":"3","rule_id":"r","source_member_id":"m"}]}\n',
               b'{"row":0,"spans":[{"start":1.9,"end":4.9,"code":3.1,"rule_id":"r","member_id":"m"}]}\n',
               b'{"row":0,"spans":[{"start":true,"end":4,"code":3,"rule_id":2,"member_id":42}]}\n',
               b'{"row":0,"spans":[{"start":1,"end":4,"code":3,"rule_id":"r","member_id":"","source_member_id":"fallback"}]}\n',
               b'{"row":1,"row":0,"spans":[{"start":1,"end":4,"code":3,"rule_id":"r","member_id":"m"}]}\n',
               b'{"row":0,"spans":[{"start":0,"start":1,"end":4,"code":2,"code":3,"rule_id":"r","member_id":"first","member_id":"last"}]}\n',
               b'{"row":0}\n',b'{"row":0,"spans":null}\n']
        for case in cases:
            with self.subTest(case=case):self.compare(case)

    def test_json_and_utf8_representation_contract_is_preserved(self):
        cases=[b'\xef\xbb\xbf{"row":0,"spans":[]}\n',
               b'{"row":0,"spans":[],"ignored":"\xff"}\n',
               b'{"row":0,"spans":[]} {"row":1,"spans":[]}\n',
               b'{"row":0,\n"spans":[]}\n',
               b'{"row":0,"spans":[{"start":1,"end":4,"code":3,"rule_id":"r","member_id":"\\ud800"}]}\n',
               b'{"row":0,"spans":[]}\r{"row":1,"spans":[]}\r',
               b'{"row":0,"spans":[],"ignored":NaN}\n',
               b'{"row":0,"spans":[],}\n',
               b'{"row":0,"spans":[{"start":1,"end":4,"code":3,"rule_id":"r","member_id":"} {"}]}\n']
        for case in cases:
            with self.subTest(case=case):self.compare(case)
        self.compare([record(0,member_id='😀\u2028é'),record(1,rule_id='r\x00x')])

    def test_sparse_duplicate_rows_and_dense_coverage_validation(self):
        for sparse in (False,True):
            with self.subTest(sparse=sparse):
                self.compare([record(0,1,3),record(0,3,5),{'row':1,'spans':[]},record(2),{'row':3,'spans':[]}],sparse=sparse)
        invalid=[[record(2),record(1)],[record(0),record(0,2,6)],
                 [record(0),record(4)],[record(0,start=-1)],[record(0,stop=reference.W+1)],
                 [record(0,code=0)],[record(0,code=11)],[record(0,rule_id='')],[record(0,member_id='')]]
        for data in invalid:
            with self.subTest(data=data):self.compare(data)
        self.compare([record(0),record(2)],sparse=False)
        self.compare([record(0)],sparse=False)
        self.compare([record(0,start=1,stop=6)],cols=(0,5))

    def test_fallback_after_stream_progress_has_no_missing_or_duplicate_spans(self):
        data=[record(row) for row in range(30)]
        data[-1]={'row':29,'spans':[{'x_start':1,'x_end_exclusive':4,'to_code':3,'rule_id':'r','source_member_id':'m'}]}
        with patch.object(columns,'original_remainder',wraps=columns.original_remainder) as fallback:
            self.compare(data,rows=(0,30),compressed=True,block_size=256)
            self.assertTrue(fallback.called)
            self.assertGreater(fallback.call_args.args[-1],0)

    def test_merging_tiles_retains_global_span_order_and_reference_diagnostics(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);tiles=[]
            for i,items in enumerate(([record(0,6,9),record(2,5,7)], [record(0,1,4),record(1,2,3)])):
                path=root/str(i);path.write_text('\n'.join(map(json.dumps,items))+'\n')
                tiles.append({'_path':path,'_rows':(0,4),'_cols':None})
            manifest={'_tiles':tiles,'_sparse_rows_allowed':True}
            actual=[span for row,batch in columns.layer_rows(manifest,0,4) for span in batch.reference_records(row)]
            expected=[span for _,batch in reference.layer_rows(manifest,0,4,'water') for span in batch]
            self.assertEqual(actual,expected)
            cursor=columns.RowCursor(manifest,0,4)
            self.assertEqual(cursor.take(0).columns[0].tolist(),[1,6])
            self.assertEqual(cursor.take(1).columns[0].tolist(),[2])
            self.assertEqual(cursor.take(2).columns[0].tolist(),[5])
            self.assertEqual(cursor.take(3),[])

    def test_reference_policy_fallback_materializes_the_original_metadata(self):
        rows=self.compare([record(0,member_id='😀é')])
        batch=rows[0][1]
        entries=[{'layer_id':name,'manifest_path':name,'priority':1} for name in ('one','two')]
        policy=LayerPolicy(entries);chunks=[(0,batch),(1,batch)]
        with self.assertRaises(ValueError) as expected:
            policy.reference_row(chunks,0,np.asarray([128]),np.asarray([1]))
        with self.assertRaises(ValueError) as actual:
            policy.resolve(chunks,0,np.asarray([128]),np.asarray([1]))
        self.assertEqual(str(actual.exception),str(expected.exception))

    def test_zero_length_probe_does_not_finalize_a_partial_utf8_record(self):
        raw=json.dumps(record(0,member_id='😀'),ensure_ascii=False).encode()
        with columns.CompatibleJSONLines(io.BytesIO(raw)) as stream:
            self.assertEqual(stream.read(7),raw[:7]);self.assertEqual(stream.read(0),b'')
            self.assertEqual(stream.read(),raw[7:]);self.assertEqual(stream.read(),b'')

    def test_randomized_sparse_rows_and_multiple_span_values(self):
        rng=np.random.default_rng(20261110)
        for trial in range(80):
            data=[]
            for row in sorted(rng.choice(np.arange(32),size=16,replace=False).tolist()):
                spans=[];start=int(rng.integers(0,5))
                while start<100:
                    stop=min(100,start+int(rng.integers(1,8)))
                    spans.append({'start':start,'end':stop,'code':int(rng.integers(1,11)),
                                  'rule_id':'rule-\\-é','member_id':f'component-{trial}-{row}'})
                    start=stop+int(rng.integers(0,10))
                data.append({'row':row,'spans':spans})
            with self.subTest(trial=trial):
                self.compare(data,rows=(0,32),compressed=trial%2==0,block_size=4096)


if __name__=='__main__':unittest.main()
