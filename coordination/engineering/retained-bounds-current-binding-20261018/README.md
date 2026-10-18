# Retained bounds: historical producer and current execution

This revised design supersedes PR2485's initial full-current-module hash-pair proposal. That proposal unnecessarily coupled bounds applicability to unrelated native-grid/storage changes. The historical/current identity split is retained; current broad-module compatibility allowlists are removed.

Engineering candidate only. No Uruguay applicability, physical or native evaluation was run. Uruguay's 3,242 original cells (2,982 land, 260 water; 13 owners) remain unactivated.

## Actual consumed dependency contract

`scripts/retained-coordinate-bounds.mjs` exports the reusable pure `dense-json-whole-primitive-bounds-v1` contract. It has no imports, storage, hashing, scanner or I/O dependency. This caller invokes it only on JSON.parse-produced whole geometries. It checks whole Polygon/MultiPolygon shape, dense arrays, finite geographic coordinates, ring length/closure and conservative antimeridian bounds. Finite coordinate equality preserves the historical JSON hash's signed-zero semantics. Sparse or embellished arrays are outside this declared domain and refuse.

The original task caller is preserved at commit29a972b5e56c03baf351da5f90401018b1c3dc71, under `coordination/engineering/americas-following-original-evaluations-20261018/foreign-applicability-001/ury-binding-evidence-001/caller/derive-declared-scope-applicability.proposed.mjs` (blob52e794affb33cadd03315fd620cc4db77ea9657d). Its `method_commit` overloaded historical producer identity and current execution identity. Relabeling it or suppressing its checks would be wrong.

The revised caller retains `method_commit`, authentic old completion/config/driver pins and complete historical dependency custody. `retained_code_closure` must equal the immutable descriptors in the authentic previous producer config (only task materialization paths may differ), and each body is tree/OID/size/SHA authenticated. The audited historical helper/grid hashes identify that retained producer; they are not a list of permitted future current files.

A distinct `execution_commit` equals `accepted_commit`. The focused `current_bounds_module`, native selector/manifest and new `execution_package` are bound to that exact commit. The complete current `code_closure` is rooted at `scripts/retained-coordinate-bounds.mjs`, recursively authenticated and checked against its exact materialized import layout/package context. Today that closure has one pure module. Future imports cannot silently bypass closure authentication. The original `method_package` stays historical. The receipt records both identities, the actual current module SHA and the binding-module SHA.

The current broad neighbor helper and native grid are not executed by this adapter and are not current compatibility dependencies. Historical Fiji equality evidence remains tied to its original execution and unchanged original transports, manifest, latitude/proof operands through the existing downstream guards. No current scanner replay or numerical equivalence claim for unrelated scanner changes is introduced.

## Config migration

Prepare the existing v2 task config with additional mandatory fields: `execution_commit`, `retained_code_closure`, `inputs.current_bounds_module`, and `inputs.execution_package`. `code_closure` now describes only the actual focused execution closure; every task_file follows a common root plus its repository path, with package.json at that root. Preserve the authentic old `method_commit`, previous completion/config/driver and historical method_package. Remove obsolete current helper/grid inputs. No ready-to-run Uruguay config or execution authorization is supplied here.

## Evidence and limits

The 13 published whole selected features equal acceptedc893 part25; selected bank/world index/part25 bytes are unchanged from stage7e78. Original geometries are not rewritten. Historical OSM/Wambacher ODbL provenance, stated2017 data with later publication/conversion, CRS84 and Artigas#927 limits remain. A historical Python runtime inventory cannot authenticate a future current physical invocation.

Eight focused tests use actual immutable historical helper/grid code to compare the pure operation across valid polygons, multipart/seam/extreme/signed-zero cases and malformed-input refusals. They check historical completion/config/driver/closure mutations, current identity mismatches and the dependency-free contract. Fixture provenance is in `test/fixtures/retained-bounds-code/manifest.json`. The tests do not run the Uruguay dataset, physical producers or native qualification. No selected data, package declarations, workflow or broad consumer refactor changes.

Validation: `node --test test/retained-bounds-code-binding.test.mjs`; `node --check coordination/engineering/retained-bounds-current-binding-20261018/derive-declared-scope-applicability.mjs`.
