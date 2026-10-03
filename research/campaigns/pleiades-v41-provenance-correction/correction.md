# Superseding correction: Pleiades datasets v4.1 release pin

This correction supplements [the original Iberian Pleiades name evaluation](../pleiades-iberia-names-source/source-evaluation.md#release-license-method). It preserves that packet unchanged and supersedes only its incorrect narrative release-commit identifier.

## Correct release provenance

The original narrative says the v4.1 tag resolved to `c4423b89541d752792d84fab5d824c7a2db96a44`. That is incorrect: the GitHub commit lookup for that SHA returned HTTP 422, “No commit found for SHA.” The original source manifest already records the right release commit, `b6a6790f71c45e4a4ef60fce296c506f28f458bf`.

A fresh lookup of the upstream `refs/tags/v4.1` returned an object of type `commit` with SHA `b6a6790f71c45e4a4ef60fce296c506f28f458bf`. The commit API gives author and committer date 2025-05-28 and message “merging v4.1 preparation branch into main for release.” The original manifest records the release date as 2025-05-28. The exact tag-ref and failed-lookup response bodies, their hashes, and the resolved commit record are retained in this directory.

## Restoration verification

For all 25 selected records in the original manifest, I formed a raw JSON URL under the resolved immutable commit and retrieved it. Every URL returned HTTP 200. Each retrieved byte length and SHA-256 matched its original per-resource manifest entry exactly. Per-record URLs, actual and expected byte lengths, actual and expected SHA-256 values, and match results are in [`restoration-check.json`](restoration-check.json). The original per-resource evidence remains in [`the original source manifest`](../pleiades-iberia-names-source/source-manifest.json).

The pinned v4.1 [README](https://raw.githubusercontent.com/isawnyu/pleiades.datasets/b6a6790f71c45e4a4ef60fce296c506f28f458bf/README.md) states CC BY 3.0 and says content remains governed by individual contributors’ copyrights. Contributor lists already retained per resource in the original manifest continue to apply.

## Method and limits

The check resolved the tag through GitHub’s refs API; looked up both the correct and incorrect commit IDs; and fetched each of the 25 resources using the full resolved commit SHA. Hashes were calculated over response bytes and compared with the preserved manifest. The upstream commit record response is 46,464 bytes with SHA-256 `575cc055fd12b745ced4d89e7bf74826c6debf5e1ab3773ed5f4684d455d5143`; API endpoint and extracted details are recorded in [`source-manifest.json`](source-manifest.json).

This verifies tag resolution and restoration identity for these 25 resources. It does not validate the cited ancient texts, the underlying name attestations, the date semantics of Pleiades `start`/`end`, the historical meaning of any geography, or continuous name use. The source assertions and all caveats in the original evaluation remain unchanged. No geographic assignment or import was made.
