"""Numeric resolver parity against the unchanged explicit-priority resolver."""
import unittest
from unittest.mock import patch

import numpy as np

import compose_full_water_grid as reference
from prefill_columns import LayerPolicy, empty_columns


def entry(label, priority, overrides=(), **extra):
    return dict(layer_id=label, manifest_path=label+'.json', priority=priority,
                overrides=list(overrides), **extra)


def span(start, stop, code=2, identity='owner'):
    return (7, start, stop, code, 'rule', identity, None, None)


def original(entries, chunks, row, ends, values):
    spans=[]
    for layer, records in chunks:
        ent=entries[layer]
        for record in records:
            if record[3]>6:
                raise ValueError(f'prefill layers may only assign water code 1–6, got {record[3]} on row {row}')
            if 'allowed_codes' in ent and record[3] not in ent['allowed_codes']:
                raise ValueError(f'assignment code not allowed by selected basin policy on row {row}: {record[3]}')
        spans.extend(reference.add_layer_identity(records,int(ent['priority']),
                     str(ent.get('layer_id',ent['manifest_path'])),set(ent.get('overrides',[]))))
    assignments, conflicts=reference.choose_assignments(spans,row,ends,values)
    return reference.assignment_arrays(assignments),sum(b-a for a,b in {(a,b) for a,b,_,_ in conflicts})


class PrefillColumnTests(unittest.TestCase):
    def assert_parity(self, entries, chunks, values=None, ends=None):
        ends=np.asarray([128] if ends is None else ends,dtype=np.uint32)
        values=np.asarray([1] if values is None else values,dtype=np.uint32)
        policy=LayerPolicy(entries)
        try:
            columns, overlap=original(entries,chunks,7,ends,values)
        except ValueError as exc:
            with self.assertRaises(ValueError) as actual:
                policy.resolve(chunks,7,ends,values)
            self.assertEqual(str(actual.exception),str(exc))
            return None
        actual=policy.resolve(chunks,7,ends,values)
        for left,right in zip(columns,actual.columns):np.testing.assert_array_equal(left,right)
        self.assertEqual(overlap,actual.overlap_cells)
        return actual

    def test_empty_and_single_band_retain_all_source_breakpoints(self):
        self.assert_parity([],[])
        self.assert_parity([entry('arbitrary',10**80)],[(0,[])])
        actual=self.assert_parity([entry('arbitrary',-10**80)],[(0,[span(2,4),span(4,8),span(11,12)])])
        self.assertFalse(actual.used_reference)
        self.assertEqual(actual.columns[0].tolist(),[2,4,11])

    def test_any_number_of_priority_levels_and_transitive_permissions(self):
        entries=[entry('one',-10),entry('two',5),entry('three',20,('one','two')),
                 entry('four',100,('one','two','three'))]
        # The intermediate layer has no permission, but is entirely shadowed.
        chunks=[(0,[span(2,30)]),(1,[span(4,20)]),(2,[span(3,25,4)]),(3,[span(9,12,6)])]
        actual=self.assert_parity(entries,chunks)
        self.assertFalse(actual.used_reference)
        self.assertEqual(actual.overlap_cells,22)
        entries[2]['overrides']=['two']
        self.assert_parity(entries,chunks)

    def test_ambiguous_duplicate_and_shadowed_same_priority_use_reference(self):
        for same_owner in (False,True):
            entries=[entry('a',1),entry('b',1),entry('top',2,('a','b'))]
            lower=[(0,[span(2,10)]),(1,[span(4,8,2 if same_owner else 3,'owner' if same_owner else 'other')])]
            self.assert_parity(entries,lower)
            actual=self.assert_parity(entries,lower+[(2,[span(2,10,6)])])
            self.assertTrue(actual.used_reference)
            self.assertEqual(actual.overlap_cells,8)

    def test_policy_membership_and_water_validation_errors_preserved(self):
        for allowed,code in (([1],2),(['2'],2),([2],7),([],3)):
            self.assert_parity([entry('a',1,allowed_codes=allowed)],[(0,[span(3,9,code)])])
        self.assert_parity([entry('a',1)],[(0,[span(3,9)])],values=[17,1],ends=[5,128])
        self.assert_parity([entry('a',1),entry('b',3,('a',))],
                          [(0,[span(3,10)]),(1,[span(4,8,5)])],values=[1,17,1],ends=[4,6,128])

    def test_randomized_arbitrary_layers_priorities_gaps_and_overlaps(self):
        rng=np.random.default_rng(20261108)
        for trial in range(500):
            count=int(rng.integers(0,8));labels=[f'unrelated-{i}' for i in range(count)]
            entries=[entry(label,int(rng.integers(-3,4)),
                     [other for other in labels if rng.random()<0.75]) for label in labels]
            chunks=[]
            for i in range(count):
                records=[];x=int(rng.integers(0,10))
                while x<128:
                    stop=min(128,x+int(rng.integers(1,20)))
                    records.append(span(x,stop,int(rng.integers(1,7)),f'member-{i}'))
                    x=stop+int(rng.integers(0,18))
                chunks.append((i,records))
            with self.subTest(trial=trial):self.assert_parity(entries,chunks)

    def test_randomized_multi_priority_valid_numeric_path(self):
        rng=np.random.default_rng(20261109)
        for trial in range(250):
            count=int(rng.integers(1,10));labels=[f'layer-{i}' for i in range(count)]
            priorities=rng.permutation(count).tolist()
            entries=[entry(label,priorities[i],labels) for i,label in enumerate(labels)]
            chunks=[]
            for i in range(count):
                records=[];x=int(rng.integers(0,20))
                while x<128:
                    stop=min(128,x+int(rng.integers(1,16)))
                    records.append(span(x,stop,int(rng.integers(1,7)),f'member-{i}'))
                    x=stop+int(rng.integers(0,15))
                chunks.append((i,records))
            with self.subTest(trial=trial):
                actual=self.assert_parity(entries,chunks)
                self.assertFalse(actual.used_reference)

    def test_numeric_columns_can_be_consumed_without_duplicate_tuples(self):
        columns=(np.asarray([2,6],dtype=np.uint32),np.asarray([4,9],dtype=np.uint32),
                 np.asarray([3,5],dtype=np.uint8))
        xs=np.arange(12,dtype=np.uint32)
        codes,present=reference.assignment_codes((),xs,columns=columns)
        self.assertEqual(codes.tolist(),[0,0,3,3,0,0,5,5,5,0,0,0])
        self.assertEqual(present.tolist(),[False,False,True,True,False,False,True,True,True,False,False,False])
        with patch.object(reference,'W',12):
            self.assertEqual(reference.merge_row_cuts(np.asarray([12]),assignment_columns=columns).tolist(),[0,2,4,6,9,12])
            self.assertEqual(reference.merge_row_cuts(np.asarray([12]),assignment_columns=empty_columns()).tolist(),[0,12])
        codes,present=reference.assignment_codes((),xs,columns=empty_columns())
        self.assertFalse(np.any(codes));self.assertFalse(np.any(present))


if __name__=='__main__':unittest.main()
