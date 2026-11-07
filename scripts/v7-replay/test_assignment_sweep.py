"""Compare optimized span groups with an independent half-open event oracle."""
import unittest
import numpy as np
import compose_full_water_grid as compose


def reference(spans):
    cuts=sorted({edge for s in spans for edge in s[1:3]})
    out=[];conflicts=[]
    for a,b in zip(cuts,cuts[1:]):
        active=[s for s in spans if s[1]<=a<s[2]]
        if not active:continue
        winner=max(active,key=lambda s:s[8])
        out.append((a,b,winner[3],winner[4],winner[5]))
        conflicts.extend((a,b,s[5],winner[5]) for s in active if s is not winner)
    return out,conflicts


class AssignmentSweepTests(unittest.TestCase):
    def span(self,a,b,priority=1,*,member=None,layer=None,overrides=()):
        layer=layer or f'layer-{priority}';member=member or f'member-{priority}'
        return (0,a,b,1,'rule',member,None,None,priority,layer,set(overrides))

    def test_random_isolated_nested_touching_and_overlapping_groups(self):
        rng=np.random.default_rng(94072)
        for _ in range(500):
            count=int(rng.integers(1,50));spans=[]
            for i in range(count):
                a=int(rng.integers(0,256));b=min(256,a+int(rng.integers(1,60)))
                spans.append(self.span(a,b,i,overrides=[f'layer-{j}' for j in range(i)]))
            rng.shuffle(spans)
            actual,conflicts=compose.choose_assignments(spans,0,np.array([256]),np.array([1]))
            expected,expected_conflicts=reference(spans)
            self.assertEqual(actual,expected)
            self.assertEqual(sorted(conflicts),sorted(expected_conflicts))

    def test_explicit_overlap_failures_are_preserved(self):
        for spans,message in (
            ([self.span(0,5),self.span(3,9,member='other')],'ambiguous same-priority'),
            ([self.span(0,5),self.span(3,9)],'duplicate same-priority'),
            ([self.span(0,5,1),self.span(3,9,2)],'undeclared priority override')):
            with self.subTest(message=message),self.assertRaisesRegex(ValueError,message):
                compose.choose_assignments(spans,0,np.array([10]),np.array([1]))

    def test_random_two_priority_bands_keep_every_source_cut_and_override(self):
        rng=np.random.default_rng(25011)
        for _ in range(300):
            spans=[]
            for priority in (0,1):
                x=0
                while x<256:
                    x+=int(rng.integers(0,12))
                    if x>=256:break
                    stop=min(256,x+int(rng.integers(1,36)))
                    spans.append(self.span(x,stop,priority,member=f'{priority}-{x}',
                                           layer=f'layer-{priority}',overrides=['layer-0']))
                    x=stop
            actual,conflicts=compose.choose_assignments(spans,0,np.array([256]),np.array([1]))
            expected,expected_conflicts=reference(spans)
            self.assertEqual(actual,expected)
            self.assertEqual(sorted(conflicts),sorted(expected_conflicts))

    def test_physical_validation_for_isolated_and_overlap_spans(self):
        cases=[([self.span(0,2),self.span(4,6)],np.array([4,8]),np.array([1,17])),
               ([self.span(2,6,1),self.span(4,8,2,overrides=['layer-1'])],
                np.array([4,8]),np.array([1,17]))]
        for spans,ends,values in cases:
            with self.assertRaisesRegex(ValueError,'physical land/nonwater'):
                compose.choose_assignments(spans,0,ends,values)

    def test_touching_same_priority_is_not_an_overlap(self):
        spans=[self.span(0,4),self.span(4,8)]
        result,conflicts=compose.choose_assignments(spans,0,np.array([8]),np.array([1]))
        self.assertEqual([s[:2] for s in result],[(0,4),(4,8)])
        self.assertEqual(conflicts,[])

    def test_two_band_permissions_and_arbitrary_integer_priorities(self):
        low=[self.span(0,5,layer='a'),self.span(5,10,layer='b')]
        high=[self.span(1,4,2**80,layer='high-a',overrides=['a']),
              self.span(6,9,2**80,layer='high-b',overrides=['b'])]
        actual,conflicts=compose.choose_assignments(low+high,0,np.array([10]),np.array([1]))
        expected,expected_conflicts=reference(low+high)
        self.assertEqual(actual,expected);self.assertEqual(sorted(conflicts),sorted(expected_conflicts))
        high=[self.span(1,9,2**80,layer='high-a',overrides=['a'])]
        with self.assertRaisesRegex(ValueError,'undeclared priority override'):
            compose.choose_assignments(low+high,0,np.array([10]),np.array([1]))


if __name__=='__main__':unittest.main()
