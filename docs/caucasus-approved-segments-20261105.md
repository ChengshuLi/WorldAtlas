# Approved Caucasus segment changes

The user approved the Anapa opening and the JAXA-product Abin divide. The combined boundary preserves both changes and remains a simple LineString with the original eastern endpoint. Its binary64 sorted compact GeoJSON SHA-256 is `3fe216ececc3e371de5722098885fe43cb21777481cb979870235cf89b14b2fd` (4,732 vertices). `caucasus_combine_approved_segments.py` checks both input pins and geometry topology before producing this result. The Anapa input comes from `caucasus_anapa_candidate_assembly.py`; the Abin input follows the procedure in `abin-jaxa-product-20261105.md`.

This line records an intermediate stage of the source construction. The
[V8 Caucasus replay](../scripts/caucasus-audit/CAUCASUS-WGS84-REPLAY.md)
rebuilds the selected 10,084-vertex boundary from raw inputs. The editable
boundary and region are in the `v8-mainland` Neon revision. The V8 runner
validates the closures against the physical grid produced in the same run.
