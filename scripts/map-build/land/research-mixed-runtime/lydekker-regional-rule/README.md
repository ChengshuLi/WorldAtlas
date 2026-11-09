# Lydekker regional land rule

The V8 regional stage uses this rule to assign whole physical components
against the selected line observation and source-backed group policy.
Selected affiliations take precedence over the line default. Named source
anchors can assign nearby components using WGS84 center-to-center distances.
The rule holds conflicting, crossing, or partially covered components for
review. It does not infer membership through chains of nearby islands.

The [V8 configuration](../../../pipeline/config.json) selects the regional
snapshot and its source data and code pins. The regional writer reads fresh
physical components and mainland streams from the same run.

The [policy preparation record](reproduction/README.md) traces the selected
island groups from source evidence through the local previews and Neon
registration to the V8 policy.

Run focused tests from this directory with Python, NumPy, SciPy and pyproj.

    python3 -m unittest discover -v
