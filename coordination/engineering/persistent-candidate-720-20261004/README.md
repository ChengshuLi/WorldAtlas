# Persistent merge-preview repair (issue720)

GitHub's official warning says merge refs can become outdated and consumers should
GET/poll the PR to request a test merge. The late-fetch/poll repair in PR719 implements
that recommendation. Our subsequent REST/GraphQL/ref reads still observed an old
PR680 candidate. A public reported case also describes over 11 minutes of unsuccessful
GET polling, but its reports are secondary, partly AI-authored evidence, not an
independent certification of GitHub's internal cause.

- Official guidance: https://docs.github.com/en/rest/guides/getting-started-with-the-git-database-api#checking-mergeability-of-pull-requests
- Reported similar case: https://github.com/bgunyel/clause-and-effect/issues/274
- Supported explicit branch merge: https://docs.github.com/en/rest/branches/branches#merge-a-branch

The fallback uses GitHub's ordinary merge endpoint on a unique disposable branch
pinned to exact main, with an exact reviewed head SHA. Neither main, PR metadata nor
worker branches are edited. It runs no candidate code with write credentials. The
normal reviewed-byte/mode, evidence, authority, isolated-test and final merge guards
remain. Only trusted preparation receives contents-write; candidate testing remains
read-only. The branch is retained during immutable-SHA testing and removed by the
final job, including rejected tests/merges. Altered refs are retained, not blindly
deleted. Canceled jobs or cleanup access failures can leave an owned temporary ref;
receipts identify resources for inspection. This is bounded recovery, not a guarantee
that GitHub's automatic previews refresh or that main never advances during tests.

`github-probe.json` records an actual execution of the candidate-creation/cleanup
helper against PR680's unchanged head: exact parents, temporary ref deletion and
unchanged main/head/body/title/target observed before/after. It does not certify PR680
reviewed file bytes, source facts, merge eligibility or publication. No PR680 merge
or tests were requested. The queue owner's existing reservation is preserved.

`validation.txt` records focused coordination controls: existing gates plus permanent
lag fallback, conflict/wrong parents, reviewed-byte rejection, stale authority, final
main guards, exact-owned cleanup refusal and actual final-entry receipt persistence.
