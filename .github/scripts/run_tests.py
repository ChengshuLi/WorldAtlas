"""Run the installed Python suites concurrently, each with isolated database fixtures."""

from concurrent.futures import ThreadPoolExecutor, as_completed
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


def main():
    # Unix socket paths must stay short on macOS; Python fixtures use their
    # ordinary temporary directories independently of this server directory.
    with tempfile.TemporaryDirectory(prefix='worldatlas-tests-', dir='/tmp') as temp:
        directory = Path(temp)
        data = directory / 'data'
        subprocess.run(['initdb', '-D', str(data), '-U', 'postgres', '-A', 'trust',
                        '--no-locale', '--encoding=UTF8'], check=True)
        subprocess.run(['pg_ctl', '-D', str(data), '-l', str(directory / 'postgres.log'),
                        '-o', f"-k {directory} -p 5432 -c listen_addresses=''", '-w', 'start'],
                       check=True)
        try:
            databases = {}
            base = make_conninfo(user='postgres', dbname='postgres', host=str(directory))
            schema = (ROOT / 'database/migrations/001_initial_schema.sql').read_text()
            with psycopg.connect(base, autocommit=True) as server:
                for name, needs_database in SUITES.items():
                    if not needs_database:
                        continue
                    server.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)))
                    url = make_conninfo(base, dbname=name)
                    with psycopg.connect(url, autocommit=True) as database:
                        database.execute(schema)
                    databases[name] = url
            started = time.monotonic()
            failed = False
            with ThreadPoolExecutor(max_workers=len(SUITES)) as executor:
                futures = [executor.submit(run_suite, name, directory, databases) for name in SUITES]
                for future in as_completed(futures):
                    name, code, elapsed, log = future.result()
                    failed |= code != 0
                    print(f'\n{name}: {"FAILED" if code else "passed"} ({elapsed:.2f}s)', flush=True)
                    print(log.read_text(), end='', flush=True)
            print(f'\nAll suites finished in {time.monotonic() - started:.2f}s wall time.', flush=True)
            return int(failed)
        finally:
            subprocess.run(['pg_ctl', '-D', str(data), '-m', 'fast', '-w', 'stop'], check=True)


if __name__ == '__main__':
    sys.exit(main())
