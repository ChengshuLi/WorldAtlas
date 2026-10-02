# Source-policy corrections in coverage

The coverage dialog lazily reads `source-policy-corrections/summary.json` alongside its existing reports. This 41,705-byte projection retains the three effective policy descriptions, every affected location ID grouped by its actual source role, and bounded source facts and links. It is independent of map geometry, dated records and the canonical grid. The full correction evidence remains in the compressed Git artifact.

`selectedSourcePolicyRoles()` counts IDs from the actual selected features, after the existing `coverageScope()` continent/territory filter. Spain therefore shows 333 agricultural adaptations and 39 municipalities in Europe, and 8 adaptations and 4 municipalities in Africa. Country-wide totals are not substituted for continent selections. The existing hierarchy progress, selection counts and review decisions remain unchanged.

Corrected descriptions show the installed role and its selected counts. Original descriptions and corroborating source facts are in a collapsed evidence section; contradictory source metadata is separately retained. The UI explicitly says that boundaries and location scale remain under review. If the projection cannot load or its policy assumptions fail validation, coverage remains available with a visible earlier-review notice; reopening retries failed transport. No silent substitution occurs.

Development serves the exact `/source-policy-corrections/summary.json` route. Static publishing copies the same nested asset path. Neither requires publishing the full original source receipts.

## Reproduce and verify

```sh
python scripts/prepare-source-policy-summary.py --check
node --test test/coverage-source-policy.test.mjs test/source-policy-corrections.test.mjs
node --test test/coverage-source-policy.browser.mjs
```

Regenerate the bounded projection explicitly with `python scripts/prepare-source-policy-summary.py` after a reviewed full-bundle revision. The producer preserves a source-bundle hash and rejects output over 80 KB. Fresh clones need no scratch files or live source requests. The standalone browser test exercises the real coverage module, asset transport, failure/retry, selected counts and evidence disclosure without waiting for a full map build.

## Future global-review producer integration

The three existing review producers are deliberately **unchanged**. Their retained source-policy objects, input hashes and frozen semantic inventories describe their original inspections. Runtime corrections do not retroactively rewrite those observations or close any branch. Root integration must validate all six follow-up ledgers before authorizing regeneration of these products.

For a future reviewed regeneration, import the already tested helper:

```python
from source_policy_corrections import load_effective_source_policies
```

Then use these exact policy lookups, preserving the unchanged base-policy file:

| Producer | Existing lookup | Future effective lookup |
| --- | --- | --- |
| `scripts/review-world.py` | `policies=read(D/'location-policy.json')['countries']` | `policies=load_effective_source_policies(R)['countries']` |
| `scripts/review-granularity-global.py` | `policy=read('location-policy.json')['countries']` | `policy=load_effective_source_policies()['countries']` |
| `scripts/review-global-semantic-closure.py` | `profiles = load(data / 'location-policy.json')['countries']` | `profiles = load_effective_source_policies(data.parent)['countries']` |

The helper checks the original or previously corrected policy objects exactly, rejects unrelated policy edits, preserves `retained_administrative_selection`, and leaves source dates and geometry unchanged. Its JavaScript counterpart is `effectiveSourcePolicies()`. Python/JavaScript parity is tested.

Retain `level` whenever code expects an original source administrative layer such as ADM3. Use `effective_level` only when presenting the installed geographic/functional source role. The corrected `role` describes actual installed units; it is never sufficient to assign an atlas tier or certify local granularity. Keep contradictory source metadata as source observation, not an effective classification.

Before writing any regenerated review, explicitly add `source-policy-corrections/europe-v1.json.gz` and the effective-resolver code to that product's input fingerprints. Record the correction ID and evidence IDs for corrected profiles, retain original descriptions as context, and leave all unresolved semantic statuses unchanged. Per-location effective roles require the bundle's keyed annotations with matching ID/footprint evidence; a country label alone must not relabel a retained municipality as an agricultural district. Current active geography, registry and frozen history must remain unchanged. Refreshing a source-role annotation is not an identity or history migration.
