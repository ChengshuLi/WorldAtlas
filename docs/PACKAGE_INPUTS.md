# Deployment package inputs

`.github/package-inputs.json` is the shared source of truth for deployment package inputs and the applicability of package CI. It declares ordinary source files/directories, optional directories, package verification controls, and approved generated outputs. Directory entries end in `/`; other entries match exactly. No implementation byte fingerprints are maintained.

`npm run build:static`, `npm run build:hosted`, and `npm run build:cloudflare` create a temporary source image containing only those declared inputs and the caller's installed dependencies. Private inner builders run there. Ordinary filesystem reads, imports and child tools cannot consume unpublished repository files absent from that image. Required missing inputs, source symlinks and dependency links escaping the dependency installation fail the build. Successful builds return only approved outputs; failed child builds retain previous caller outputs. Temporary images are removed in `finally` and live inside the managed checkout's cache so abandoned images remain subject to workspace cleanup. Check storage before large builds.

This is a cooperative build boundary, not an operating-system security sandbox. Deliberate absolute access to outside files, malicious dependencies and forged stage environment variables are not contained. It also does not guarantee a reproducible environment or pin remote network responses. Build jobs retain existing read-only credentials and deployment/import restrictions. Use the public package commands and review build changes under the normal independent-review gate.

CI reads the declaration at trusted base and enumerates all changed paths, including rename/copy origins. Any declared input or verification path requires a package build and budget checks. Missing or malformed declaration, incomplete inventory, changing PR identity, API failure or capped comparisons conservatively require the build. Unchanged package inputs skip candidate checkout, dependency installation and package compilation; the receipt does not claim a new size measurement.

Application regression selection remains a separate question. Unpublished geography packets and history campaigns run their focused scope/evidence/invariant checks. If a research file is explicitly included in the package, its changes also run package checks; they do not automatically require unrelated application tests. Runtime, schema and build-boundary changes retain application regression according to the integration profile.

When adding a genuine package dependency outside declared directories, add its precise path to the declaration in the same reviewed PR. Do not declare a whole research namespace to make a missing-read error disappear. Data manifests that point at unpublished research must promote the actual required inputs explicitly. New ordinary modules inside declared `src/` and `hosted/` directories are already inputs. Root configuration files absent from the image cannot silently affect a build; adopting one requires declaring it. Verification-only controls trigger package checks without entering the package source image.

## Retained original Cloudflare output

The original output inventory is captured immediately after the genuine Cloudflare
build, before readback and regression consumers. Upload still waits for required
checks to succeed. Authentication compares every retained output byte with that
inventory, so a later consumer cannot silently change the reusable package.

New manifests identify this boundary as `immediate-cloudflare-build-v1` and retain
the actual build workflow's Git identity. The complete declared source image,
installed dependencies/runtime and build configuration remain authoritative.
Tests, unrelated workflows and observer scripts outside the declared image do not
invalidate those bytes merely because they changed. A declared observer remains a
package input; this change does not guess which declared files are unused.

Legacy manifests keep their original provenance. They cannot establish immediate
build capture and therefore require the ordinary full-build path under the new
reuse policy. This removes false invalidation for later eligible selected-package
reuse; it does not skip current-head tests, authenticate old runtime evidence as
new, or enable the separately reviewed final-worker adoption by itself.

Local checks:

```sh
node --test test/package-inputs.test.mjs test/package-build.test.mjs test/deployment-budget-scope.test.mjs
npm run build:cloudflare
npm run build:hosted
```

The hosted archive budget uses GNU tar and is verified on Ubuntu CI; macOS BSD tar is not an equivalent archive measurement. Cloudflare preparation creates local artifacts only, without deployment or live database changes.
