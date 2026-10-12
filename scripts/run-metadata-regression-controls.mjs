import {METADATA_FRESH_TESTS} from './metadata-regression-program.mjs';
import {streamTestProcess} from './run-integration-tests.mjs';
// Current HEAD and complete current fixture inputs are supplied by the existing
// detached full-checkout path. No canonical/model preparation or build is run.
process.exitCode = await streamTestProcess(['--test', '--test-reporter=tap', '--test-concurrency=2', ...METADATA_FRESH_TESTS]);
