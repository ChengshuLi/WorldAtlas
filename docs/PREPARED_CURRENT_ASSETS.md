# Current prepared assets

Ordinary static, hosted and Cloudflare builds compile current application code and
consume the reviewed current atlas products. They do not reconstruct v8, install
v9, replay original scientific qualification or rewrite temporal bucket headers.
The normal test shards likewise read the committed current products.

`data/ownership-selection.json` selects the base native manifest and optional
accepted additive sidecar. Prepared ownership/reference/evidence indices and
runtime buckets remain bound to that **base** footprint. The additive envelope
supplies its separate effective reference. A new additive selection does not
silently rebind temporal data to a different footprint.

The native deployment transport is prepared once in
`data/canonical-grid/current-startup/`. Its index binds the selected native
manifest, base release, hierarchy, complete GPU-word transport, native latitudes
and retained public compatibility URLs. Builds check and copy those exact bytes.
Missing, corrupt, incomplete or differently selected products fail the build.
Current source reviews and the accepted physical-class association are retained
in `data/current-build-context.json`; its preparation record is historical
provenance, not a claim that the current build reran scientific qualification.

## Prepare a reviewed update

Preparation and scientific acceptance remain explicit. Existing source,
incremental ownership, temporal-runtime and native-candidate producers retain
those responsibilities. Run only the producers affected by the reviewed change:

- `npm run data:prepare` for an intentional reference-geography update
- `npm run data:history` for historical source preparation
- `scripts/prepare-ownership-incremental.py` for reviewed ownership changes
- `scripts/prepare-ownership-runtime.py` for matching temporal runtime products
- `scripts/native-ownership/prepare-native-candidate.mjs` for a new native bank

After the native bank is accepted, prepare its deployment transport in a fresh
output directory, preserving the previous bank's immutable public URLs:

```sh
node scripts/prepare-startup-ownership.mjs --output /tmp/worldatlas-startup-next
```

The default reads the committed selection and current-startup predecessor. An
explicit reviewed candidate may be supplied with `--manifest REPOSITORY_PATH
--sha256 WHOLE_MANIFEST_SHA256`; `--previous DIRECTORY` selects its predecessor.
The command uses the existing native packers and exact-fragment restorer. It does
not compile geography, alter source products or replace current-startup in place.
Successor row and run transports use the selected manifest's existing
`ownership-vintages/<sha256>/` namespace; retained predecessor URLs keep their
original bytes. The fixed normative latitude-rule URL remains unchanged.
The completed index is written last; failed attempts cannot become a valid bank.

Review and commit the completed bank with its matching selection, current base
context, geography/audit products and affected prepared indices. Keep predecessor
source evidence and existing public URLs. Additive-only updates continue through
the existing accepted sidecar/envelope/four-asset path; the normal package checks
current owner/parent/geometry bindings, patch format and effective release without
replaying original source qualification. Actual emitted-asset runtime tests still
apply the patch against the prepared base and reject occupied-cell conflicts.

## Original reproduction

Original scientific artifacts, code, commands and release pins remain in Git at
their recorded vintages. Use those explicit reproduction entry points when
investigating or regenerating that historical result. They are not prerequisites
for packaging an already accepted current bank.

The initial current promotion reuses the successful
[run 38757451254](https://github.com/ChengshuLi/WorldAtlas/actions/runs/38757451254)
package artifact 11985611672. It does not establish new scientific or geographic
approval, and an ordinary build does not deploy or import content.
