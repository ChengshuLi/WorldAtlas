# Exact original-source point diagnostics

`scripts/evidence/exact_predicates.py` supplies bounded exact point predicates and
original-segment crossing certificates. It uses Python's standard library, with no
projection, GEOS overlay, snapping, geometry repair or owner assignment. Exact means
rational arithmetic over the unchanged finite IEEE754 binary64 coordinates supplied
by the caller. It does not mean exact projection, source accuracy or ground truth.

The read-only CLI accepts a version-1 JSON request and creates a new output only:

```sh
python -B scripts/exact-source-diagnostic.py --root /path/to/source-root \
  --request /path/to/request.json --output /path/to/new-diagnostic.json
```

A request declares `context` containing `crs`, `axis_order: ["x", "y"]`,
`numeric_vintage` and `coordinate_encoding: "IEEE754-binary64"`. Each whole-file
source descriptor repeats the identical context. No CRS aliases, transforms,
axis swaps or differing numeric vintages are guessed. The caller must establish
that the declarations describe the actual original sources; hashes alone do not
establish truthful source metadata.

`collections` has exactly `gap`, `first`, and `second`, each with a `provider_id`
and complete `member_ids` roster. `files` lists original GeoJSON Feature or
FeatureCollection files using relative `path`, whole-byte `bytes` and `sha256`,
`role`, `provider_id`, and `context`. Every original feature must have its original
string `id`; every feature in every declared file is retained. The complete actual
roster must equal the declared roster, without duplicates or omitted members.
Changed original vertices fail the whole-byte pins. A differently pinned source is
a different input; consumers must preserve the predecessor's request and results.
Missing, malformed, nonpolygon and invalid geometries remain explicit unknown
member evidence. Every matching provider/member ID is retained.

`points` lists unique string `id` and two-number `xy` values. Results distinguish
inside/outside/boundary on unchanged original segments, retain hole boundaries,
and report the symbolic strict-gap classes `first-only`, `second-only`, `both`,
and `neither`. A boundary on any original member remains a boundary diagnostic;
unknown members prohibit a definitive four-class result even when another member
is known to contain the point. Both/neither carry source-overlap/source-uncovered
ambiguity. Outside-gap points are recorded. These classes are source-point evidence,
not affiliation, full-cell/component coverage, water, authority or ownership.

Optional `crossings` entries contain `first` and `second` references to the
byte-verified original collections: `role`, `member_id`, `source_sha256`, and
zero-based `polygon_index`, `ring_index`, `segment_index`. The CLI resolves actual
original endpoints and constructs IDs from provider/member/hash/index provenance;
caller-supplied substitute endpoints cannot enter these certificates. An optional
`exported` point is tested exactly. The lower-level `segment_certificate` primitive
accepts explicitly supplied original endpoints/context and provenance IDs; callers
of that primitive must separately establish byte custody.

Certificates retain original segment IDs, exact rational intersection parameters
and nodes. Non-dyadic nodes cannot be exported as exact Float64 pairs. The nearest
pair is displayed only as a tested approximation; `export-incidence-failure` is
preserved when either original incidence fails. Exact dyadic crossings can pass
this local incidence test, which does not approve a polygon mesh or the existing
#972 acceptance contract. Parallel disjoint and collinear contacts have distinct
disjoint/unsupported outcomes.

The unchanged reader limits are 32 MiB per ordinary file, 256 MiB total and 512
source descriptors. Additional conservative runtime limits are 512 members,
1,024 original segments per geometry, 250,000 topology pairs per geometry, 4,096
query points, and one million point/segment checks. Exceeding these limits produces
an unsupported diagnostic rather than unchecked containment. Ring topology is
checked exactly; no original vertex is removed. Self crossings, nonclosed rings,
zero-length/zero-area rings, misplaced/nested holes and overlapping multipart
interiors are invalid. Multipart boundary contacts are conservatively unsupported;
this helper does not claim to support every valid OGC contact configuration.
It intentionally cannot yet process the full private Portugal–Spain originals.

Controls live in `test/exact-source-predicates.py`. They include integer triangle
(1/3,1/3) export failure, exact dyadic crossings, analytic inside/outside/boundary
points, holes/reversal/multipart/tiny polygons, overlapping members retaining all
IDs, unknown members, altered bytes/rosters/CRS/vintages, degenerate/nonfinite
inputs and immutable two-run CLI output. A full rational face arrangement, new
geographic storage format, materialized-face approval and geography repair are
outside this helper's scope.
