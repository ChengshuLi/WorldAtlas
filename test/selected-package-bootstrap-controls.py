#!/usr/bin/env python3
"""Offline actual-module tests: python3 this.py /path/to/selected-package-bootstrap.py."""
import base64
import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from unittest.mock import patch
import urllib.error
import urllib.request

BOOTSTRAP = Path(sys.argv.pop(1)).resolve()
SOURCE_ROOT = Path(os.environ.get('WORLDATLAS_TEST_SOURCE_ROOT', str(BOOTSTRAP.parent.parent)))
spec = importlib.util.spec_from_file_location('selected_package_bootstrap_under_test', BOOTSTRAP)
bootstrap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bootstrap)
SYSTEM_NODE = shutil.which('node')
SYSTEM_GIT = shutil.which('git')
OFFLINE_GIT_READ = subprocess.check_output

def actual_static_graph(source_root, entry_point):
    # Node parses these bodies without linking or evaluating them. This test
    # observes the true graph instead of maintaining a parallel regex allowlist.
    walker="import fs from 'node:fs';import path from 'node:path';import vm from 'node:vm';const root=process.argv[1],q=[process.argv[2]],seen=new Set();while(q.length){const n=q.pop();if(seen.has(n))continue;seen.add(n);for(const s of new vm.SourceTextModule(fs.readFileSync(path.join(root,n),'utf8')).dependencySpecifiers)if(s.startsWith('.'))q.push(path.posix.normalize(path.posix.join(path.posix.dirname(n),s)));}process.stdout.write(JSON.stringify([...seen]));"
    result=subprocess.run([SYSTEM_NODE,'--experimental-vm-modules','--input-type=module','-e',walker,str(source_root),entry_point],
                          stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=False)
    if result.returncode:
        raise AssertionError('Actual static graph could not be read: '+result.stderr.decode())
    return json.loads(result.stdout)

class StartedNode(BaseException): pass

class BootstrapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tooltemp = tempfile.TemporaryDirectory(prefix='worldatlas-bootstrap-node-')
        cls.tool = Path(cls.tooltemp.name) / 'node'
        try: os.link(SYSTEM_NODE, cls.tool)
        except OSError: shutil.copy2(SYSTEM_NODE, cls.tool)
    @classmethod
    def tearDownClass(cls): cls.tooltemp.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='worldatlas-bootstrap-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'repo'; self.root.mkdir()
        oldcwd = Path.cwd(); os.chdir(self.root); self.addCleanup(os.chdir, oldcwd)
        self.write('package.json', '{"name":"test-fixture","type":"module"}\n')
        self.write('package-lock.json', '{"packages":{}}\n')
        self.write('scripts/assemble-selected-package.mjs', "import './child.mjs';\n")
        self.write('scripts/child.mjs', "import '../coordination/deep/consumer.mjs';\nexport async function deferred(){return import('@noble/hashes/sha2.js');}\n")
        self.write('coordination/deep/consumer.mjs', "import fs from 'node:fs';\nexport const value=1;\n")
        self.git('init', '-q'); self.git('config', 'user.name', 'Bootstrap test'); self.git('config', 'user.email', 'bootstrap-test@example.invalid')
        self.git('add', '.'); self.git('commit', '-qm', 'Synthetic trusted base')
        self.base = self.git('rev-parse', 'HEAD').decode().strip()
        self.cache = Path(self.temp.name) / 'toolcache'
        self.node = self.cache / 'node/24.0.0/x64/bin/node'; self.node.parent.mkdir(parents=True)
        os.link(self.tool, self.node)
        self.env = dict(os.environ)
        for key in list(self.env):
            if key.startswith(('GIT_', 'NODE_', 'PYTHON', 'LD_', 'DYLD_', 'SELECTED_PACKAGE_')) or key in ('GH_TOKEN', 'GITHUB_TOKEN'):
                self.env.pop(key)
        self.env.update(SELECTED_PACKAGE_TRUSTED_BASE=self.base, RUNNER_TOOL_CACHE=str(self.cache), GH_TOKEN='synthetic-token-never-transmitted')
        self.started = []

    def write(self, name, raw):
        target = self.root / name; target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw.encode() if isinstance(raw, str) else raw); return target
    def git(self, *args, input=None):
        env = {k:v for k,v in os.environ.items() if not k.startswith('GIT_')}
        return subprocess.check_output([SYSTEM_GIT, '-C', str(self.root), *args], input=input, env=env, stderr=subprocess.PIPE)
    def trust_changes(self):
        self.git('add', '.'); self.git('commit', '-qm', 'Updated trusted fixture')
        self.env['SELECTED_PACKAGE_TRUSTED_BASE'] = self.git('rev-parse', 'HEAD').decode().strip()
    def api_value(self, route):
        authority=getattr(self,'authority_root',self.root)
        def git(*args):
            clean={k:v for k,v in os.environ.items() if not k.startswith('GIT_') and k not in ('GH_TOKEN','GITHUB_TOKEN')}
            return OFFLINE_GIT_READ([SYSTEM_GIT,'-C',str(authority),'--no-replace-objects',*args],env=clean,stderr=subprocess.PIPE)
        oid=route.rsplit('/',1)[1]
        if '/commits/' in route:
            return {'sha':oid,'tree':{'sha':git('rev-parse',oid+'^{tree}').decode().strip()}}
        if '/blobs/' in route:
            raw=git('cat-file','blob',oid)
            return {'sha':oid,'encoding':'base64','size':len(raw),'content':base64.b64encode(raw).decode()}
        rows=[]
        for item in git('ls-tree','-z',oid).split(b'\0'):
            if not item: continue
            header,name=item.split(b'\t');mode,kind,child=header.decode().split()
            rows.append({'path':name.decode(),'mode':mode,'type':kind,'sha':child})
        return {'sha':oid,'truncated':False,'tree':rows}

    def run_bootstrap(self):
        def execve(program, args, env):
            self.started.append((program, args, dict(env))); raise StartedNode()
        owner=self
        class Opener:
            def open(self, request, timeout):
                owner.assertEqual(request.get_header('Authorization'),'Bearer synthetic-token-never-transmitted')
                route=request.full_url.removeprefix('https://api.github.com/repos/ChengshuLi/WorldAtlas')
                value=owner.api_value(route)
                if hasattr(owner,'alter_api'): value=owner.alter_api(route,value)
                return io.BytesIO(json.dumps(value).encode())
        with patch.dict(os.environ, self.env, clear=True), patch.object(bootstrap.shutil, 'which', return_value=str(self.node)), patch.object(bootstrap.os, 'execve', side_effect=execve), patch.object(bootstrap.urllib.request,'build_opener',return_value=Opener()):
            bootstrap.main()
    def accepted(self):
        with self.assertRaises(StartedNode): self.run_bootstrap()
        self.assertEqual(len(self.started), 1)
        self.assertEqual(self.started[0][1], [str(self.node), self.env.get('SELECTED_PACKAGE_ENTRY_POINT','scripts/assemble-selected-package.mjs')])
        self.assertEqual(self.started[0][2]['GH_TOKEN'], 'synthetic-token-never-transmitted')
        self.assertEqual(self.started[0][2]['GIT_NO_REPLACE_OBJECTS'],'1')
        self.assertNotIn('GITHUB_TOKEN',self.started[0][2])
        self.assertNotIn('GIT_CONFIG_COUNT',self.started[0][2])
    def rejected(self, reason):
        with self.assertRaisesRegex(ValueError, reason): self.run_bootstrap()
        self.assertEqual(self.started, [])

    def proof_fixture(self):
        self.write('scripts/run-selected-package-proof.mjs', "import './proof-child.mjs';\n")
        self.write('scripts/proof-child.mjs', "import '../coordination/deep/consumer.mjs';\n")
        # These bodies must be authenticated as bytes, never executed by admission.
        self.write('scripts/selected-package-bootstrap.py', "raise RuntimeError('verifier helper must not execute')\n")
        self.write('scripts/extract-package-output.py', "raise RuntimeError('extractor helper must not execute')\n")
        self.trust_changes()
        self.env['SELECTED_PACKAGE_ENTRY_POINT']='scripts/run-selected-package-proof.mjs'
    def verified_only(self, entry_point='scripts/assemble-selected-package.mjs'):
        self.env['SELECTED_PACKAGE_ENTRY_POINT']=entry_point
        self.env['SELECTED_PACKAGE_VERIFY_ONLY']='true'
        output=io.StringIO()
        with contextlib.redirect_stdout(output): self.run_bootstrap()
        self.assertEqual(self.started,[], 'Verification must never launch the authenticated programme')
        receipt=json.loads(output.getvalue())
        self.assertEqual(receipt['kind'],'authenticated-package-startup-closure')
        self.assertEqual(receipt['trusted_base'],self.env['SELECTED_PACKAGE_TRUSTED_BASE'])
        self.assertEqual(receipt['entry_point'],entry_point)
        self.assertEqual(receipt['files'],sorted(set(receipt['files'])))
        self.assertIn(entry_point,receipt['files'])
        self.assertNotIn('synthetic-token',output.getvalue())
        return receipt

    def test_explicit_assembly_entry_point_launches_only_assembly(self):
        self.env['SELECTED_PACKAGE_ENTRY_POINT']='scripts/assemble-selected-package.mjs';self.accepted()
    def test_proof_entry_point_launches_only_authenticated_observer(self):
        self.proof_fixture();self.accepted()
    def test_reject_unlisted_entry_points_even_in_verify_only_mode(self):
        for name in ['scripts/untrusted.mjs','../scripts/assemble-selected-package.mjs',
                     '/tmp/run-selected-package-proof.mjs','file:scripts/run-selected-package-proof.mjs',
                     'scripts/run-selected-package-proof.mjs --resolve-frozen','']:
            with self.subTest(entry_point=name):
                self.env.update(SELECTED_PACKAGE_ENTRY_POINT=name,SELECTED_PACKAGE_VERIFY_ONLY='true')
                self.rejected('Unknown trusted package entry point')
    def test_verify_only_assembly_returns_exact_static_closure_without_launch(self):
        receipt=self.verified_only()
        self.assertEqual(receipt['files'],['coordination/deep/consumer.mjs','scripts/assemble-selected-package.mjs','scripts/child.mjs'])
        self.assertFalse((self.root/'scripts/selected-package-bootstrap.py').exists(),
                         'Frozen assembly verification must not require current observer helpers')
    def test_verify_only_proof_returns_observer_closure_without_launch(self):
        self.proof_fixture();receipt=self.verified_only('scripts/run-selected-package-proof.mjs')
        self.assertEqual(receipt['files'],['coordination/deep/consumer.mjs','scripts/proof-child.mjs','scripts/run-selected-package-proof.mjs'])
        self.assertNotIn('scripts/assemble-selected-package.mjs',receipt['files'])
    def test_verify_only_cannot_bypass_source_authentication(self):
        self.env['SELECTED_PACKAGE_VERIFY_ONLY']='true'
        self.write('coordination/deep/consumer.mjs','export const value=99;');self.rejected('Actual source differs')
    def test_verify_only_cannot_bypass_external_module_rejection(self):
        self.write('scripts/child.mjs',"import 'untrusted-package';\n");self.trust_changes()
        self.env['SELECTED_PACKAGE_VERIFY_ONLY']='true';self.rejected('External credential-bearing startup module')
    def test_verify_only_does_not_evaluate_static_module_bodies(self):
        self.write('scripts/child.mjs',"import fs from 'node:fs';fs.writeFileSync('MUST_NOT_EXECUTE','bad');throw Error('not evaluated');\n")
        self.trust_changes();self.verified_only();self.assertFalse((self.root/'MUST_NOT_EXECUTE').exists())
    def test_verify_only_remains_credential_free_for_git_and_parser_children(self):
        original_run=bootstrap.subprocess.run;calls=[]
        def checked_run(*args,**kwargs):
            if '-C' not in args[0]: calls.append((args,kwargs))
            return original_run(*args,**kwargs)
        with patch.object(bootstrap.subprocess,'run',side_effect=checked_run):self.verified_only()
        self.assertTrue(calls)
        for args,kwargs in calls:
            self.assertNotIn('GH_TOKEN',kwargs['env']);self.assertNotIn('GITHUB_TOKEN',kwargs['env'])
    def test_proof_mode_authenticates_both_python_helper_bodies(self):
        self.proof_fixture()
        for helper in ['scripts/selected-package-bootstrap.py','scripts/extract-package-output.py']:
            with self.subTest(helper=helper):
                original=(self.root/helper).read_bytes();self.write(helper,b'# substituted helper\n')
                self.rejected('Actual source differs');self.write(helper,original)
    def test_proof_verify_only_authenticates_both_python_helper_bodies(self):
        self.proof_fixture();self.env['SELECTED_PACKAGE_VERIFY_ONLY']='true'
        for helper in ['scripts/selected-package-bootstrap.py','scripts/extract-package-output.py']:
            with self.subTest(helper=helper):
                original=(self.root/helper).read_bytes();self.write(helper,b'# substituted helper\n')
                self.rejected('Actual source differs');self.write(helper,original)
    def test_proof_mode_rejects_missing_helper_files(self):
        self.proof_fixture()
        for helper in ['scripts/selected-package-bootstrap.py','scripts/extract-package-output.py']:
            with self.subTest(helper=helper):
                original=(self.root/helper).read_bytes();(self.root/helper).unlink()
                self.rejected('Actual source member missing');self.write(helper,original)
    def test_proof_mode_rejects_untrusted_untracked_helper(self):
        self.write('scripts/run-selected-package-proof.mjs',"import './child.mjs';\n");self.trust_changes()
        self.write('scripts/selected-package-bootstrap.py','# untracked verifier\n')
        self.write('scripts/extract-package-output.py','# untracked extractor\n')
        self.env['SELECTED_PACKAGE_ENTRY_POINT']='scripts/run-selected-package-proof.mjs'
        self.rejected('Trusted source member missing')
    def test_proof_mode_rejects_helper_symlinks_and_executable_bit_changes(self):
        self.proof_fixture()
        for helper in ['scripts/selected-package-bootstrap.py','scripts/extract-package-output.py']:
            with self.subTest(helper=helper):
                file=self.root/helper;original=file.read_bytes()
                file.chmod(0o755);self.rejected('Actual source differs');file.chmod(0o644)
                target=self.write('helper-copy.py',original);file.unlink();file.symlink_to(target)
                self.rejected('Source link');file.unlink();self.write(helper,original)
    def test_proof_helpers_remain_bound_despite_git_replacement(self):
        self.proof_fixture();helper='scripts/extract-package-output.py'
        original=self.git('rev-parse','HEAD:'+helper).decode().strip();raw=b'# replaced helper\n'
        altered=self.git('hash-object','-w','--stdin',input=raw).decode().strip()
        self.git('replace',original,altered);self.write(helper,raw);self.rejected('Actual source differs')

    def shallow_candidate(self):
        self.authority_root=self.root
        self.write('selected-new.json','new selected data')
        self.git('add','.');self.git('commit','-qm','candidate only')
        clone=Path(self.temp.name)/'shallow'
        subprocess.check_call([SYSTEM_GIT,'clone','--quiet','--depth=1','file://'+str(self.root),str(clone)],stderr=subprocess.DEVNULL)
        self.root=clone;os.chdir(clone)
        absent=subprocess.run([SYSTEM_GIT,'cat-file','-e',self.base+'^{commit}'],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        self.assertNotEqual(absent.returncode,0,'Fixture must really lack the base commit')
    def test_accept_genuine_candidate_only_shallow_checkout(self):
        self.shallow_candidate();self.accepted()
    def test_reject_wrong_authenticated_base_commit(self):
        self.alter_api=lambda route,value:{**value,'sha':'f'*40} if '/commits/' in route else value
        self.rejected('Authenticated trusted-base commit')
    def test_reject_corrupted_missing_base_tree(self):
        self.shallow_candidate()
        def alter(route,value):
            if '/trees/' in route: value['tree'][0]['sha']='f'*40
            return value
        self.alter_api=alter;self.rejected('Trusted Git object body differs')
    def test_reject_truncated_missing_base_tree(self):
        self.shallow_candidate()
        self.alter_api=lambda route,value:{**value,'truncated':True} if '/trees/' in route else value
        self.rejected('Complete authenticated tree')

    def missing_objects(self):
        self.shallow_candidate()
        objects=self.root/'.git/objects'
        objects.rename(Path(self.temp.name)/'saved-objects');objects.mkdir()
    def test_accept_missing_base_blob_metadata_without_hydration(self):
        self.missing_objects();self.accepted()
        self.assertEqual(list((self.root/'.git/objects').iterdir()),[],'API metadata must stay in memory')
    def test_reject_corrupted_missing_base_blob(self):
        self.missing_objects()
        def alter(route,value):
            if '/blobs/' in route: value['content']=base64.b64encode(b'corrupt').decode();value['size']=7
            return value
        self.alter_api=alter;self.rejected('Trusted Git object body differs')

    def test_accept_intact_transitive_static_closure(self): self.accepted()
    def test_reject_direct_source_edit(self):
        self.write('scripts/assemble-selected-package.mjs', "import './child.mjs';\n// edited\n"); self.rejected('Actual source differs')
    def test_reject_transitive_source_edit(self):
        self.write('coordination/deep/consumer.mjs', 'throw Error("edited");\n'); self.rejected('Actual source differs')
    def test_reject_executable_bit_edit(self):
        (self.root / 'scripts/child.mjs').chmod(0o755); self.rejected('Actual source differs')
    def test_reject_source_symlink(self):
        target=self.root / 'scripts/child.mjs'; copy=self.write('copy.mjs', target.read_bytes()); target.unlink(); target.symlink_to(copy); self.rejected('Source link')
    def test_reject_source_parent_symlink(self):
        target=self.root / 'coordination/deep'; moved=self.root / 'outside'; target.rename(moved); target.symlink_to(moved, target_is_directory=True); self.rejected('Source link')
    def test_reject_untracked_package_scope(self):
        self.write('scripts/package.json', '{"type":"module"}'); self.rejected('Unexpected Node package scope')
    def test_reject_deep_untracked_package_scope(self):
        self.write('coordination/package.json', '{"type":"module"}'); self.rejected('Unexpected Node package scope')
    def test_reject_package_scope_dangling_symlink(self):
        (self.root / 'scripts/package.json').symlink_to('missing.json'); self.rejected('Unexpected Node package scope')
    def test_reject_root_package_edit(self):
        self.write('package.json','{"name":"different","type":"module"}'); self.rejected('Actual source differs')
    def test_reject_lock_edit(self):
        self.write('package-lock.json','{}'); self.rejected('Actual source differs')
    def test_reject_static_external_module(self):
        self.write('scripts/child.mjs', "import '@noble/hashes/sha2.js';\n"); self.trust_changes(); self.rejected('External credential-bearing startup module')
    def test_reject_static_external_reexport(self):
        self.write('scripts/child.mjs', "export {sha256} from '@noble/hashes/sha2.js';\n"); self.trust_changes(); self.rejected('External credential-bearing startup module')
    def test_reject_static_bare_builtin(self):
        self.write('scripts/child.mjs', "import fs from 'fs';\n"); self.trust_changes(); self.rejected('External credential-bearing startup module')
    def test_reject_static_external_despite_edited_extra_or_symlink_dependency(self):
        self.write('scripts/child.mjs', "import '@noble/hashes/sha2.js';\n"); self.trust_changes()
        self.write('node_modules/@noble/hashes/sha2.js', 'throw Error("edited");')
        self.write('node_modules/@noble/hashes/extra.js', 'throw Error("extra");')
        (self.root / 'node_modules/@noble/hashes/link.js').symlink_to('sha2.js')
        self.rejected('External credential-bearing startup module')
    def test_reject_nested_dependency_shadow(self):
        self.write('scripts/node_modules/@noble/hashes/sha2.js', 'throw Error("shadow");'); self.rejected('Unexpected nested module resolution directory')
    def test_reject_nested_dependency_dangling_symlink(self):
        (self.root / 'scripts/node_modules').symlink_to('missing', target_is_directory=True); self.rejected('Unexpected nested module resolution directory')
    def test_reject_deep_nested_dependency_directory(self):
        self.write('coordination/node_modules/x.js', ''); self.rejected('Unexpected nested module resolution directory')
    def test_preinstall_authenticates_root_inputs_without_launching_node(self):
        self.env['SELECTED_PACKAGE_PREFLIGHT']='install'
        self.write('package-lock.json','{"lockfileVersion":3}')
        self.write('requirements.txt','numpy==2.3.5\n')
        self.trust_changes(); self.run_bootstrap();self.assertEqual(self.started,[])
        for name in ['package-lock.json','requirements.txt']:
            original=(self.root/name).read_bytes();self.write(name,'modified installer input')
            with self.assertRaisesRegex(ValueError,'Actual source differs'):self.run_bootstrap()
            self.write(name,original)
        self.write('.npmrc','script-shell=untrusted\n')
        with self.assertRaisesRegex(ValueError,'Unexpected installer root configuration'):self.run_bootstrap()
    def test_preinstall_refuses_unreviewed_project_lifecycle_even_on_trusted_base(self):
        self.env['SELECTED_PACKAGE_PREFLIGHT']='install'
        self.write('package.json','{"type":"module","scripts":{"prepare":"node candidate.mjs"}}')
        self.trust_changes()
        with self.assertRaisesRegex(ValueError,'Project installer hooks'):self.run_bootstrap()
    def test_reject_startup_injection(self):
        for key in ('NODE_OPTIONS','NODE_PATH','LD_PRELOAD','DYLD_INSERT_LIBRARIES'):
            with self.subTest(key=key):
                self.env[key]='injected'; self.rejected('Startup injection'); self.env.pop(key)
    def test_reject_node_outside_toolcache(self):
        self.node=Path(SYSTEM_NODE); self.rejected('Verified setup-node executable')
    def test_reject_symlinked_node(self):
        self.node.unlink(); self.node.symlink_to(SYSTEM_NODE); self.rejected('Verified setup-node executable')
    def test_ignore_benign_git_replacement(self):
        original=self.git('rev-parse','HEAD:scripts/child.mjs').decode().strip(); altered=self.git('hash-object','-w','--stdin',input=b'evil replacement\n').decode().strip(); self.git('replace',original,altered); self.accepted()
    def test_reject_source_backed_by_git_replacement(self):
        original=self.git('rev-parse','HEAD:scripts/child.mjs').decode().strip(); raw=b'import "node:fs"; // replaced\n'; altered=self.git('hash-object','-w','--stdin',input=raw).decode().strip(); self.git('replace',original,altered); self.write('scripts/child.mjs',raw); self.rejected('Actual source differs')
    def test_parser_handles_comments_multiline_adjacent_and_reexport(self):
        self.write('scripts/child.mjs', "import/* comment */{\nvalue as v\n}from/* comment */'../coordination/deep/consumer.mjs';import 'node:fs';export/* comment */{value}from '../coordination/deep/consumer.mjs';\nconst ordinary='python-import';const generated=\"import('+JSON.stringify(oldValidatorPath)+')\";\n")
        self.trust_changes(); self.accepted()
    def test_parser_does_not_evaluate_source(self):
        self.write('scripts/child.mjs', "import fs from 'node:fs';fs.writeFileSync('MUST_NOT_EXECUTE','bad');\nthrow Error('must not evaluate');\n")
        self.trust_changes(); self.accepted(); self.assertFalse((self.root/'MUST_NOT_EXECUTE').exists())
    def test_parser_follows_commented_static_import_despite_edit(self):
        self.write('scripts/child.mjs', "import/* comment */{value}from/* comment */'../coordination/deep/consumer.mjs';\n"); self.trust_changes(); self.write('coordination/deep/consumer.mjs','export const value=99;'); self.rejected('Actual source differs')
    def test_strip_credentials_and_git_config_from_all_subprocesses(self):
        self.env.update(LD_LIBRARY_PATH='/opt/hostedtoolcache/Python/3.12.15/x64/lib',GITHUB_TOKEN='synthetic-github-token',GIT_CONFIG_COUNT='1',GIT_CONFIG_KEY_0='some.setting',GIT_CONFIG_VALUE_0='injected')
        original=bootstrap.subprocess.check_output; original_run=bootstrap.subprocess.run; calls=[]
        def checked(*args, **kwargs): calls.append((args,kwargs)); return original(*args,**kwargs)
        def checked_run(*args,**kwargs):
            if '-C' not in args[0]: calls.append((args,kwargs))
            return original_run(*args,**kwargs)
        with patch.object(bootstrap.subprocess,'check_output',side_effect=checked),patch.object(bootstrap.subprocess,'run',side_effect=checked_run): self.accepted()
        self.assertNotIn('LD_LIBRARY_PATH',self.started[-1][2])
        self.assertTrue(any('--experimental-vm-modules' in args[0] for args,kwargs in calls))
        for args,kwargs in calls:
            env=kwargs['env']
            for key in ('GH_TOKEN','GITHUB_TOKEN','LD_LIBRARY_PATH','GIT_CONFIG_COUNT','GIT_CONFIG_KEY_0','GIT_CONFIG_VALUE_0'): self.assertNotIn(key,env)
            self.assertEqual(env['GIT_NO_REPLACE_OBJECTS'],'1'); self.assertEqual(env['GIT_CONFIG_GLOBAL'],'/dev/null')
    def test_authenticate_python_runtime_helper_when_identity_module_is_consumed(self):
        self.write('scripts/child.mjs', "import './package-output-artifact.mjs';\n")
        self.write('scripts/package-output-artifact.mjs', "export const identity=2;\n")
        self.write('scripts/package-python-runtime.py', "raise RuntimeError('must not execute')\n")
        self.trust_changes(); self.accepted(); self.started.clear()
        self.write('scripts/package-python-runtime.py', "print('substituted executable helper')\n")
        self.rejected('Actual source differs')

    def test_accept_real_repository_static_closure(self):
        # Copy Node's independently parsed static graph, without evaluating modules.
        names=actual_static_graph(SOURCE_ROOT, 'scripts/assemble-selected-package.mjs')
        self.assertIn('scripts/assemble-selected-package.mjs',names)
        for name in names+['scripts/package-python-runtime.py']: self.write(name,(SOURCE_ROOT/name).read_bytes())
        self.write('package.json',(SOURCE_ROOT/'package.json').read_bytes()); self.trust_changes(); self.accepted()
        cli=(SOURCE_ROOT/'scripts/assemble-selected-package.mjs').read_text()
        self.assertLess(cli.index('delete process.env.GH_TOKEN;delete process.env.GITHUB_TOKEN;'),cli.index('result=await assembleSelectedPackage('))

    def test_accept_real_proof_observer_closure_and_explicit_python_helpers(self):
        names=actual_static_graph(SOURCE_ROOT, 'scripts/run-selected-package-proof.mjs')
        self.assertIn('scripts/run-selected-package-proof.mjs',names)
        self.assertNotIn('scripts/assemble-selected-package.mjs',names,
                         'Frozen assembly is imported only after its separate authentication')
        for name in names+['scripts/selected-package-bootstrap.py','scripts/extract-package-output.py','scripts/package-python-runtime.py','package.json']:
            self.write(name,(SOURCE_ROOT/name).read_bytes())
        self.trust_changes();receipt=self.verified_only('scripts/run-selected-package-proof.mjs')
        self.assertEqual(receipt['files'],sorted(names))

class WorkflowBootstrapTests(unittest.TestCase):
    def setUp(self):
        workflow=(SOURCE_ROOT/'.github/workflows/merge-integration-checks.yml').read_text()
        self.assertIn("python3 -I -S -B - <<'ASSEMBLY_BOOTSTRAP'",workflow)
        self.code=textwrap.dedent(workflow.split("<<'ASSEMBLY_BOOTSTRAP'\n",1)[1].split('          ASSEMBLY_BOOTSTRAP',1)[0])
        self.temp=tempfile.TemporaryDirectory(prefix='worldatlas-inline-bootstrap-'); self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name); oldcwd=Path.cwd(); os.chdir(self.root); self.addCleanup(os.chdir,oldcwd)
        self.output=self.root/'output'; self.marker=self.root/'marker'
        self.base='a'*40;self.bootstrap_ref=self.base
        self.env=dict(os.environ,GH_TOKEN='synthetic-token-never-transmitted',GITHUB_REPOSITORY='ChengshuLi/WorldAtlas',SELECTED_PACKAGE_TRUSTED_BASE=self.base,GITHUB_OUTPUT=str(self.output),BOOTSTRAP_TEST_MARKER=str(self.marker))
        self.body=b"import os\nwith open(os.environ['BOOTSTRAP_TEST_MARKER'],'w') as out: out.write('trusted base helper')\n"
        self.blob={'type':'file','encoding':'base64','path':'scripts/selected-package-bootstrap.py','content':base64.b64encode(self.body).decode(),'size':len(self.body),'sha':hashlib.sha1(b'blob '+str(len(self.body)).encode()+b'\0'+self.body).hexdigest()}
        self.requests=[]; self.handlers=[]
    def invoke(self, error=None):
        test=self
        class OfflineOpener:
            def open(self, request, timeout):
                test.requests.append((request,timeout))
                if error: raise error
                return io.BytesIO(json.dumps(test.blob).encode())
        def opener(*handlers): self.handlers.extend(handlers); return OfflineOpener()
        with patch.dict(os.environ,self.env,clear=True),patch.object(urllib.request,'build_opener',side_effect=opener):
            exec(compile(self.code,'<actual inline workflow bootstrap>','exec'),{})
    def assert_fallback(self):
        self.assertFalse(self.marker.exists()); self.assertEqual(self.output.read_text(),'assembled=false\n')
    def test_authenticated_base_body_executes_without_candidate_helper(self):
        candidate=self.root/'scripts/selected-package-bootstrap.py'; candidate.parent.mkdir(); candidate.write_text("raise RuntimeError('candidate helper must never execute')")
        self.invoke(); self.assertEqual(self.marker.read_text(),'trusted base helper'); self.assertFalse(self.output.exists())
        request,timeout=self.requests[0]
        self.assertEqual(request.full_url,'https://api.github.com/repos/ChengshuLi/WorldAtlas/contents/scripts/selected-package-bootstrap.py?ref='+self.bootstrap_ref)
        self.assertEqual(request.get_header('Authorization'),'Bearer synthetic-token-never-transmitted'); self.assertEqual(timeout,30)
        self.assertEqual(len(self.handlers),1)
        with self.assertRaises(ValueError): self.handlers[0].redirect_request(None,None,None,None,None,None)
    def test_missing_trusted_helper_falls_back_without_candidate_execution(self):
        self.invoke(urllib.error.HTTPError('https://api.github.com',404,'Not Found',None,None)); self.assert_fallback()
    def test_bad_blob_identity_falls_back(self):
        self.blob['sha']='0'*40; self.invoke(); self.assert_fallback()
    def test_nonordinary_trusted_path_falls_back(self):
        self.blob['type']='symlink'; self.invoke(); self.assert_fallback()
    def test_wrong_repository_falls_back_before_token_request(self):
        self.env['GITHUB_REPOSITORY']='other/repo'; self.invoke(); self.assert_fallback(); self.assertFalse(self.requests)
    def test_nonexact_base_falls_back_before_token_request(self):
        self.env['SELECTED_PACKAGE_TRUSTED_BASE']='main'; self.invoke(); self.assert_fallback(); self.assertFalse(self.requests)

