// Executed only from a verified immutable baseline, with a read-only token.
import {githubAPI} from './issue-claim-contract.mjs';
import {collectGeographicApproval} from './geographic-adjudication-api.mjs';

try {
  const values = {}, args = process.argv.slice(2);
  for (let index = 0; index < args.length; index += 2) {
    if (!['--pr', '--head'].includes(args[index]) || !args[index + 1] || Object.hasOwn(values, args[index])) {
      throw Error('Use exact --pr NUMBER --head COMMIT arguments');
    }
    values[args[index]] = args[index + 1];
  }
  if (!/^[1-9]\d*$/.test(values['--pr'] ?? '') || !/^[a-f0-9]{40}$/.test(values['--head'] ?? '')) {
    throw Error('Require exact PR number and reviewed commit');
  }
  const result = await collectGeographicApproval({api: githubAPI(process.env.GH_TOKEN),
    repo: process.env.GITHUB_REPOSITORY ?? 'ChengshuLi/WorldAtlas',
    number: Number(values['--pr']), expectedHead: values['--head']});
  const raw = JSON.stringify(result) + '\n';
  if (Buffer.byteLength(raw) > 48 * 1024 * 1024) throw Error('Approval transport exceeds bounded base64 budget');
  process.stdout.write(raw);
} catch (error) {
  process.stdout.write(JSON.stringify({status: 'blocked', reason: error instanceof SyntaxError ?
    'Malformed source dossier or review JSON' : String(error.message).slice(0, 1024)}) + '\n');
  process.exitCode = 1;
}
