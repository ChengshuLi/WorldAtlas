# Water decision export

`export_draft.py` exports a named Neon draft and its matching entity revision in
one read-only transaction. It includes the selected water features, basin
participants, routes, ocean seeds, policies, category bindings and the raw
source records they reference.

Use psycopg 3 with a read-only Neon role and standard libpq connection
variables. The exporter requires TLS certificate verification.

    python3 scripts/v7-decision-export/draft/export_draft.py \
      --revision REVISION --out NEW_FILE.json

The exporter writes a new canonical JSON file and prints its SHA-256.
Use the [V8 pipeline guide](../../v7-pipeline/README.md) for the selected build
inputs and rebuild command. The mainland preview uses its
[own revision query](../../v7-land/mainland-l2-draft/README-selected-stage2.md).

Run the synthetic checks from this directory with
`python3 -m unittest -v test_export_draft.py`.
