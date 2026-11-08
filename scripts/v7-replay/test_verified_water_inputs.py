import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from verified_water_inputs import VerifiedWaterInputs
import verified_water_inputs as capability
import shared_nearest


def encode(grid):
    offsets=[0];runs=[]
    for row in grid:
        cuts=[i for i in range(1,len(row)) if row[i]!=row[i-1]]+[len(row)]
        runs.extend(value for stop in cuts for value in (stop,row[stop-1]))
        offsets.append(len(runs)//2)
    return np.asarray(offsets,dtype='<u4').tobytes(),np.asarray(runs,dtype='<u4').tobytes()


class VerifiedWaterTests(unittest.TestCase):
    def fixture(self, root):
        specifications={}
        physical=[[17,17,1,1,17,17,17,1],[17,1,1,1,1,17,1,1],[1,1,17,17,1,1,1,1]]
        land=[[18 if code==17 else 0 for code in row] for row in physical]
        for role,grid in (('physical',physical),('land',land)):
            for kind,data in zip(('rows','runs'),encode(grid)):
                path=root/(role+'_'+kind);path.write_bytes(data)
                specifications[role+'_'+kind]={'path':path,'sha256':hashlib.sha256(data).hexdigest()}
        return specifications

    def arguments(self, specs, role):
        return [role,*[item for kind in ('rows','runs') for item in (specs[role+'_'+kind]['path'],specs[role+'_'+kind]['sha256'])],8,3]

    def test_readonly_snapshot_and_exact_existing_shore_geometry(self):
        with tempfile.TemporaryDirectory() as tmp:
            specs=self.fixture(Path(tmp));context=VerifiedWaterInputs(specs,8,3,work_root=tmp)
            with context as shared:
                physical=shared.grid(*self.arguments(specs,'physical'))
                land=shared.grid(*self.arguments(specs,'land'))
                self.assertFalse(physical[1].flags.writeable)
                with self.assertRaises(ValueError):physical[1][0]=5
                for bounds in ((0,8,0,3),(-2,5,1,3),(6,11,0,2)):
                    actual=shared.shore_index.centers_for_crop(bounds,45.,[18])
                    expected=shared_nearest.centers_for_crop(physical,land,bounds,8,3,45.,[18])
                    for key in expected:np.testing.assert_array_equal(actual[key],expected[key])
            with self.assertRaisesRegex(RuntimeError,'not active'):context.grid(*self.arguments(specs,'physical'))
            with self.assertRaisesRegex(RuntimeError,'cannot be reused'):context.__enter__()

    def test_multiple_threads_share_only_readonly_arrays_and_crop_state(self):
        from concurrent.futures import ThreadPoolExecutor
        with tempfile.TemporaryDirectory() as tmp:
            specs=self.fixture(Path(tmp))
            with VerifiedWaterInputs(specs,8,3,work_root=tmp) as shared:
                expected=shared.shore_index.centers_for_crop((-2,5,0,3),45.,[18])
                def read(_):
                    grid=shared.grid(*self.arguments(specs,'physical'))
                    self.assertFalse(grid[1].flags.writeable)
                    return shared.shore_index.centers_for_crop((-2,5,0,3),45.,[18])
                with ThreadPoolExecutor(max_workers=2) as pool:
                    for actual in pool.map(read,range(12)):
                        for key in expected:np.testing.assert_array_equal(actual[key],expected[key])

    def test_wrong_path_pin_grid_or_role_is_never_reused(self):
        with tempfile.TemporaryDirectory() as tmp:
            specs=self.fixture(Path(tmp))
            with VerifiedWaterInputs(specs,8,3,work_root=tmp) as shared:
                for at,value in ((0,'other'),(1,Path(tmp)/'other'),(2,'0'*64),(5,16)):
                    arguments=self.arguments(specs,'physical');arguments[at]=value
                    with self.assertRaisesRegex(ValueError,'mismatch'):shared.grid(*arguments)

    def test_relative_parent_segments_refer_to_the_same_bound_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);specs=self.fixture(root);(root/'nested').mkdir()
            specs['physical_rows']['path']=root/'nested/../physical_rows'
            with VerifiedWaterInputs(specs,8,3,work_root=tmp) as shared:
                a=shared.grid(*self.arguments(specs,'physical'))
                arguments=self.arguments(specs,'physical');arguments[1]=root/'physical_rows'
                self.assertIs(a[0],shared.grid(*arguments)[0])

    def test_foreign_cached_helper_fails_before_reading_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            specs=self.fixture(Path(tmp))
            for module in (capability.coastal_shore_index,capability.coastal_shore_index.shore,capability.snapshot_input):
                with self.subTest(module=module.__name__),patch.object(module,'__file__',str(Path(tmp)/'foreign.py')):
                    context=VerifiedWaterInputs(specs,8,3,work_root=tmp)
                    with patch.object(capability,'visit_pinned',side_effect=AssertionError('must fail before snapshots')):
                        with self.assertRaisesRegex(ImportError,'outside the selected checkout'):
                            with context:self.fail('entered')

    def test_explicit_workspace_ignores_cached_default_temp_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);specs=self.fixture(root);scratch=root/'scratch';scratch.mkdir()
            original=capability.snapshot_input.tempfile.TemporaryDirectory
            directories=[]
            def observed(*args,**kwargs):
                directories.append(Path(kwargs['dir']))
                return original(*args,**kwargs)
            with (patch.object(capability.snapshot_input.tempfile,'tempdir',str(root/'must-not-be-used')),
                  patch.object(capability.snapshot_input.tempfile,'TemporaryDirectory',side_effect=observed)):
                with VerifiedWaterInputs(specs,8,3,work_root=scratch):pass
            self.assertEqual(directories,[scratch]*4)
            self.assertFalse(list(scratch.iterdir()))

    def test_changed_original_does_not_change_snapshot_and_fails_exit(self):
        with tempfile.TemporaryDirectory() as tmp:
            specs=self.fixture(Path(tmp));context=VerifiedWaterInputs(specs,8,3,work_root=tmp)
            with self.assertRaisesRegex(ValueError,'SHA-256 mismatch'):
                with context as shared:
                    grid=shared.grid(*self.arguments(specs,'physical'));expected=grid[1].copy()
                    path=specs['physical_runs']['path'];path.write_bytes(bytes(path.stat().st_size))
                    np.testing.assert_array_equal(grid[1],expected)
            self.assertEqual(context._state,'closed')
            self.assertFalse(context._arrays)

    def test_corrupt_pin_and_invalid_offsets_fail_before_capability(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);specs=self.fixture(root);specs['land_runs']['sha256']='0'*64
            with self.assertRaisesRegex(ValueError,'SHA-256 mismatch'):
                with VerifiedWaterInputs(specs,8,3,work_root=tmp):self.fail('entered')
            specs=self.fixture(root);path=specs['land_rows']['path'];path.write_bytes(np.asarray([0,1,1,4],dtype='<u4').tobytes())
            specs['land_rows']['sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
            with self.assertRaisesRegex(ValueError,'RLE offsets'):
                with VerifiedWaterInputs(specs,8,3,work_root=tmp):self.fail('entered')

    def test_symlink_source_is_rejected_and_body_error_is_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);specs=self.fixture(root)
            with self.assertRaisesRegex(RuntimeError,'original error'):
                with VerifiedWaterInputs(specs,8,3,work_root=tmp):
                    specs['physical_runs']['path'].write_bytes(b'bad')
                    raise RuntimeError('original error')
            specs=self.fixture(root);link=root/'alias';link.symlink_to(specs['physical_runs']['path'])
            specs['physical_runs']['path']=link
            with self.assertRaises(OSError):
                with VerifiedWaterInputs(specs,8,3,work_root=tmp):self.fail('entered')


if __name__=='__main__':unittest.main()
