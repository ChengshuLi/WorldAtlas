`original-authority-quartets.json` supplies the stock modern compose `authorities` array in MEX, ECU, BOL, PER, COL order. Every entry has exactly `rule_preimage`, `source_authority`, `ledger` and `native_patch`, each with full ordinary Git pin fields obtained from actual local objects.

The first three pins retain country-qualified-authorities-001 at `673b20c77c5b1fd346bb0c846090c3661f8d1ddd`; each patch retains country-supported-inputs-001 at `db3801d77516795a6f9b09a241f1196cdc1ccd49`. Each patch pin exactly equals its original authority binding's `native_patch` field. The payload is 7,233 bytes, SHA256 `1104fab0dcd9c28772d4c7455cf5de281c6a5f6058769d6892c450b7d6471dd0`.

Copy the array unchanged into Main's fresh stock compose configuration, alongside its actual current `selector` pin and chosen `effective_release_id`. Those two Main-owned fields are deliberately not invented here. The ordinary entry point is:

```text
NODE24 scripts/prepare-delivery-handoff.mjs compose COMPOSE_CONFIG FRESH_OWNED_OUTPUT
```

`preparation.json` retains country order, source commits, output custody, the original summary pin and all five immutable held-original/scope-partition pin pairs. The source summary still records 3,884 held original cells, 22,669 Panama rights-blocked cells and zero accepted cells. This handoff does not reclassify those holds or treat the supported native qualification as accepted delivery.

No compose, scientific operator, final scientific review, fetch, author-repository edit, integration or publication ran. Normal Git operations on ChengshuLi/WorldAtlas remain user-authorized without repeated approval, subject to mandatory safety requirements; this preparation stays task-local.
