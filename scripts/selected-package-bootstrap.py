"""Trusted-base, isolated standard-library startup for selected package reuse."""
import hashlib
import base64
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import urllib.request


def need(value, message):
    if not value:
        raise ValueError(message)



def main():
    root = Path.cwd()
    base = os.environ['SELECTED_PACKAGE_TRUSTED_BASE']
    need(re.fullmatch('[a-f0-9]{40}', base), 'Exact trusted base required')
    for key in ('NODE_OPTIONS', 'NODE_PATH', 'LD_PRELOAD', 'DYLD_INSERT_LIBRARIES'):
        need(not os.environ.get(key), 'Startup injection is not admitted')
    env = dict(os.environ, GIT_NO_REPLACE_OBJECTS='1', GIT_CONFIG_NOSYSTEM='1',
               GIT_CONFIG_GLOBAL='/dev/null', GIT_NO_LAZY_FETCH='1', GIT_TERMINAL_PROMPT='0')
    for key in list(env):
        # setup-python supplies LD_LIBRARY_PATH for its own interpreter. Never
        # propagate that loader search path to Git, the parser or credential-bearing Node.
        if key in ('GH_TOKEN', 'GITHUB_TOKEN', 'LD_LIBRARY_PATH') or key.startswith('GIT_CONFIG_') and key not in ('GIT_CONFIG_NOSYSTEM', 'GIT_CONFIG_GLOBAL'):
            env.pop(key)

    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *_):
            raise ValueError('Git metadata redirects are not admitted')
    opener = urllib.request.build_opener(NoRedirect())
    def api(route):
        request = urllib.request.Request('https://api.github.com/repos/ChengshuLi/WorldAtlas' + route,
            headers={'Authorization': 'Bearer ' + os.environ['GH_TOKEN'], 'Accept': 'application/vnd.github+json'})
        with opener.open(request, timeout=30) as response:
            raw = response.read(8 * 1024 * 1024 + 1)
        need(len(raw) <= 8 * 1024 * 1024, 'Bounded Git metadata required')
        return json.loads(raw)

    def object_body(kind, oid):
        need(re.fullmatch('[a-f0-9]{40}', oid), 'Git object identity required')
        local = subprocess.run(['git', '--no-replace-objects', 'cat-file', kind, oid], env=env,
            timeout=20, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if local.returncode == 0:
            raw = local.stdout
        elif kind == 'blob':
            value = api('/git/blobs/' + oid)
            need(value.get('sha') == oid and value.get('encoding') == 'base64', 'Authenticated blob required')
            raw = base64.b64decode(''.join(value['content'].split()), validate=True)
            need(len(raw) == value['size'], 'Complete authenticated blob required')
        else:
            need(kind == 'tree', 'Only missing tree/blob metadata may be acquired')
            value = api('/git/trees/' + oid)
            need(value.get('sha') == oid and value.get('truncated') is False, 'Complete authenticated tree required')
            rows = []
            for row in value['tree']:
                name, mode, child = row['path'], row['mode'], row['sha']
                need(name not in ('', '.', '..') and '/' not in name and '\0' not in name and re.fullmatch('[a-f0-9]{40}', child), 'Safe tree member required')
                need(mode in ('040000', '100644', '100755', '120000', '160000'), 'Known Git tree mode required')
                encoded = name.encode()
                rows.append((encoded + (b'/' if mode == '040000' else b'\0'), mode.lstrip('0').encode() + b' ' + encoded + b'\0' + bytes.fromhex(child)))
            raw = b''.join(body for _, body in sorted(rows))
        need(len(raw) <= 32 * 1024 * 1024 and hashlib.sha1((kind + ' ' + str(len(raw)) + '\0').encode() + raw).hexdigest() == oid,
             'Trusted Git object body differs')
        return raw

    # A candidate-only shallow checkout need not contain its PR base. The
    # authenticated API binds the base tree; missing metadata stays in memory.
    commit = api('/git/commits/' + base)
    need(commit.get('sha') == base and re.fullmatch('[a-f0-9]{40}', commit.get('tree', {}).get('sha', '')), 'Authenticated trusted-base commit required')
    tree_oid = commit['tree']['sha']
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

    if os.environ.get('SELECTED_PACKAGE_PREFLIGHT') == 'install':
        # Dispatch accepts an exact source commit, not a selected-data PR
        # classification. Authenticate installer inputs before any candidate
        # npm/pip command can alter a runtime used by the later token step.
        roots = {name: row for name, row in tree(tree_oid).items() if row[0] != '40000'}
        current = subprocess.check_output(['git', '--no-replace-objects', 'ls-tree', '-z', 'HEAD'], env=env)
        current_roots = {}
        for line in current.split(b'\0'):
            if not line: continue
            header, name = line.split(b'\t', 1)
            mode, kind, oid = header.decode().split()
            if kind != 'tree': current_roots[name.decode()] = (mode, oid)
        need(current_roots == roots, 'Installer root programme differs from trusted base')
        ordinary_roots = {file.name for file in root.iterdir() if file.name != '.git' and (file.is_file() or file.is_symlink())}
        need(ordinary_roots == set(roots), 'Unexpected installer root configuration')
        for name in roots: verified(name)
        package = json.loads(verified('package.json'))
        lifecycle = {'preinstall', 'install', 'postinstall', 'prepublish', 'preprepare', 'prepare', 'postprepare'}
        need(not lifecycle.intersection(package.get('scripts', {})), 'Project installer hooks require explicit programme review')
        # Root inputs (including lock, requirements and any npm configuration)
        # are identical. Dependency install scripts are those of the trusted
        # lock; there is no candidate project lifecycle code to execute.
        return

    node = Path(shutil.which('node')).absolute()
    cache = Path(os.environ['RUNNER_TOOL_CACHE']).resolve()
    need(node.is_file() and not node.is_symlink() and node.resolve().is_relative_to(cache / 'node'), 'Verified setup-node executable required')
    entry_point = os.environ.get('SELECTED_PACKAGE_ENTRY_POINT', 'scripts/assemble-selected-package.mjs')
    need(entry_point == 'scripts/assemble-selected-package.mjs', 'Unknown trusted package entry point')
    pending, seen, external = [entry_point], set(), set()
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
    verified('scripts/extract-package-output.py')
    launch_env = dict(env, GH_TOKEN=os.environ['GH_TOKEN'])
    os.execve(node, [str(node), entry_point], launch_env)


if __name__ == '__main__':
    main()
