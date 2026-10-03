# Palette production verification — 3 October 2026

This directory owns the second and final permitted publication/evidence PR for issue 23. GitHub issue 23 and its canonical reservation are authoritative. Implementation PR 645 was actually squash-merged as `c5fce09842a0af2ae05cf6c611f012b6a71befff`; its exact historical/source audit remains in `../palette-contrast-20261003-7e91/`.

## Publication identity

- Existing private WorldAtlas Site: project `appgprj_6abdf87277c08191bce4a22b8dfb25db`, version 24.
- Exact pushed Site source: `2326792cc52fc353264abc33c2ac4e983fb2c3e5`.
- Native successful deployment: `appgdep_6ac14428eaac8191b59b5d3d8f05fb0d`.
- Native archive: 262,389,760 bytes, 539 files; SHA-256 `d06648cdc833b47020614be807d912e81904c2ccfc9ddbbc20e8cc4a33ada20d`.
- Uploaded archive: 262,410,240 uncompressed bytes / 186,358,149 gzip bytes; gzip SHA-256 `dbc36f8e482a5e7c7de284fddfe477e9d5959d1fbd469a6e3ca88de96710d94a`.
- The upload and native archive are separate receipts, not interchangeable hashes. All 539 packaged files matched committed Site-source bytes.
- Original migration SQL/snapshots remain intact. Only the existing 0000–0007 immutable legacy-D1 staging prefix was packaged; no provider DDL, baseline transfer, new factual import, audience or environment change occurred.

`native-publication.json`, `source-push.json`, `source-package-match.json`, `site-upload-budget.json` and `site-migration-staging.json` retain these separate receipts. `build-reuse.json` proves packaged application/prepared inputs equal the fully validated build. `publication-gate.log.gz` retains 581 unit tests, 15 geographic preparation tests, prepared parity and all 51 exact ownership buckets.

## Production attempts

`production-after.json` and `production-after-renderers.json` are the **failed first attempt**, retained without rewriting its outcome. The four date samples, two original profiles and GPU colors/modes passed, but reload failed after `/ownership/runs-54525952.bin.gz` returned HTTP 500 once. This is not a complete acceptance pass.

`production-first-attempt-status.json` identifies the failed request. Both bounded read-only probes in `production-asset-recheck.json` subsequently returned HTTP 200 with 798,580 bytes and SHA-256 `a82bfc28b4398ebe4febafbe2b939b7a70a9989c4aa9ee522c75ebb28cdddd3b`, exactly matching the packaged asset. No code or credential change was made in response.

The separate `production-after-recheck.json` and `production-after-recheck-renderers.json` record the full rerun. Their `completed` fields are authoritative for that attempt; intermediate checkpoints are not passes. Screenshot names identify the attempt and renderer. `acceptance-summary.json` confirms the complete rerun passed: 989 requests, all HTTP 200, both renderers and reloads, no page errors. It records both outcomes and all production evidence file hashes.

## Reproduction and limits

Use existing private access from native Sites `get_site`, supplied on hidden raw-TTY stdin to:

```sh
node --use-env-proxy scripts/verify-live-palette.mjs https://worldatlas-explorer.chengshu-li-2013.chatgpt.site data/engineering/YOUR-OWN-JOB/production.json after
```

Do not put a token in shell arguments, browser input, Git or logs. The fixed-origin GET-only parent proxy adds the documented private header server-side. The renderer child receives only a loopback URL. Use a fresh owned output path to preserve previous outcomes. This checks actual production client/assets/API, WebGL2 and forced Canvas fills/legends, four date samples, both profiles, all 14 modes, unknown styling, navigation ownership counters and reload stability. Headless Linux Chromium is not a physical mobile or human color-vision certificate.

Both source-supplied owner labels retain original category ID `owner:Q148`: Beijing resolves to “People's Republic of China” and Taipei to “Republic of China”. Presentation keys retain the original ID and source label; no factual owner or geometry is rewritten. The expected presentation colors are `#8430d8` and `#d84cf4`. The worldwide pinned source/raster audit and the palette's future-data/environmental-mode limits are documented in `docs/CATEGORY_PALETTE.md` and the first evidence directory.

## Rollback and serial resume

Site 23 remains the rollback: source `8aaeb86cdfe9fc49a3ca52c76151989ec994ece1`, saved version `appgprj_6abdf87277c08191bce4a22b8dfb25db~appgver_0656cd2f66a88191b43d0ff43852b85f`, deployment `appgdep_6ac132614ab08191b1dab4d525bdae4c`.

Read the latest issue 23/39 comments and `coordination/engineering/palette-publish-20261003-7e91.json` before resuming. Confirm the canonical claim matches worker `engineering-night-20261003-7e91f438` and claim `4406050d-c644-4160-99aa-e43c1d052fd3`; never create a competing writer. Settle all live verification outcomes before confirmed workflow renewal to `live_work=false`. Only then submit the final bounded evidence PR, incorporate latest main, pass exact-head scope/package checks, use the serialized squash queue, verify its matching bot result and actual merge, and release the completed claim. A queued request is not completion.
