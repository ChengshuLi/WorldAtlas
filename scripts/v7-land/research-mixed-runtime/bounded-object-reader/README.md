# Bounded object reader: research prototype

This reader is a research component, not an admitted source gate or a map-builder release. The caller must authenticate object identities and verify exact sizes and hashes. It does not validate geographic data or make an existing gate's guarantees.

It launches an explicitly configured official CLI without a shell, permits only caller-authorized keys, limits each read, enforces idle and object-read deadlines, and cleans up the launched process group. A failure returns no successful stream. Raw CLI stderr is discarded to prevent unbounded diagnostic storage and accidental disclosure.

The environment, CLI, credentials and manifest admission remain caller trust inputs. Deadlines cover blocking reads and the post-EOF wait, not an independently enforced bound on all process memory, total disk or caller work. A descendant that deliberately detaches from the process group is outside the cleanup guarantee. The caller must keep its requested materialization block size within the reader limit.

Fifteen bounded tests passed, including local stalled/descendant process checks. A small real object was read successfully and matched its expected size and hash. Full-tile streaming, production admission, and end-to-end geographic replay remain under test.

Run the synthetic tests with `python3 -I -S -B test_r2_stream.py`.
