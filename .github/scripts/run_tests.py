"""Run the installed Python suites concurrently, each with isolated database fixtures."""

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import time
import traceback

import psycopg
from psycopg import sql
from psycopg.conninfo import make_conninfo
from worldatlas.source_imports.contracts import database_checks

import worldatlas

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = Path(worldatlas.__file__).resolve().parent
SUITES = {
    'database': True,
    'source_imports': True,
    'map_build': True,
    'map_releases': False,
}


def run_suite(name, directory, databases):
    started = time.monotonic()
    log = directory / (name + '.log')
    with log.open('w') as output:
        try:
            if name == 'database':
                with psycopg.connect(databases[name], autocommit=True) as database:
                    for check in sorted((ROOT / 'database/tests').glob('*.sql')):
                        database.execute(check.read_text())
                        print('PASS', check.name, file=output)
                code = 0
            else:
                env = dict(os.environ, WORLDATLAS_TEST_DATABASE_URL=databases.get(name, ''))
                code = subprocess.run(
                    [sys.executable, '-m', 'unittest', 'discover',
                     '-s', str(PACKAGE / name), '-t', str(PACKAGE.parent)],
                    env=env, cwd=directory, stdout=output, stderr=subprocess.STDOUT,
                ).returncode
        except Exception:
            traceback.print_exc(file=output)
            code = 1
    return name, code, time.monotonic() - started, log


@contextmanager
def test_databases(selected, enabled):
    if not enabled or not any(SUITES[name] for name in selected):
        yield {}
        return

    image = subprocess.check_output(
        ['docker', 'build', '--quiet', str(ROOT / 'database/tests')], text=True
    ).strip()
    container = subprocess.check_output(
        ['docker', 'run', '--detach', '--publish', '127.0.0.1::5432',
         '--env', 'POSTGRES_HOST_AUTH_METHOD=trust',
         '--volume', f'{ROOT / "database"}:/worldatlas-database:ro', image],
        text=True,
    ).strip()
    try:
        address = subprocess.check_output(
            ['docker', 'port', container, '5432/tcp'], text=True
        ).strip()
        port = address.rsplit(':', 1)[1]
        base = make_conninfo(host='127.0.0.1', port=port, user='postgres',
                             dbname='postgres', connect_timeout=2)
        deadline = time.monotonic() + 20
        while True:
            try:
                server = psycopg.connect(base, autocommit=True)
                break
            except psycopg.OperationalError:
                if time.monotonic() >= deadline:
                    subprocess.run(['docker', 'logs', container], check=False)
                    raise
                time.sleep(0.2)
        databases = {}
        with server:
            for name in selected:
                if not SUITES[name]:
                    continue
                server.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)))
                subprocess.run(
                    ['docker', 'exec', container, 'psql', '-Xq', '-U', 'postgres',
                     '-d', name, '-f', '/worldatlas-database/schema.sql'],
                    check=True,
                )
                databases[name] = make_conninfo(base, dbname=name)
        yield databases
    finally:
        subprocess.run(['docker', 'rm', '--force', '--volumes', container],
                       stdout=subprocess.DEVNULL, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--suite', choices=SUITES, help='run one suite; defaults to all suites')
    parser.add_argument('--without-database', action='store_true',
                        help='run Python tests that can run without PostgreSQL')
    args = parser.parse_args()
    if args.without_database and args.suite == 'database':
        parser.error('the database suite requires PostgreSQL')
    if (ROOT / "database/schema/construction_contracts.sql").read_text() != database_checks():
        parser.error("construction checks are stale; regenerate database/schema/construction_contracts.sql")
    selected = (args.suite,) if args.suite else tuple(
        name for name in SUITES if name != 'database' or not args.without_database
    )
    with (
        tempfile.TemporaryDirectory(prefix='worldatlas-tests-') as temp,
        test_databases(selected, not args.without_database) as databases,
    ):
        directory = Path(temp)
        started = time.monotonic()
        failed = False
        with ThreadPoolExecutor(max_workers=len(selected)) as executor:
            futures = [executor.submit(run_suite, name, directory, databases) for name in selected]
            for future in as_completed(futures):
                name, code, elapsed, log = future.result()
                failed |= code != 0
                print(f'\n{name}: {"FAILED" if code else "passed"} ({elapsed:.2f}s)', flush=True)
                print(log.read_text(), end='', flush=True)
        print(f'\nAll suites finished in {time.monotonic() - started:.2f}s wall time.', flush=True)
        return int(failed)


if __name__ == '__main__':
    sys.exit(main())
