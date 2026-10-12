"""Trusted-base, isolated standard-library startup for selected package reuse."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess


def need(value, message):
    if not value:
        raise ValueError(message)


def main():
    root = Path.cwd()
    base = os.environ['SELECTED_PACKAGE_TRUSTED_BASE']
    need(re.fullmatch('[a-f0-9]{40}', base), 'Exact trusted base required')
    for key in ('NODE_OPTIONS', 'NODE_PATH', 'LD_PRELOAD', 'LD_LIBRARY_PATH', 'DYLD_INSERT_LIBRARIES'):
        need(not os.environ.get(key), 'Startup injection is not admitted')
    env = dict(os.environ, GIT_NO_REPLACE_OBJECTS='1', GIT_CONFIG_NOSYSTEM='1',
               GIT_CONFIG_GLOBAL='/dev/null', GIT_NO_LAZY_FETCH='1', GIT_TERMINAL_PROMPT='0')
    for key in list(env):
        if key in ('GH_TOKEN', 'GITHUB_TOKEN') or key.startswith('GIT_CONFIG_') and key not in ('GIT_CONFIG_NOSYSTEM', 'GIT_CONFIG_GLOBAL'):
            env.pop(key)

    def object_body(kind, oid):
        need(re.fullmatch('[a-f0-9]{40}', oid), 'Git object identity required')
        raw = subprocess.check_output(['git', '--no-replace-objects', 'cat-file', kind, oid], env=env, timeout=20)
        need(len(raw) <= 32 * 1024 * 1024 and hashlib.sha1((kind + ' ' + str(len(raw)) + '\0').encode() + raw).hexdigest() == oid,
             'Trusted Git object body differs')
        return raw

    commit = object_body('commit', base)
    tree_oid = re.search(rb'^tree ([a-f0-9]{40})\n', commit).group(1).decode()
    trees = {}

    def tree(oid):
        if oid not in trees:
            raw = object_body('tree', oid)
            rows, at = {}, 0
            while at < len(raw):
                end = raw.index(b'\0', at)
                mode, name = raw[at:end].split(b' ', 1)
                name = name.decode()
                need(name not in ('', '.', '..') and '/' not in name and name not in rows, 'Ordinary Git tree required')
                rows[name] = (mode.decode(), raw[end + 1:end + 21].hex())
                at = end + 21
            trees[oid] = rows
        return trees[oid]

    def entry(name):
        oid = tree_oid
        parts = name.split('/')
        for index, part in enumerate(parts):
            row = tree(oid).get(part)
            if row is None:
                return None
            if index == len(parts) - 1:
                return row
            need(row[0] == '40000', 'Ordinary source parent required')
            oid = row[1]

    def actual(name):
        at = root
        for part in name.split('/'):
            need(part not in ('', '.', '..'), 'Safe source path required')
            at = at / part
            need(not at.is_symlink(), 'Source link not admitted')
        need(at.is_file(), 'Actual source member missing')
        return at

    def verified(name):
        row = entry(name)
        need(row and row[0] in ('100644', '100755'), 'Trusted source member missing')
        raw = object_body('blob', row[1])
        file = actual(name)
        need(file.read_bytes() == raw and ('100755' if file.stat().st_mode & 0o111 else '100644') == row[0], 'Actual source differs from trusted base')
        return raw

    node = Path(shutil.which('node')).absolute()
    cache = Path(os.environ['RUNNER_TOOL_CACHE']).resolve()
    need(node.is_file() and not node.is_symlink() and node.resolve().is_relative_to(cache / 'node'), 'Verified setup-node executable required')
    pending, seen, external = ['scripts/assemble-selected-package.mjs'], set(), set()
    while pending:
        name = pending.pop()
        if name in seen:
            continue
        seen.add(name)
        need(len(seen) <= 512, 'Bounded assembly closure required')
        raw = verified(name)
        scope = PurePosixPath(name).parent
        while True:
            if str(scope) != '.':
                nested = root / scope / 'node_modules'
                need(not nested.exists() and not nested.is_symlink(), 'Unexpected nested module resolution directory')
            package = str(scope / 'package.json')
            if entry(package):
                verified(package)
            else:
                need(not (root / package).exists() and not (root / package).is_symlink(), 'Unexpected Node package scope')
            if str(scope) == '.':
                break
            scope = scope.parent
        # Parse without linking/evaluating in a credential-free builtin-only
        # child. Node's actual parser handles comments, assertions and multiline
        # syntax; a source regex is not execution-closure authority.
        parser = "import vm from 'node:vm';import fs from 'node:fs';const module=new vm.SourceTextModule(fs.readFileSync(0,'utf8'));process.stdout.write(JSON.stringify(module.dependencySpecifiers));"
        dependencies = json.loads(subprocess.check_output([str(node), '--experimental-vm-modules', '--input-type=module', '-e', parser],
            input=raw, env=env, stderr=subprocess.PIPE, timeout=20))
        for spec in dependencies:
            if spec.startswith('.'):
                pending.append(os.path.normpath(str(PurePosixPath(name).parent / spec)))
            elif not spec.startswith('node:'):
                external.add(spec)
    need(not external, 'External credential-bearing startup module is not admitted')
    verified('package-lock.json')
    os.execve(node, [str(node), 'scripts/assemble-selected-package.mjs'], os.environ)


if __name__ == '__main__':
    main()
