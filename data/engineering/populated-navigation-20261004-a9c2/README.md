# Populated-year navigation: current baseline and candidate

Issue638, ENG1, worker engineering-populated-navigation-a9c25e14-20261004.
Fresh implementation base f3263796efccac63dd20296130aeb176323d38ea;
the confirmed claim receipt is in the matching coordination directory.
The previous issue6 implementation is safely handed to ENG main on714;
its production-only remainder stays open/blocked, with the old claim released.

## Actual input and measurement conditions

The observed production Site24 source is2326792cc52fc353264abc33c2ac4e983fb2c3e5,
deployment appgdep_6ac14428eaac8191b59b5d3d8f05fb0d. Native version24 archive
receipt is sha256:d06648cdc833b47020614be807d912e81904c2ccfc9ddbbc20e8cc4a33ada20d,
262389760bytes/539files. Production still serves geographic release5,
geography:review:df86cbaeaf2e18f16ddf2906ef089768baac22f4428e28ed0a4724296cbb413e,
hierarchy03d23534f87cdd0582bcb228780f00f65090bec2e8a760acbab528383f28549d,
footprints2ac42eeb9fef8af923a0d4c4e55af49ca0a103de891ffbfb2c1181ad75950286.
Actual scalar responses captured here have revision3051. All activity is bounded
GET-only; no production mutation, credential rotation or deployment occurred.

Run with Node24 and NODE_USE_ENV_PROXY=1, preserving the managed HTTP/HTTPS
proxy and TLS trust. Native Sites get_site supplies supported owner-private service
access. Keep that credential in session memory and supply only through hidden TTY
stdin; never put it in files, arguments, browser headers, output or Git.

The retained benchmark navigates headless Chromium153.0.8010.12 at1440x1080,
without CPU/network throttling, through a fixed-origin GET-only localhost proxy.
It buffers upstream responses; API waits include network/Worker/database and do
not establish separate Neon query, connection or provider wake durations.
Fresh-context startup is separate from subsequent year selection. This is not
physical-phone evidence. Every completed sample, outlier and failure is retained.

Attempt01 failed before any request because the matching headless browser binary
was missing. Attempt02 made one failed root transport request and timed out:
Node fetch had not opted into the inherited sidecar proxy. Neither is a passing
performance run. Corrected attempt03 completed; its first2020 selection exceeded
three seconds. Attempt04 adds a1ms CDP CPU sampler; compare profiled cases with
profiled candidates and do not silently combine instrumentation conditions.
The retained timeline's100000-event bound can truncate it; the independent CPU
profile is the explicit sampling evidence, not a claim that the timeline is complete.

## Bounded implementation

The sampled resolver was the largest named client CPU function. Candidate fields
are indexed once by location, avoiding repeated compound-key allocations during
resolution. Complete immutable reference presentation context is built once per
loaded asset generation and passed to the resolver; a geography reload clears it.
Default uncached resolver callers retain their previous behavior. Supported dated
fields, uncertainty, withdrawals, source provenance and revision checks are unchanged.
No API/query, ownership, geometry, loader completion or source payload is modified.

The candidate preview serves locally built frontend code while all geography,
ownership, prepared evidence and API data come from the actual release5 Site.
It executes the changed client code against complete production inputs; it is not
a changed production deployment or a benchmark of a changed server handler.
Its exact code/build/input receipts must accompany subsequent review and publication.
The first preview passed five supported selections below three seconds, but repeated
measurements, all-mode/fault checks, independent review, CI and publisher delivery
remain required. Do not close638 from this initial preview.

## Reproduce without inherited caches

From the pinned primary base, npm ci and install its matching Chromium headless shell.
Use profile-benchmark.mjs for supported baseline measurements. Build the candidate
frontend with VITE_STATIC_ATLAS=true VITE_HOSTED_DATABASE=true npx vite build --sourcemap.
Use preview-benchmark.mjs with the same four benchmark arguments plus an absolute
candidate dist directory. The private credential always enters hidden stdin.
capture-snapshot.mjs captures only bounded2020/2021/1900 GET responses with exact
whole-file hashes and revision; it is not a complete database backup or source audit.

For scalar parity, git archive the pinned base's src into an empty directory,
then run verify-resolver-parity.mjs with that directory and an absolute receipt path.
It reads exact committed geographic/reference/ownership inputs plus the retained
scalar snapshot claims and compares every field for49625locations across six years.
The committed input generation is release6; this is offline scalar-code parity,
not a repinning of served release5 structure or new geographical approval.
Single Node timing samples can vary with allocation/GC and are not hosted latency.

Publication goes through ENG main and714 after reviewed accepted merge.
The two-PR issue budget and actual three-second production acceptance remain.

## Completed validation and retained limits

Two completed profiled candidate runs retained all ten selections below three
seconds. The failed second attempt returned a catalog5 HTTP500 before any usable
navigation sample; the fresh readback and subsequent successful run are separate
receipts. Baseline repeat outliers remain retained. These are preview results,
not actual deployed production acceptance. Provider query/wake phases remain
unmeasured, and the timeline may reach its event cap.

The mode receipt covers fourteen modes and six continent profiles; the fault
receipt covers nine locally injected scenarios including revision restart,
same-year complete-cache outage, other-year fail-closed and unsupported years.
Scalar parity compares every field for all locations across six dates.
The scoped test log has fifty passing tests. The hosted package completion log
is retained; its first attempt lacked system Shapely, while the second uses the
pinned Python environment on PATH. Its exited process status was not retained
on resumed observation, so the receipt records the actual completion marker.
No Site deployment or production mutation was performed.
