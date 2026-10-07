"""Directed real entry/helper controls for the independently found counterexamples."""
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch
import restore
import verify


def main(node):
    cases = [(9007199254740993, 9007199254740992.0, False),
             (9007199254740993, 9007199254740993, True),
             (21, 21.0, True), (0, -0.0, False), (False, 0, False), (1.5, 1, False)]
    for a, b, expected in cases:
        assert verify.same_values(a, b) is expected
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        (root / 'body').write_bytes(b'abc')
        pin = {'path': 'body', 'bytes': 3, 'sha256': hashlib.sha256(b'abcdefg').hexdigest()}
        # Stat and open race: the actual opened stream is larger than the admitted stat.
        with patch.object(Path, 'is_file', return_value=True), patch.object(Path, 'stat', return_value=SimpleNamespace(st_size=3, st_mode=0o100644)), patch.object(Path, 'open', return_value=io.BytesIO(b'abcdefg')):
            try: restore.raw_file(root, pin)
            except ValueError as error: assert 'EOF length' in str(error)
            else: raise AssertionError('Post-stat stream growth accepted')
        pin['sha256'] = hashlib.sha256(b'abc').hexdigest()
        assert restore.raw_file(root, pin) == b'abc'
    base = "import sys;sys.path.insert(0,sys.argv[1]);import verify,execution;"
    tests = [('', True),
             ("execution.subprocess.run=lambda *a,**k:None;", False),
             ("verify.same_values=lambda a,b:True;", False),
             ("execution.sys.version='wrong-version';", False),
             ("execution.sys.executable='/bin/false';", False)]
    for mutation, positive in tests:
        code = base + mutation + 'execution.authenticate_runtime(sys.argv[2])'
        result = subprocess.run([sys.executable, '-c', code, str(restore.PREFIX), node], capture_output=True, text=True)
        if positive:
            assert result.returncode == 0, result.stderr
        else:
            assert result.returncode != 0 and 'cold runtime/import/callable identity differs' in result.stderr, result.stderr
    bad_node = subprocess.run([sys.executable, '-c', base + 'execution.authenticate_runtime(sys.argv[2])', str(restore.PREFIX), '/bin/false'], capture_output=True, text=True)
    assert bad_node.returncode != 0
    print(json.dumps({'status': 'PASS', 'controls': 14, 'exact_large_integer_relation': True,
                      'bounded_actual_eof_after_stat': True, 'real_cold_runtime_and_callable_guards': True}))


if __name__ == '__main__':
    main(sys.argv[1])
