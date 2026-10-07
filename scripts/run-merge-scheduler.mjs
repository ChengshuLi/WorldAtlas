import {requestAccounting} from './github-quota.mjs';
import fs from 'node:fs';
import {githubAPI} from './issue-claim-contract.mjs';
import {registerRequest, scheduleNext} from './merge-scheduler.mjs';
const event = JSON.parse(fs.readFileSync(process.env.GITHUB_EVENT_PATH, 'utf8'));
const repo = process.env.GITHUB_REPOSITORY;
if (process.env.GITHUB_REF !== 'refs/heads/main' || !/^[-\w.]+\/[-\w.]+$/.test(repo ?? '')) throw Error('Scheduler runs only from trusted main');
const accounting=requestAccounting(process.env.QUEUE_PHASE??'schedule');
const api = githubAPI(process.env.GH_TOKEN,{onRequest:accounting.observe,readWaitMs:8*60*1000});
try {
if (process.env.QUEUE_PHASE === 'register') {
  const input = event.inputs ?? {}, request = {pr_number: Number(input.pr_number), expected_head: input.expected_head, request_id: input.request_id};
  if (!Number.isSafeInteger(request.pr_number) || request.pr_number < 1 || !/^[a-f0-9]{40}$/.test(request.expected_head ?? '') || !/^[-a-zA-Z0-9]{16,100}$/.test(request.request_id ?? '')) throw Error('Invalid queue request');
  console.log(JSON.stringify(await registerRequest({api, repo, request})));
} else console.log(JSON.stringify(await scheduleNext({api, repo})));

} finally {console.log(JSON.stringify({request_accounting:accounting.receipt()}));}
