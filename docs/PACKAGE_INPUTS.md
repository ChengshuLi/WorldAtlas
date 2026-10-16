# Deployment package inputs

`.github/package-inputs.json` is the shared source of truth for deployment package inputs and the applicability of package CI. It declares ordinary source files/directories, optional directories, package verification controls, and approved generated outputs. Directory entries end in `/`; other entries match exactly. No implementation byte fingerprints are maintained.

`npm run build:static`, `npm run build:hosted`, and `npm run build:cloudflare` create a temporary source image containing only those declared inputs and the caller's installed dependencies. Private inner builders run there. Ordinary filesystem reads, imports and child tools cannot consume unpublished repository files absent from that image. Required missing inputs, source symlinks and dependency links escaping the dependency installation fail the build. Successful builds return only approved outputs; failed child builds retain previous caller outputs. Temporary images are removed in `finally` and live inside the managed checkout's cache so abandoned images remain subject to workspace cleanup. Check storage before large builds.

This is a cooperative build boundary, not an operating-system security sandbox. Deliberate absolute access to outside files, malicious dependencies and forged stage environment variables are not contained. It also does not guarantee a reproducible environment or pin remote network responses. Build jobs retain existing read-only credentials and deployment/import restrictions. Use the public package commands and review build changes under the normal independent-review gate.

The integration queue builds the Cloudflare application for full software profiles.
The declaration also bounds selected-output reuse and its source inventory. Legacy
Site package budget checks run when explicitly invoking `npm run build:hosted` for
recovery, rather than through an automatic main-push workflow.

Application regression selection remains a separate question. Unpublished geography packets and history campaigns run their focused scope/evidence/invariant checks. If a research file is explicitly included in the package, its changes also run package checks; they do not automatically require unrelated application tests. Runtime, schema and build-boundary changes retain application regression according to the integration profile.

When adding a genuine package dependency outside declared directories, add its precise path to the declaration in the same reviewed PR. Do not declare a whole research namespace to make a missing-read error disappear. Data manifests that point at unpublished research must promote the actual required inputs explicitly. New ordinary modules inside declared `src/` and `hosted/` directories are already inputs. Root configuration files absent from the image cannot silently affect a build; adopting one requires declaring it. Verification-only controls trigger package checks without entering the package source image.

## Retained original Cloudflare output

The original output inventory is captured immediately after the genuine Cloudflare
build, before package controls, browser-selection/install code and regression consumers. Upload still waits for required
checks to succeed. Authentication compares every retained output byte with that
inventory, so a later consumer cannot silently change the reusable package.

New manifests identify this boundary as `immediate-cloudflare-build-v1` and retain
the genuine queue build workflow's Git identity (`worker-merge.yml`). Historical
captures retain their exact original two-workflow roster, including the removed
`merge-integration-checks.yml`. Both rosters are checked against the actual immutable
source and executed workflow. Their producer identities must still match exactly
before output reuse; deleting the author workflow requires a fresh queue-only
full-build capture before a subsequent selected delivery can reuse it. The complete declared source image,
output bytes and build configuration remain authoritative. The capture writer and
isolated Python execution helper are explicit package inputs; the ordinary pre-build
snapshot checks their actual bytes against Git as well as binding their committed identities.

Reuse does not recreate or compare the original installed environment. Historical
runtime metadata stays literal in the original manifest. New captures record the actual
build's runtime metadata without an installed-file inventory. Current assembly admits
its locked Node dependencies, authenticates the archive extractor, and runs the current
selected additive computation with its actual source/input/output bindings. Any new
scientific execution uses the isolated Python launcher and records its own execution;
retaining old output never establishes fresh runtime equivalence or a fresh full build.
Tests, unrelated workflows and observer scripts outside the declared image do not
invalidate those bytes merely because they changed. A declared observer remains a
package input; this change does not guess which declared files are unused.

Selected declaration admission checks the append-only inert file boundary and
immutable source rows. It does not equate the parent reader inventory with all
scientific consumption: detached readers authenticate their own inputs, while
existing scientific loading and copied-publication checks remain authoritative.

The final worker retains genuine full-build originals at this same boundary.
For selected-data candidates it authenticates eligible author or final-worker
archives through the trusted bootstrap, verifies their complete output inventory
and the trusted assembly receipt, then runs current delivery-smoke consumers.
Ordinary unchanged-producer selected-data batches do not reinstall or rerun the
browser suite; full software profiles retain browser qualification. A selected-data
full-build fallback retains the ordinary build preflight and delivery smoke.
A worker run's workflow commit and built candidate commit are distinct: the authenticated inventory log binds the candidate,
and the executed workflow must match its captured descriptor. The existing capture
log records `GITHUB_WORKFLOW_SHA` and the workflow path/ref, including the distinct
merge-ref workflow commit for pull requests. Missing execution provenance cannot
be inferred from the source or Actions run head. A missing or
incompatible original takes the ordinary full-build path. Assembled output is
never retained as a new full-build original.

Legacy manifests keep their original provenance. They cannot establish immediate
build capture and therefore require the ordinary full-build path under the new
reuse policy. This removes false invalidation for later eligible selected-package
reuse; it does not skip current-head tests, authenticate old runtime evidence as
new, or enable the separately reviewed final-worker adoption by itself.

Local checks:

```sh
node --test test/package-inputs.test.mjs test/package-build.test.mjs test/deployment-budget.test.mjs
npm run build:cloudflare
npm run build:hosted
```

The hosted archive budget uses GNU tar and is verified on Ubuntu CI; macOS BSD tar is not an equivalent archive measurement. Cloudflare preparation creates local artifacts only, without deployment or live database changes.
