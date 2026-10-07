# West Siberian packet preservation and statutory erratum

This is a new, isolated evidence vintage for issue #1092. The original 2026-10-06 assessment, issue contract, controls, source register and reproduction receipt remain byte-for-byte unchanged. This erratum derives its 45 rows from the original pinned assessment and uses its exact scope contract; it does not alter IDs, geometry, earlier statements, or source-era dates.

## Added evidence

On 2026-10-07 a verified HTTPS request (HTTP 200) retrieved the legislature-hosted consolidated text of Khanty-Mansiysk Autonomous Okrug Law 63-oz. The 2,601,738-byte PDF SHA-256 is `b8dce42fc4527a0d7fee004897a21a324c54b042f09083b165c50415c9236834`. Its title page lists amendments through 2025-05-30; PDF metadata is dated 2025-06-11. Article 1 (pages 1–2) lists all eight city-named HMAO subjects in this batch as municipal urban okrugs. The PDF says its law appendices are not included. This confirms municipal form in that dated text, not Atlas administrative-tier equivalence, current 2026 legal status, or boundary geometry. The file is not redistributed because separate reuse terms for the generated PDF compilation were not verified. Exact source URL, restoration instructions, byte count and hash are in `source-register.json`.

The eight subjects are Nefteyugansk, Nizhnevartovsk, Raduzhny, Uray, Nyagan, Kogalym, Khanty-Mansiysk and Pokachi. Their findings remain `insufficient-evidence`; source-role strings and geometry are unchanged. No legal boundary annex or official polygon was inspected.

## Safe reproduction

Run `verify-erratum.py` once from the repository root using the recorded Python 3 runtime. It uses a new dated output vintage and refuses a reused, occupied, symlinked, original or escaped destination. It checks the immutable original assessment and issue contract before any write, performs the source-roster positive and negative controls plus input-tamper and destination-safety controls, and launches two independent generator processes into fresh directories. `reproduction-result.json` binds the evaluation commit, interpreter/runtime, execution-code and input hashes, and exact product hashes from both runs. Then run `finalize-receipt.py` once; it independently rechecks the immutable run products and writes the schema-bound `reproduction-receipt.json` without modifying either run or the first receipt. Equal assessment/scope/control product hashes are observations from those actual runs; run-specific execution receipts are kept separate.

The output directories are immutable receipts. Do not delete, edit, or rerun into them. A later reproduction needs a separately reviewed new date-vintage and corresponding source/evidence manifest update.

## Remaining limits

Verified Rosstat HTTPS requests for the federal OKTMO catalog and regional municipal lists failed certificate validation with both the system trust store and bundled certifi CA list on 2026-10-07; certificate checks were not bypassed. Other row-level legal/statistical material is still partly search-extracted and has no retained source bytes. All nine multipart subjects still lack complete authoritative component-level geometry checks, including island/separated-area completeness. The HMAO law PDF itself omits annexes and may have later amendments. Physical class, cause, Atlas tier mapping, current boundaries and source reuse remain unresolved wherever the evidence does not establish them. No geometry change, import, certification or publication is authorized.
