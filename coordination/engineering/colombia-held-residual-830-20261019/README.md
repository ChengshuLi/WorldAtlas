# Colombia ADM2 residual 830: documented-unresolved exception proposal

References: [issue #2441](https://github.com/ChengshuLi/WorldAtlas/issues/2441), [accepted delivery PR #2459](https://github.com/ChengshuLi/WorldAtlas/pull/2459), and [prior request-only evidence PR #2553](https://github.com/ChengshuLi/WorldAtlas/pull/2553).

## Scope and accounting

The original `gb-COL-ADM2--repair-evaluation` contract covers 7,060 land keys in 3,575 original intervals and 81 owners. PR #2459's 6,230 supported/qualified outcomes are preserved. This residual packet covers the exact other 830 keys, touching 473 original intervals and 28 owners, in disjoint partitions A (424) and B (406). The 6,230 figure is prior supported/qualified outcome accounting; it is not a claim of new accepted repair cells.

The current packet proposes a documented-unresolved exception for each of the 830 held keys under the original contract's alternative of a qualified additive repair or a documented exception. Every key remains natively held with zero assignment while this proposal awaits independent exact-head review and explicit issue acceptance. Current totals are **830 held, 0 accepted exceptions, 0 accepted repair cells, 0 new repairs, and 0 owner changes**.

## Evidence and per-key dispositions

`per-key-unresolved-request.json` gives each key its exact original tuple, complete original source-index membership and IDs, exact original foreign raster contact, target negative-operand pointer, mapped-land-support run, native hold class, and target-level physical-result pointer. It replaces the old evidence request with a concrete proposed documented-unresolved disposition. The remaining question is whether the represented-vintage foreign contact has applicable source role for an exclusive assignment under the original contract. The proposal does not infer current sovereignty, legal status, or present applicability.

The complete retained evidence is `COL830-retained-contact-physical-witness.json` (Library `libfile_837b9799528881918c2b6a784edf1549`, version 0; 927,236 bytes; SHA-256 `9fd5fa35bbe2e77b0c7aca0ac1efa060748f81e8a058b3e2cdc97ab402beebe3`). It joins all 830 keys to the full original tuples and their exact source and physical evidence pointers. The 46-feature source membership remains heterogeneous. Each key has one retained foreign ADM1 raster contact among 10 features; each is present in its target's negative operand roster. The native diagnostic does not encode a separate per-negative per-key predicate. All 830 keys have a mapped_land_support coverage run. Those retained facts do not establish contemporary territorial applicability or qualify a positive repair.

The physical source is the retained whole-target body at `coordination/engineering/americas-original-repair-20261017/five-country-physical-001/physical-result-001/whole-target-support.json`, blob `114a89ea669bafbdcc67295d8470302111336d8b`, 27,539,267 bytes, SHA-256 `48a9748e5ca358808c6b7125b8ccbe156b4613d8c8a2f41074f047dc09a6dc9b`. Witness pointers preserve target-level query relations, support-pointset presence, and issue context. These are target-level facts, not claims that each held key intersects a physical pointset or passes/fails physical qualification.

The exact amendment instructions are preserved at `COL830-finite-documented-exception-amendment.md` (Library `libfile_2bc2144e8b4081918b9fbf588aa0a747`, version 0; 10,621 bytes; SHA-256 `ae090463eefa0a657cb84308ef99511012c7f6c195d5b8708b697e83a39c8d6c`). The original package manifest is pinned there and in the witness: `coordination/engineering/americas-original-repair-20261017/col/original-scope-001/package.json`, blob `f2a2726515da524ec2fd2794b23663b0870f4bd1`, SHA-256 `c07fe47b7dd3059a0d99ea18ad9a9ee3c41fa9c46de84fcdd8577dafa0cd83bb`.

## Current-owner observation status

The retained owner-observation artifact and full-package crosswalk are preserved byte-for-byte. The owner receipt records a prior full-scope run at main `79c78026412f3d70117c0ba75317a68684d710eb`, covering all 7,060 keys. It is historical evidence, not a new run for this amendment. The accepted input snapshot remains `509ce23692f902d4bad853801a9ae17d02c93475`; this branch is based on main `e69a8ff2f5380c336bae300f898f70175e2ea049`. A read-only comparison from 79c to e69 found two commits; none of the 55 receipt-pinned code, native, selector, or patch input paths changed. The comparison also includes unrelated package/tooling/test changes and a one-line deletion from `.github/package-inputs.json`, which is not one of the receipt pins. This packet does not rerun or reclassify owner outcomes for e69.

## Review and acceptance state

This is an evidence-backed proposal, not an acceptance receipt. All 830 keys remain held and unaccepted. Exact-head independent review and explicit issue acceptance are still required before any exception credit. No geometry/source survey, owner observation, repair constructor, or state change was performed for this amendment.

## Artifact pins

- Request (830 keys): 3,401,672 bytes; SHA-256 `ee0f373b7cc55845fa3d5b2de223f70de940e8793d0d615f60ca650dced1fcfb`.
- Partition A (424 keys): 2,741,628 bytes; SHA-256 `6eb9c1c5ac62c8662b84e261a887910902047f20323b522b03dda1eb6fdb53e0`.
- Partition B (406 keys): 2,600,846 bytes; SHA-256 `15112eabfe4178cff3e28891c2f1b5c4f80cb399e07062c3ab592aa71203d410`.
- Retained witness: 927,236 bytes; SHA-256 `9fd5fa35bbe2e77b0c7aca0ac1efa060748f81e8a058b3e2cdc97ab402beebe3`.
- Amendment handoff: 10,621 bytes; SHA-256 `ae090463eefa0a657cb84308ef99511012c7f6c195d5b8708b697e83a39c8d6c`.
