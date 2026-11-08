# Regional decision export

`export-v3-line.local.sql` reads the named regional decision revision and
includes its line observations, source versions and entity assignments.
Supply the `revision` parameter through psycopg on a read-only connection.
The V8 pipeline reads the selected regional snapshot using the pins in its
[configuration](../../../v7-pipeline/config.json).
