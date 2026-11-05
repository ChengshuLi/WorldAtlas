"""Bounded checks for isolation of the Caucasus assembly subprocesses."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import caucasus_seed_gate as gate
import caucasus_source_assembly as assembly
import caucasus_stage2_binding as binding


class ProcessIsolation(unittest.TestCase):
    def test_assembler_children_ignore_python_environment_and_user_site(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            hostile = root / 'hostile'
            hostile.mkdir()
            marker = root / 'startup-ran'
            (hostile / 'sitecustomize.py').write_text('open(%r,"w").write("ran")\n' % str(marker))
            # Fake only the selectors, retaining real subprocess startup and the
            # actual assembler. Both child processes must enter isolated mode.
            (root / 'caucasus_compact_selectors.py').write_text(
                "import json,sys\nassert sys.flags.isolated and not sys.flags.no_site\n"
                "assert %r not in sys.path\n" % str(hostile) +
                "open(sys.argv[sys.argv.index('--output')+1],'w').write('{}')\n")
            (root / 'caucasus_selector_replay.py').write_text(
                "import json,sys\nassert sys.flags.isolated and not sys.flags.no_site\n"
                "assert %r not in sys.path\n" % str(hostile) +
                "json.dump({'comparison': {'possible_changed_centers':0,"
                "'maximum_wgs84_vertex_displacement_m':0}, 'geometry':{},"
                "'geometry_sha256':'test'},open(sys.argv[sys.argv.index('--output')+1],'w'))\n")
            hydro = root / 'hydro.zip'
            with zipfile.ZipFile(hydro, 'w') as archive:
                archive.writestr('hybas_eu_lev12_v1c.shp', b'fixture')
            author, recipe, selected, output = (root / n for n in ('author', 'recipe', 'selected', 'output'))
            for path in (author, recipe, selected):
                path.write_text('{}')
            args = ['assembler', '--decisions', str(recipe), '--decisions-sha256', assembly.sha(recipe),
                    '--hydro-zip', str(hydro), '--author', str(author), '--selected', str(selected),
                    '--output', str(output)]
            env = {'PYTHONPATH': str(hostile), 'PYTHONUSERBASE': str(hostile)}
            with patch.object(assembly, 'HERE', root), patch.object(assembly, 'HYDRO_ZIP_SHA', assembly.sha(hydro)), \
                 patch.object(assembly, 'AUTHOR_SHA', assembly.sha(author)), patch.object(sys, 'argv', args), \
                 patch.dict(os.environ, env):
                assembly.main()
            self.assertEqual(json.loads(output.read_text()), {})
            self.assertFalse(marker.exists())

    def test_binding_bootstrap_uses_isolation_and_pinned_sibling_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'sibling_fixture.py').write_text('VALUE = 42\n')
            (root / 'caucasus_seed_gate.py').write_text(
                "import sibling_fixture,sys\nassert sys.flags.isolated\nassert sibling_fixture.VALUE == 42\n")
            request = root / 'request'
            request.write_text('{}')
            with patch.object(binding, 'HERE', root), patch.object(binding, 'verify_config'), \
                 patch.object(binding, 'validate_direct_request'):
                pin = {'path': 'unused', 'sha256': '0' * 64}
                binding.run_seed({'recipe': pin, 'hydro': pin, 'author': pin}, request,
                                 gate.digest(request), root, '0' * 64, root, root, root / 'report')


if __name__ == '__main__':
    unittest.main()
