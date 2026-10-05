# Bounded handoffs

- [#932](https://github.com/ChengshuLi/WorldAtlas/issues/932) is blocked on #445 and owns exactly the 167 scoped Chile ADM3 communes. It restores and audits the official 2023 SUBDERE DPA polygons, including license clearance, island/coast edges, exact roster and parent matching. The archive SHA-256 and byte length are pinned in the issue.
- [#933](https://github.com/ChengshuLi/WorldAtlas/issues/933) is blocked on #445 and owns exactly the 47 scoped Paraguay ADM2 districts. It verifies all scoped legal roles, parents and boundary suitability against authoritative instruments after exact source restoration and hash verification. It is distinct from #926, which covers 194 other Paraguay source IDs under #446.
- Existing [#930](https://github.com/ChengshuLi/WorldAtlas/issues/930) is a related engineering handoff for `atlas:city:PRY-4837` and its four source members, but is parented to #446. The exact city ID is in #445 and absent from #446’s subject scope, so #930 is not a substitute or evidence coverage for this packet. Coordinate that cross-packet dependency before implementation; this packet does not change #930’s parent, claim or scope.

Each handoff preserves the no-import, no-publication and no-regional-approval gates. These issues are recorded as blocked follow-ups; their creation does not resolve any geographic uncertainty.
