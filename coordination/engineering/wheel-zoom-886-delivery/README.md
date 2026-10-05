# Wheel zoom #886 live delivery and preserved failed attempt

The implementation is merged in PR #893 at primary `59f0e6b155d17e42880e0750c19aa9789f70b7d2`. Reviewed authored head `8eef902fbab9a6c9e7eafc5d0df8b3050a0e94ce` passed hosted packaging, all three full-regression shards and the normal queue's combined-tree tests. Its original wheel observations, failures, controls, source vintages and physical-device limits remain in `coordination/engineering/wheel-zoom-886/`; this checkpoint does not replace them.

Delegated publisher operation `2a2ac472-32ef-45db-ae9c-746a52fa6ee1`, GitHub deployment `6853129750`, attempted Worker `2a01cf68-a1f8-4870-b1ac-ff7aa4a494d8`. All 378 non-UI package files and the backend/config were byte-identical to the previous verified publication. The publisher found HTTP 503 from the data API and independently captured HTTP 402 from the restricted app-role `SELECT 1 AS ok`: “Your account or project has exceeded the quota. Upgrade your plan to increase limits.” This generic error does not identify storage, compute or transfer as the exhausted allowance. No new live wheel benchmark or whole-app acceptance was completed.

The publisher restored Worker `2c711f51-eb21-43d2-9047-d50d6714c02b` at 100%, provider deployment `5a30a63a-1d92-4bff-af13-4bde89a58e03`, and settled the operation as failed. The publisher's failure and rollback JSON files here are byte-for-byte copies of the original sanitized receipts. `independent-public-readback.json` is a separate author observation after rollback: prior HTML, JavaScript and CSS hashes match; both the release and one-record snapshot API reads remain HTTP 503. Restoring the prior Worker restores code/assets, not Neon availability. No SQL/object/source/billing/credential changes or information deletion occurred in this work.

Original receipts:

- [Source merge](https://github.com/ChengshuLi/WorldAtlas/pull/893#issuecomment-5989590794)
- [Exact-head independent review](https://github.com/ChengshuLi/WorldAtlas/pull/893#issuecomment-5989290626)
- [Publication failure and rollback](https://github.com/ChengshuLi/WorldAtlas/issues/886#issuecomment-5989673505)
- [Failed-settled Cloudflare result](https://github.com/ChengshuLi/WorldAtlas/issues/886#issuecomment-5989673863)

The provider's generic SQL error is preserved without reinterpretation. In the authorized ENG neon chat, the user subsequently pasted: “You've used all of your monthly network transfer allowance for this project.” `quota-identification.json` retains that later report and its provenance. This identifies transfer as the account-reported blocker; it is not a management-API measurement of the usage amount, billing dates or which operation consumed it. Shrinking stored data does not reset transferred-byte usage. No attribution to the wheel fix or a particular test/export is inferred.

## Fresh successful delivery after plan upgrade

The user upgraded Neon, and independent bounded release/snapshot GETs returned HTTP 200 again (post-upgrade-public-preflight.json). The designated publisher registered a fresh operation b1958782-e408-400c-bc5a-0149cfd37cc6, GitHub deployment 6853304833, primary 4a1fc6777fe766dca2c0698362a06f06a44f9344. Worker f46f5cdd-58f5-41cd-abee-cb5b41c2106d serves at 100%, provider deployment de99de3e-4dd1-4c01-9728-f3b29a979565. The original failed attempt remains failed; its receipts above remain unchanged.

The publisher retained package/provider/map-host/result receipts and GitHub comment bytes here. Only HTML and the main JavaScript/CSS differ from the previous package: all 378 other asset files and backend/config remain byte-identical. Release6/revision3051 and release hashes remain unchanged; public reads work without login and writes remain disabled. The 2021 snapshot contains all396 current attribute rows. This verifies delivery preservation, not historical completeness or full old-archive parity. The original Site/storage, rollback UI bytes and Worker version remain preserved.

- [Successful anonymous API/assets/data readback](https://github.com/ChengshuLi/WorldAtlas/issues/886#issuecomment-5989805566)
- [Fresh verified publication result](https://github.com/ChengshuLi/WorldAtlas/issues/886#issuecomment-5989806012)

## Actual-host browser acceptance

Fresh isolated Chromium153 contexts on AppleM1/macOS, ANGLEMetal, 1440x1080/DPR1 and no artificial CPU/network throttle ran sequentially against the public URL. ForcedCanvas was measured separately. No user browser/profile/CUA was used. independent-success-readback.json pins the provider100% Worker and exact served HTML/JS/CSS hashes during acceptance; each wheel receipt captures script URLs and reference asset hash. Neither browser run writes SQL or object storage.

Both live-metal-after.json and live-canvas-after.json retain all eight warmed wheel samples, raw events/rAF/transform/counter observations, requests, errors and machine conditions. Their adjacent compressed DevTools traces and screenshots are retained. All16 samples meet the pre-existing targets.json response/frame bounds: first observed transform15.4–32.8ms, p95rAF16.7–16.8ms. All camera samples retain zero ownership compilations/uploads and zero new requests. NativeGPU frame identities reach zoom1→13 and13→1 within eight120px notches; Canvas cached-grid sampling strides reach 512→1 and 1→512. High-resolution input and rapid reversal are included. All declared p95 frame targets passed in these fresh runs; one Canvas reversal rAF gap exceeded 34 ms (frames_over_34ms=1) and remains in the raw receipt. the earlier Canvas33.3ms and softwareGPU misses remain in the original evidence packet and are not erased.

live-metal-app.json and live-canvas-app.json each passed all14 modes while wheeling, superseded2020/2021 requests with final2022, London six-tier inspector, hover/click agreement, home, resize and unchanged ownership counters with no browser errors. The merged controller's positive/negative timing controls were rerun and retained here; unit normalization/time-smoothing checks pass. Original real-Leaflet controller fixture/review evidence covers pointer anchor≤1px, cancellation, keyboard/buttons, modifier bypass, line/page deltas and lifecycle.

Numbers are browser proxies with synthetic trusted wheel input, not photon latency, universal60FPS, physical-device or mobile certification. Metrics are archived to their actual deployed primary4a1fc677 rather than relabeled as the evidence PR's earlier baseline59f0e6b. The implementation and data are unchanged by this evidence-only PR. Issue886 can close after exact-head review, applicable CI and normal merge of this final proof; successful deployment is already separately registered. Old archive migration remains a separate tracked task.
