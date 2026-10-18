# Uruguay caller binding evidence

Read-only handoff from the existing `ury-foreign-inputs-001` preparation. No code or config was changed, and no caller, native, or scientific operation was run.

## Verified mismatch

The frozen Uruguay caller is `coordination/engineering/americas-following-original-evaluations-20261018/foreign-applicability-001/derive-declared-scope-applicability.proposed.mjs`, copied into `ury-foreign-inputs-001/derive-declared-scope-applicability.mjs`. Its immutable source is commit `32d819ddc9333ff025584665665c963822dfcead`, blob `52e794affb33cadd03315fd620cc4db77ea9657d`, 25,506 bytes, SHA-256 `7d0b6ecd222b52a8701a6b11ddbcd34b06e8e47dd58b3c958b1a7a9c9c770e66`.

At caller line 105, the guard is:

```js
need(config.inputs.current_native_grid.git_blob_oid===closure.get('src/native-grid.js').git_blob_oid,'Normative native grid changed');
```

The current pin is accepted main `7e78edd0dba65dd6d904e04186f0b6b36d2a4ba6`, path `src/native-grid.js`, mode `100644`, blob `811966bb79e8903037a24a47ada0a408f2c972d2`, 53,003 bytes, SHA-256 `f8691d492770fd8131f5e8341adacbf33b17625c6d735ccb1460cde3213a37cf`.

The retained method closure is `2d1fc6f430e756498908bf2c4e267356a13f5cc7`, same path and mode, blob `3e1d3e7e6012b5b571345caad029ab7d124c07fd`, 50,250 bytes, SHA-256 `66b453bbb2e001b9ff56bd754d55087f5919845dceeefd886016494cefa1d3e0`.

Thus the existing config’s current pin and the caller’s historical closure pin differ as whole-file identities. The guard refuses before the scientific operation. That refusal is not itself evidence that the normative coordinate grid changed. A local read-only diff between the two immutable revisions shows code changes in geometry-array handling and allocation/scanning paths (including `verifyNativeSeamView`, `nativeRuntimeIndex`, `polygonParts`, `deriveSourceTargetNativeDelta`, and `primitives`); the files are not byte-equivalent, so no equivalence is inferred here.

## Existing immutable evidence

The pending config already records the two identities above and the accepted code context. It also pins the accepted native contract inputs:

* `coordination/engineering/arctic-three-retained-land-fit-repair-native-20261008/native-v9/manifest.json` at `7e78edd…`: blob `31d970d0fe2bf8c899f020aad09a3826ea451790`, 252,447 bytes, SHA-256 `d9954fa51d18e4ce785679f920e4b6ac1ebd3cf07ce03fa7e7e674cb2a42faba`. The same path/blob is present at the retained method revision `2d1fc6f…`.
* `data/ownership-selection.json` at `7e78edd…`: blob `c92ec39f7d8c3896cdf87b558f021d230a3cb5df`, 1,849 bytes, SHA-256 `a4b26ec501d4ff52217c59ede2b26d0bc15e128bb843e06e04e295c038447e7e`.
* For comparison, `data/ownership-selection.json` at retained method revision `2d1fc6f…` is blob `1722ef4be3df1a52f589535fe0ac6fb9da27ea85`. The selection file identity also differs between those revisions; the accepted-current selection pin is explicit in the pending config.
* The historical closure’s `src/native-grid.js` above, plus its other complete code pins in `ury-foreign-inputs-001/adapter-config.pending.json`. The retained caller requires the exact historical closure and package context before comparing its coordinate helper and grid with accepted current code.
* The exact reviewed prior result inputs are pinned in that same config, including the complete prior result at `b6900b2fe487f3971045b63fb51c39dd30e013f3` and the retained method commit `2d1fc6f…`. These establish the historical method/result vintage; they do not update it to accepted-main code.

The caller already compares the old and current `coordinateBounds` export bodies byte-for-byte at lines 102–104. No corresponding method-equivalence evidence is encoded for `native-grid.js`; the existing guard is whole-file blob equality. The accepted 7e78 file and its immutable review/CI history are available as the current-code evidence, while the retained 2d1 file and prior-result pins preserve historical provenance. Neither fact alone supplies a new binding rule.

## Decision reserved for root

Root/cloud must decide whether and how a legitimate caller revision can bind accepted `7e78` while preserving the old method/result provenance and the native-grid behavior required by this route. This handoff does not recommend bypassing the guard, substituting the old blob as current, or claiming semantic equivalence from unchanged manifest metadata. No Uruguay physical or native evaluation has been performed; its prepared 3,242-cell scope remains unqualified and unaccepted.
