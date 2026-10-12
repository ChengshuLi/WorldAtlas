# Selected package output reuse (#1798)

Recorded 2026-10-12 (America/Los_Angeles). This is engineering work, not a
geographic approval, delivery, deployment, or new scientific qualification.

## Measured target

Norway A's original hosted package job 114965661618 took 818 seconds overall:
checkout 146 seconds, Cloudflare build 264 seconds, native readback 4 seconds,
browser setup 34 seconds, and selected consumers 322 seconds. Consumer setup
included 108.071 seconds of invariant model-reader restoration. Its TAP tests
ran concurrently, so individual test durations must not be added as savings.
Only 40 declared files (14.56 MB) changed in the 8,708-file (2.77 GB) input image.
These are historical observations, not measurements of this implementation.

## Admission and output custody

A successful original full regression shard 0 or full selected package job
retains actual `dist/client` and `dist/cloudflare`, complete streamed byte
inventory, source snapshot and original build receipt. Receipt-only artifacts
are ineligible. Metadata-only reuse and assembled outputs never mint originals.

Admission authenticates run, attempt, exact successful producer job/steps,
artifact ID, name, size, digest, and the producer log's manifest/upload binding.
The full original source inventory and producer programme must match current
invariants. Only the additive selection hook and append-only individually
consumed inert selected inputs may change. Actual original input files are
checked against the complete committed inventory, including untracked extras
inside declared directories and optional absence. Installed Node, dependency
bodies, and Python distribution bodies are compared, as well as versions,
lockfile and build configuration. Installed identity is captured before the original
build/consumer suite, so generated Vite caches cannot masquerade as changed
installed dependencies. Python bytecode cache timestamp headers are
excluded from identity; executable bytecode and original source bytes remain
hashed. Unknown or unavailable authority safely returns to the full build.

Credential-bearing startup uses an API-authenticated trusted-base isolated
Python bootstrap. It verifies source bytes/modes and Node package-resolution
scopes against authenticated Git objects. A candidate-only shallow checkout
acquires missing trusted-base tree/blob metadata through authenticated API reads,
verifies exact object hashes, and keeps it in memory without base data hydration.
Node's real parser, without evaluation
and with no credential environment, identifies the static startup graph. Static
external modules, nested module resolution directories and startup injections
are refused. The verified setup-node executable starts the driver, which removes
its token environment before deferred scientific imports.

The existing privately branded selected reader consumes current authority and
publishes the four additive bodies through its unchanged exclusive-create
publisher. A separate private assembly execution token cannot impersonate an
original full-build consumption context. Only four authenticated old additive
assets and `atlas-geography.json`'s `reference_release` and `additiveRelease`
fields change. Original native-context provenance remains original. A separate
current assembly receipt records the original producer and current execution.

Every invariant output member is rehashed before publishing. Current output
and receipt are staged and replaced together with rollback. Archive extraction
rejects traversal, duplicate/extra/missing members, symlinks, encryption and
hash/size drift. Output bytes are streamed in 1 MiB chunks; disk admission uses
authenticated archive/decoded inventory and available capacity. The selected
reader and assembly share the existing processing allowance derived from current
OS/cgroup availability and concurrent reservations; code, runtime, metadata and
reader payloads are charged against that actual allowance. No arbitrary
32 MiB member or 1 GiB package-size cutoff defines scientific eligibility.

## Current versus retained tests

Current selected smoke, native readback, focused controls, packaged coverage,
service-unavailable behavior and actual GPU/Canvas before/after rendering remain
fresh. Only unchanged prepared static/server all-location parity and canonical
compact repack are attributed to the successful original producer. The reduced
runner requires the exact current assembly receipt digest and same head, then
omits historical regression acquisition and model-reader restoration. It never
labels inherited tests as freshly executed. Full builds retain both original
base tests and every current selected test.

## Validation and adoption limits

Lightweight tests exercise actual source, ZIP, run/job/artifact, private-token,
consumer-roster and runner boundaries with synthetic fixtures; those fixtures
are not scientific proof. The normal full implementation PR must produce the
first eligible retained output. `compare-selected-package-output.mjs` compares
all output paths and every file byte except the atlas metadata file, whose
complete semantic value must match except the single original source-head
provenance scalar. Runtime, code closure, scientific counters and additive
fields are not normalized away. Any additional difference is a failed proof.

The actual full-versus-assembled output proof and changed-batch wall-clock
measurement remain open until genuine retained output is available. A same-state
rollout comparison must be reported as such, not as changed-batch acceleration.
The complete authenticated checkout still runs; its historical 146 seconds is
not claimed saved. Artifact transfer/inventory overhead is not yet measured.
No local full input hydration or full package build was performed for this work.

## Browser scale-up follow-on

The selected renderer test currently enumerates every cumulative repair cell in
four GPU/Canvas × before/after passes. The before bank/catalog are invariant.
The after bank is not a byte-identical renderer input: `applyAdditiveNativePatch`
rebuilds packed row/run arrays, changing subsequent offsets, and `PixelGPU`
uploads the complete arrays with length-dependent texture layout. Canvas also
updates touched owners' composite bounds. Unchanged logical ownership alone
does not permit reusing all old after observations. A future reduction must bind
browser/runtime identity, actual packed-row/texture layout and touched-owner
bounds, then cover newly changed/affected rows and layout boundaries. This PR
keeps the complete current cumulative renderer test.
