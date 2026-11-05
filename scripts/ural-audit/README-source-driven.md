# Source-driven downstream divider

The downstream preparer derives its rule from the selected structured source geometry and scope. Category codes come from the selected registry. The verifier checks the generated output against the same selected inputs. The older hardcoded reconstruction and preparer tests have been retired; the D8 research tools are separate and unchanged.

Run the synthetic checks with `python3 -m unittest test_source_rule test_grid_origin test_delta_divider_apply` from this directory, with project dependencies available. Geographic source exports, attestations, and grid data are inputs and are not stored in this repository.
