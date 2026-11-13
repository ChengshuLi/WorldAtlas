"""Check suite dependencies and GitHub's shallow PR merge-checkout behavior."""

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from select_tests import select_tests

ALL = {'python', 'imports', 'map', 'releases', 'sql', 'web'}
SCRIPT = Path(__file__).with_name('select_tests.py').resolve()


class SelectionTests(unittest.TestCase):
    def test_changed_paths_select_their_consumers(self):
        cases = {
            'README.md': set(),
            'docs/guide.md': set(),
            '.github/scripts/README.md': set(),
            '.gitignore': set(),
            'scripts/source-imports/osm/build_boundary.py': {'python', 'imports'},
            'scripts/source-imports/atlas_sources/catalog.py': {'python', 'imports', 'map', 'releases'},
            'scripts/map-build/map_build/build.py': {'python', 'map', 'releases'},
            'scripts/map-releases/manage_release.py': {'python', 'releases', 'web'},
            'database/migrations/001_initial_schema.sql': ALL - {'web'},
            'database/tests/entity_registry.sql': ALL - {'web'},
            'environment.yml': ALL - {'web'},
            'web/viewer/app.js': {'web'},
            'web/viewer/config.json': {'python', 'releases', 'web'},
            'package.json': {'web'},
            'package-lock.json': {'web'},
            'wrangler.jsonc': {'web'},
            '.github/workflows/ci.yml': ALL,
            '.github/scripts/select_tests.py': ALL,
            '.github/scripts/test_select_tests.py': ALL,
        }
        for path, expected in cases.items():
            with self.subTest(path=path):
                self.assertEqual({name for name, run in select_tests([path]).items() if run}, expected)
        combined = select_tests(['README.md', 'web/viewer/app.js', 'scripts/map-build/a.py'])
        self.assertEqual({name for name, run in combined.items() if run}, {'python', 'map', 'releases', 'web'})
        self.assertFalse(any(select_tests([]).values()))

    def run_selector(self, directory, event):
        output = directory.parent / 'outputs.txt'
        output.write_text('previous=value\n')
        subprocess.run([sys.executable, str(SCRIPT)], cwd=directory, check=True,
                       env=dict(os.environ, EVENT=event, GITHUB_OUTPUT=str(output)))
        lines = output.read_text().splitlines()
        self.assertEqual(lines[0], 'previous=value')
        self.assertEqual(len(lines), 7)
        values = dict(line.split('=', 1) for line in lines[1:])
        self.assertEqual(set(values), ALL)
        self.assertLessEqual(set(values.values()), {'true', 'false'})
        return {name for name, value in values.items() if value == 'true'}

    def test_manual_run_selects_everything_without_git_history(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp) / 'no-repository'
            directory.mkdir()
            self.assertEqual(self.run_selector(directory, 'workflow_dispatch'), ALL)

    def test_shallow_merge_includes_earlier_edits_and_both_sides_of_moves(self):
        with tempfile.TemporaryDirectory() as temp:
            repository = Path(temp) / 'repository'
            repository.mkdir()

            def git(*args):
                return subprocess.check_output(['git', *args], cwd=repository, stderr=subprocess.STDOUT)

            def write(name, text):
                path = repository / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text)

            git('init', '-b', 'main')
            git('config', 'user.name', 'CI test')
            git('config', 'user.email', 'ci@example.invalid')
            write('scripts/map-build/moved.py', 'print("move me")\n')
            write('README.md', 'base\n')
            git('add', '.')
            git('commit', '-m', 'base')
            git('checkout', '-b', 'feature')
            (repository / 'scripts/source-imports').mkdir()
            git('mv', 'scripts/map-build/moved.py', 'scripts/source-imports/moved.py')
            git('commit', '-m', 'move between test areas')
            write('web/viewer/app.js', '// later edit\n')
            git('add', '.')
            git('commit', '-m', 'later edit')
            git('checkout', 'main')
            write('README.md', 'target branch changed\n')
            git('add', '.')
            git('commit', '-m', 'target edit')
            git('merge', '--no-ff', 'feature', '-m', 'PR merge')
            checkout = Path(temp) / 'checkout'
            git('clone', '--depth', '2', repository.as_uri(), str(checkout))
            self.assertTrue((checkout / '.git/shallow').exists())
            self.assertEqual(self.run_selector(checkout, 'pull_request'), ALL - {'sql'})


if __name__ == '__main__':
    unittest.main()
