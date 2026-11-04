# Resumable 12-nautical-mile research band

This stage assigns water within 22,224 metres of the candidate physical-grid shoreline to the nearest candidate continent. It does **not** assign open water beyond that band, recover the historical V2 ocean partition, or include later named-sea or island exceptions. Spherical cell-edge distance and lower-code tie priority are documented approximations, not proven historical conventions. Preserved V2 is never a build input; use the separate comparison after candidate generation.

Copy `coastal-resumable-config.example.json`. Pin all five physical/land inputs, including the land report. Run:

```text
/usr/bin/python3 build_coastal_resumable.py CONFIG NEW_OUTPUT_DIRECTORY
```

The runner is single-worker. It uses an adaptive longitude halo and switches to full longitude where needed near the poles. The existing geometry routine checks that omitted shores cannot affect results; an uncertifiable tile fails rather than guessing. It locks the output directory and pins config, program code and inputs. Every completed tile has a report and hash-pinned spans. On restart with the same config, code and inputs, it revalidates completed tiles and runs missing ones; incomplete attempt directories are retained. Pass `--max-tiles N` for a controlled pause after N newly completed tiles. A complete batch emits `report.json` compatible with `compare_coastal_batch.py`. A partial run is not a completed global band. The default free-space reserve is 2 GiB and is checked at tile boundaries and during tile processing; concurrent writes or a single operation can still cross the reserve. Preserve or remove incomplete outputs only under the applicable retention rules.

Run tests from this directory:

```text
/usr/bin/python3 -m unittest -q test_coastal_band_adaptive test_build_coastal_resumable
```

A real-data run started on 2026-11-04 with 1024×1024 tiles and one worker, using the candidate land and physical streams; early north-polar tiles took approximately four to five seconds apiece, with 6,912 total tiles. Actual runtime is not established and will vary greatly with coastline complexity. The run may stop on resource or geometry guards; inspect the log and do not treat incomplete tiles as results.
