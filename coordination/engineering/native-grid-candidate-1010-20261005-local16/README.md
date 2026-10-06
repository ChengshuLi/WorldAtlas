# Offline native ownership candidate for #1010

This second part prepares a separately versioned grid from original native longitude/latitude polygons. It does not select it in application defaults, alter original geometry or release history, install database content, classify physical water, or approve factual geography.

Run the exact committed preparation code with plain Node 24:

```sh
node scripts/native-ownership/prepare-native-candidate.mjs --repo /absolute/repository --baseline d55795e4c0ad01527029db0bd1d774124a12a61a --vintage world-one
```

Use a fresh vintage for a second run. The original numerical latitude table is an immutable repository input from the previous audit; no browser inverse projection is regenerated. Original ownership run assets are not inputs. Every original native feature, identity/parent crosswalk and retained topology partition is bound before generation. Outputs use `native-v1/ownership/` inside a new offline scratch vintage. Cumulative input/output admission retains the existing 256 MiB and 512-descriptor limits. The final review packet must independently account for all retained products; a reservation is not proof that it fits.

Controls:

```sh
node --test test/native-ownership-compilation.test.mjs test/native-preparation.test.mjs
```

These exercise actual codecs and decoded picking against independent integer orientation/half-space oracles, holes, islands, overlap precedence, split dateline pieces, collinear source equivalence, row/transport partition boundaries, high owner words, malformed rings/tables, two committed synthetic CLI runs, original crosswalk/topology binding, unchanged inputs, reused-output rejection and changed/injected-code rejection. Synthetic fixtures live only under the managed checkout’s `.cache` and are cleaned by the test suite. Full-world immutable runs, exhaustive decoded/native comparison, final evidence ledger and independent exact-head acceptance remain required.
