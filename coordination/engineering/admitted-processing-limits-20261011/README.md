# Current reader resource allowance

Refs #1745. This correction separates a current readback's admission from the historical producer's authenticated limits. Historical request, facts, operating receipt, result identity and scientific predicates retain their existing checks. Current whole-member/decompression and descriptor bounds remain unchanged.

The current allowance uses Node's available-memory observation, subtracts the coordinator-provided `WORLDATLAS_CONCURRENT_RESERVED_BYTES`, 2 GiB parent headroom and 768 MiB margin, and reserves half the residual. The reader checks actual process RSS before phases and ordinary acquisitions. The coordinator must serialize admission and supply other active reservations; this is cooperative protection rather than a global hard memory quota. Existing external supervisors still enforce their own issued limits.

Readback charges the authenticated actual four-product union against this current allowance. Completed serialization restores the caller's output reserve on both success and refusal, retaining the recorded peak. Returned live data remains charged by the caller's metadata.

Observed failures motivating this boundary:

- Hosted trusted 1098 reader refused a native row-table phase under the fixed 256 MiB logical cap (run 38178266635, job 114585212437).
- Cloud 1098 baseline diagnostic refused earlier in original native authority acquisition; Node/Python/Git runtime bodies alone total 160,967,176 bytes. This is distinct from the hosted failure.
- Current13 assembly 002 reached readback then compared its current live frame against the original producer's 245,679,353-byte child limit. The original rebind remains qualified and is reused unchanged.

The independently exercised stale-reserve defect is real, but exact attribution of the hosted failure to it is not established. Genuine corrected baseline/current13 proof and normal applicable gates are required before adoption. This code freeze does not itself claim those proofs.

Producer/issuer/supervisor parameterization is deferred; their bodies are unchanged. Exact catalogue migrations preserve existing entries and require independent review of this complete consumer correction.
