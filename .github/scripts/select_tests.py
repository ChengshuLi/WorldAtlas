"""Choose CI suites from the complete PR diff and expose GitHub job outputs."""

import os
from pathlib import Path
import subprocess


def select_tests(paths, event='pull_request'):
    paths = [path for path in paths if not path.endswith('.md')]
    all_checks = event == 'workflow_dispatch' or any(
        path.startswith(('.github/workflows/', '.github/scripts/')) for path in paths
    )

    def changed(*prefixes):
        return any(path.startswith(prefixes) for path in paths)

    environment = 'environment.yml' in paths
    database = changed('database/')
    shared = changed('scripts/source-imports/atlas_sources/')
    imports = all_checks or environment or database or changed('scripts/source-imports/')
    map_tests = all_checks or environment or database or shared or changed('scripts/map-build/')
    releases = (
        all_checks or environment or database or shared or map_tests
        or 'web/viewer/config.json' in paths or changed('scripts/map-releases/')
    )
    sql = all_checks or environment or database
    web = (
        all_checks or changed('web/', 'scripts/map-releases/')
        or any(path in paths for path in ('package.json', 'package-lock.json', 'wrangler.jsonc'))
    )
    return dict(python=imports or map_tests or releases or sql,
                imports=imports, map=map_tests, releases=releases, sql=sql, web=web)


def main():
    event = os.environ['EVENT']
    paths = []
    if event != 'workflow_dispatch':
        # Checkout uses the PR merge commit; its first parent is the target branch.
        # Disable rename detection so both sides of a move select their tests.
        paths = subprocess.check_output(
            ['git', 'diff', '--no-renames', '--name-only', 'HEAD^', 'HEAD'], text=True
        ).splitlines()
    with Path(os.environ['GITHUB_OUTPUT']).open('a') as output:
        for name, run in select_tests(paths, event).items():
            output.write(f'{name}={str(run).lower()}\n')


if __name__ == '__main__':
    main()
