#!/usr/bin/env python3
"""Offline actual-module tests: python3 this.py /path/to/selected-package-bootstrap.py."""
import base64
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
            if key.startswith(('GIT_', 'NODE_', 'PYTHON', 'LD_', 'DYLD_')) or key in ('GH_TOKEN', 'GITHUB_TOKEN'):
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
    def run_bootstrap(self):
        def execve(program, args, env):
            self.started.append((program, args, dict(env))); raise StartedNode()
        with patch.dict(os.environ, self.env, clear=True), patch.object(bootstrap.shutil, 'which', return_value=str(self.node)), patch.object(bootstrap.os, 'execve', side_effect=execve):
            bootstrap.main()
    def accepted(self):
        with self.assertRaises(StartedNode): self.run_bootstrap()
        self.assertEqual(len(self.started), 1)
        self.assertEqual(self.started[0][1], [str(self.node), 'scripts/assemble-selected-package.mjs'])
        self.assertEqual(self.started[0][2]['GH_TOKEN'], 'synthetic-token-never-transmitted')
    def rejected(self, reason):
        with self.assertRaisesRegex(ValueError, reason): self.run_bootstrap()
        self.assertEqual(self.started, [])

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
    def test_reject_startup_injection(self):
        for key in ('NODE_OPTIONS','NODE_PATH','LD_PRELOAD','LD_LIBRARY_PATH','DYLD_INSERT_LIBRARIES'):
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
        self.env.update(GITHUB_TOKEN='synthetic-github-token',GIT_CONFIG_COUNT='1',GIT_CONFIG_KEY_0='some.setting',GIT_CONFIG_VALUE_0='injected')
        original=bootstrap.subprocess.check_output; calls=[]
        def checked(*args, **kwargs): calls.append((args,kwargs)); return original(*args,**kwargs)
        with patch.object(bootstrap.subprocess,'check_output',side_effect=checked): self.accepted()
        self.assertTrue(any('--experimental-vm-modules' in args[0] for args,kwargs in calls))
        for args,kwargs in calls:
            env=kwargs['env']
            for key in ('GH_TOKEN','GITHUB_TOKEN','GIT_CONFIG_COUNT','GIT_CONFIG_KEY_0','GIT_CONFIG_VALUE_0'): self.assertNotIn(key,env)
            self.assertEqual(env['GIT_NO_REPLACE_OBJECTS'],'1'); self.assertEqual(env['GIT_CONFIG_GLOBAL'],'/dev/null')
    def test_accept_real_repository_static_closure(self):
        # Copy Node's independently parsed static graph, without evaluating modules.
        walker="import fs from 'node:fs';import path from 'node:path';import vm from 'node:vm';const root=process.argv[1],q=['scripts/assemble-selected-package.mjs'],seen=new Set();while(q.length){const n=q.pop();if(seen.has(n))continue;seen.add(n);for(const s of new vm.SourceTextModule(fs.readFileSync(path.join(root,n),'utf8')).dependencySpecifiers)if(s.startsWith('.'))q.push(path.posix.normalize(path.posix.join(path.posix.dirname(n),s)));}process.stdout.write(JSON.stringify([...seen]));"
        names=json.loads(subprocess.check_output([SYSTEM_NODE,'--experimental-vm-modules','--input-type=module','-e',walker,str(SOURCE_ROOT)],stderr=subprocess.PIPE))
        self.assertGreater(len(names),10)
        for name in names: self.write(name,(SOURCE_ROOT/name).read_bytes())
        self.write('package.json',(SOURCE_ROOT/'package.json').read_bytes()); self.trust_changes(); self.accepted()
        cli=(SOURCE_ROOT/'scripts/assemble-selected-package.mjs').read_text()
        self.assertLess(cli.index('delete process.env.GH_TOKEN;delete process.env.GITHUB_TOKEN;'),cli.index('result=await assembleSelectedPackage('))

class WorkflowBootstrapTests(unittest.TestCase):
    def setUp(self):
        workflow=(SOURCE_ROOT/'.github/workflows/merge-integration-checks.yml').read_text()
        self.assertIn("python3 -I -B - <<'ASSEMBLY_BOOTSTRAP'",workflow)
        self.code=textwrap.dedent(workflow.split("<<'ASSEMBLY_BOOTSTRAP'\n",1)[1].split('          ASSEMBLY_BOOTSTRAP',1)[0])
        self.temp=tempfile.TemporaryDirectory(prefix='worldatlas-inline-bootstrap-'); self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name); oldcwd=Path.cwd(); os.chdir(self.root); self.addCleanup(os.chdir,oldcwd)
        self.output=self.root/'output'; self.marker=self.root/'marker'
        self.base='a'*40
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
        self.assertEqual(request.full_url,'https://api.github.com/repos/ChengshuLi/WorldAtlas/contents/scripts/selected-package-bootstrap.py?ref='+self.base)
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

if __name__=='__main__': unittest.main(verbosity=2)