class ProofWorkflowBootstrapTests(WorkflowBootstrapTests):
    def setUp(self):
        super().setUp()
        workflow=(SOURCE_ROOT/'.github/workflows/selected-package-proof.yml').read_text()
        self.assertIn("python3 -I -S -B - <<'ASSEMBLY_PROOF'",workflow)
        self.bootstrap_ref='b'*40;self.env['GITHUB_SHA']=self.bootstrap_ref
        self.code=textwrap.dedent(workflow.split("<<'ASSEMBLY_PROOF'\n",1)[1].split('          ASSEMBLY_PROOF',1)[0])
        self.assertNotIn('npm run build',workflow)
        self.assertLess(workflow.index('Authenticate installer inputs'),workflow.index('npm ci'))
        self.assertNotIn('write',workflow.split('    permissions:',1)[1].split('    steps:',1)[0])
        for text in ['persist-credentials: false','SELECTED_PACKAGE_ASSEMBLY_SHA256:',
                     'node scripts/run-integration-tests.mjs','selectedDeliverySmoke','--built-output-readback']:
            self.assertIn(text,workflow)
    def test_observer_checkout_contains_actual_static_closure_and_python_helpers(self):
        workflow=(SOURCE_ROOT/'.github/workflows/selected-package-proof.yml').read_text()
        checkout=workflow.split('- name: Checkout current proof implementation separately',1)[1].split('      - ',1)[0]
        self.assertIn('path: proof-tools',checkout)
        self.assertIn('ref: ${{ github.sha }}',checkout)
        sparse=re.search(r'(?m)^          sparse-checkout: \|\n((?:            [^\n]+\n)+)',checkout)
        if sparse:
            roots=[line.strip().rstrip('/') for line in sparse[1].splitlines()]
            closure=actual_static_graph(SOURCE_ROOT,'scripts/run-selected-package-proof.mjs')
            closure+=['scripts/selected-package-bootstrap.py','scripts/extract-package-output.py','scripts/package-python-runtime.py']
            absent=[name for name in closure if '/' in name and not any(name==root or name.startswith(root+'/') for root in roots)]
            self.assertEqual(absent,[], 'Sparse observer checkout omits actually executed or authenticated files')
        else:
            self.assertNotIn('sparse-checkout:',checkout,'Unsupported sparse declaration must be reviewed')
        assembly=workflow.split('- name: Assemble frozen production source and compare with current proof implementation',1)[1].split('      - ',1)[0]
        self.assertIn('working-directory: proof-tools',assembly)
        self.assertIn('SELECTED_PACKAGE_TRUSTED_BASE: ${{ github.sha }}',assembly)
        self.assertIn('SELECTED_PACKAGE_ENTRY_POINT: scripts/run-selected-package-proof.mjs',assembly)

    def assert_rejected(self, error=None):
        with self.assertRaises(Exception): self.invoke(error)
        self.assertFalse(self.marker.exists());self.assertFalse(self.output.exists())
    def test_missing_trusted_helper_falls_back_without_candidate_execution(self):
        self.assert_rejected(urllib.error.HTTPError('https://api.github.com',404,'Not Found',None,None))
    def test_bad_blob_identity_falls_back(self):
        self.blob['sha']='0'*40; self.assert_rejected()
    def test_nonordinary_trusted_path_falls_back(self):
        self.blob['type']='symlink'; self.assert_rejected()
    def test_wrong_repository_falls_back_before_token_request(self):
        self.env['GITHUB_REPOSITORY']='other/repo'; self.assert_rejected();self.assertFalse(self.requests)
    def test_nonexact_base_falls_back_before_token_request(self):
        self.env['SELECTED_PACKAGE_TRUSTED_BASE']='main'; self.assert_rejected();self.assertFalse(self.requests)

class ProofInstallerBootstrapTests(ProofWorkflowBootstrapTests):
    def setUp(self):
        super().setUp()
        workflow=(SOURCE_ROOT/'.github/workflows/selected-package-proof.yml').read_text()
        self.assertIn("python3 -I -S -B - <<'INSTALLER_PREFLIGHT'",workflow)
        self.code=textwrap.dedent(workflow.split("<<'INSTALLER_PREFLIGHT'\n",1)[1].split('          INSTALLER_PREFLIGHT',1)[0])
        self.env['SELECTED_PACKAGE_PREFLIGHT']='install'
        self.assertNotEqual(self.env['SELECTED_PACKAGE_TRUSTED_BASE'],self.env['GITHUB_SHA'],
                            'Installer fixture distinguishes frozen source from current verifier implementation')

if __name__=='__main__': unittest.main(verbosity=2)
