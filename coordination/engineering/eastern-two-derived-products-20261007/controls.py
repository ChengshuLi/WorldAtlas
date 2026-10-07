"""Directed production custody guards, with actual immutable original bytes."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
from unittest.mock import patch

import restore


def rejected(call, needle):
    try:
        call()
    except ValueError as error:
        if needle not in str(error):
            raise AssertionError('Wrong intended rejection branch: ' + str(error)) from error
        return
    raise AssertionError('Expected intended rejection: ' + needle)


def main():
    index = json.loads((restore.PREFIX / 'source-index.json').read_text())
    restore.validate_index(index)
    count = 1
    for value in ('../escape', '/absolute', 'a//b', 'a/./b', 'a/../b'):
        rejected(lambda: restore.safe(value), 'relative path')
        count += 1
    bad = copy.deepcopy(index)
    bad['bindings'].append(copy.deepcopy(bad['bindings'][0]))
    rejected(lambda: restore.validate_index(bad), 'Duplicate complete')
    count += 1
    bad = copy.deepcopy(index)
    bad['bindings'].pop()
    rejected(lambda: restore.validate_index(bad), 'roster omitted')
    count += 1
    bad = copy.deepcopy(index)
    bad['parts'][1]['offset'] += 1
    rejected(lambda: restore.validate_index(bad), 'ordered part closure')
    count += 1
    bad = copy.deepcopy(index)
    bad['members'][0]['decoded_bytes'] = restore.MAX + 1
    rejected(lambda: restore.validate_index(bad), 'Member encoded/decoded')
    count += 1
    rejected(lambda: restore.authenticate_execution('--output=unowned'), 'before Git')
    count += 1
    original = next(b for b in index['bindings'] if b['group'] == 'actual_selector_transitive_closure')
    raw = restore.member_bytes(index, index['members'][original['member_id']])
    restore.original_guard(original, raw)
    count += 1
    changed = raw.replace(b' ', b'\t', 1)
    assert changed != raw and len(changed) == len(raw)
    rebound = copy.deepcopy(original)
    rebound['sha256'] = hashlib.sha256(changed).hexdigest()
    rebound['original_binding']['sha256'] = rebound['sha256']
    rejected(lambda: restore.original_guard(rebound, changed), 'actual immutable'.capitalize())
    count += 1
    with tempfile.TemporaryDirectory() as name:
        root = Path(name)
        (root / 'linked').symlink_to(root, target_is_directory=True)
        rejected(lambda: restore.checked(root, 'linked/file'), 'Symlink')
        count += 1
        (root / 'large').write_bytes(b'abc')
        pin = {'path': 'large', 'bytes': restore.MAX + 1, 'sha256': '0' * 64}
        with patch.object(Path, 'read_bytes', side_effect=AssertionError('Unsafe read before admission')):
            rejected(lambda: restore.raw_file(root, pin), 'bounds differ')
        count += 1
    print(json.dumps({'status': 'PASS', 'actual_directed_controls': count,
                      'coherently_rebound_source_rejected_by_actual_git_oid': True,
                      'complete_roster_and_offset_and_decoded_caps_checked': True}))


if __name__ == '__main__':
    main()
