# Research: source-backed archipelago components

These reusable research helpers resolve a pinned source polygon against a pinned physical-component grid. The label-aware OSM adapter validates the relation, non-geometric label member, source digest, reconstructed geometry digest, and expected identity tags. The all-center policy selects a component only when every land-cell center is inside the source geometry, and reports partially covered components separately. Source boundary/grid-center coincidences fail closed.

The selector receives source features and current-generation component streams as inputs. It does not accept historical mismatch cells as selectors and does not persist component IDs as decisions. Center coverage does not prove continuous geometric containment, complete geographic membership, source custody, or equivalence to historical input bytes. These modules are research components, not a publication or acceptance path. A supervised caller must authenticate and recheck inputs, guard resources, validate protected roots, and reconcile writer traces before treating a build as verified.

The source extractors are bundled beside the loader and are checked by SHA-256 before use. Synthetic tests contain no real source decisions or geography records. Run the focused suite with GDAL Python bindings and NumPy installed:

    OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python3 -m unittest discover -s scripts/v7-land/archipelago-containment -p 'test_*.py' -q

The mixed global build coordinator and its other dependencies are not included here; this directory is not a standalone whole-world build command.
