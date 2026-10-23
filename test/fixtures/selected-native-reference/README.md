# Selected native reference fixture

These four retained fixture bodies are byte-identical to the former
`coordination/engineering/vietnam-selected-native-reference-install-20261016/test-fixtures/`
files at accepted commit `0e50bd281afec27ce32fac8dcb4dfe2401f94b6c`.
Their original scientific provenance is recorded in `provenance.json`; moving
this test-only fixture does not regenerate or approve a native product.
The historical packet and its exact reproduction remain in Git history.

The installer test discovers the current entry point's eager module dependencies
through the existing static-module fixture helper. Static JSON imports are leaves,
not authority. The test still explicitly constructs its synthetic registration,
source/data pins, and adverse inputs; dynamic imports and other file operands
are not inferred. Keeping these retained assets in the canonical fixture directory
lets both focused and complete checkout preparation include the same inputs.
