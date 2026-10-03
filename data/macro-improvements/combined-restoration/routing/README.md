# Candidate named-land routing crosswalk

Issue #45 evidence, recorded 2026-10-02 (America/Los_Angeles). This package accounts for all **135 original named-land routes**, matched exactly once to the supplemental source evaluations: #41 (25), #42 (64), #43 (46). It also retains #44 physical-boundary uncertainty and the finite staged corrections from #501/#502/#503/#505/#506.

**The candidate is not published.** At packaging, the published Site version was **19**, geographic release **3**, with 49,589 locations. The proposed composition has 34 new locations, six retained-ID footprint corrections, three present-day location-name corrections (including the separately proposed `PCN+00?` → Henderson label), two province-name corrections and eight new geographic groups. It would contain 49,623 locations if separately validated and published. No current macro certificate, regional handoff, canonical grid, live record or GitHub issue pin is changed by this package.

Thirteen regions have proposed location changes. Japan is the fourteenth affected **neighbor context**: the finite Marcus/Minamitorishima source polygon is explicitly excluded from Japan and included in Northwestern Pacific → Micronesia → Oceania. This reciprocal source-backed amendment changes no other Japanese island, mainland edge, EEZ or nearby Pacific domain. It requires the designated publisher to update both contexts, member-derived envelopes and matching certificates/release pins together.

The ledger preserves source/archive byte hashes, supported modern intervals, source licenses, whole-location parent chains, source attempts that failed, and staged-versus-held status. **Kingman Reef and Gardner Pinnacles remain representation holds** because their sourced dry land contains no canonical grid-cell center. Do not enlarge source footprints or assign arbitrary cells to conceal that limitation. Chagos remains partial beyond the compared Diego Garcia/Salomon domains; corrected Manuae/Aitutaki labels do not close their incomplete whole-atoll footprints.

Archived query windows, coastline rings and named-source comparisons are finite. They do not certify every archipelago member, a complete worldwide shoreline, lower-tier semantic approval or historical attributes. GSHHG comparison is dated 2017; buffers diagnose offset rather than prove current geography. The #44 reconciliation proposes zero reparentings, with 49/570 candidates still lacking sufficient physical-reach evidence. Previously approved own macro-routing conventions remain distinct from unresolved coverage and interior work.

## Files and reproduction

- `routing-status-crosswalk.json.gz`: complete original-route/source/status crosswalk, pinned supplemental inventories and correction evidence.
- `validation.json`: immutable archive/decoded hashes and bounded acceptance counts.
- `reproduce.py`: read-only validator and crosswalk reproducer from repository source files. Source paths are repository-relative and pinned to immutable git blobs; a later published file can be recovered from the recorded git commit when its current bytes change.

From the repository root:

```sh
python data/macro-improvements/combined-restoration/routing/reproduce.py
python data/macro-improvements/combined-restoration/routing/reproduce.py --output /tmp/worldatlas-routing-crosswalk-reproduced.json
```

The validator checks every source file/archive hash, all 135 unique routing associations, all candidate parent chains/statuses, 34 distinct added IDs, two holds and reciprocal Marcus/Japan inclusion. It reproduces the evidence JSON exactly. This does not rerun spatial measurement, scan the world, verify current private database claims or authorize publication; those remain in the upstream source tools and the publisher's separate gates.
