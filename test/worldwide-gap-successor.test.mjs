import {test} from 'node:test';
import {execFileSync} from 'node:child_process';
test('actual worldwide successor custody, coordinates, deltas and lineage controls', () => {
  execFileSync(process.env.PYTHON || 'python3', ['-B','test/worldwide-gap-successor.py'], {stdio:'pipe',env:{...process.env,PYTHONDONTWRITEBYTECODE:'1'}});
});
