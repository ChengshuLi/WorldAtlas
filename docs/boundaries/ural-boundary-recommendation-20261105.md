# Ural boundary: source-based working recommendation

Recommend retaining the research boundary in Neon revision
`ural-raw-source-workflow-20261105`, geometry SHA-256
`68390aa6ce5352226777adde3979315e1de85ca26d662c4b1c32610d1d73da66`, as the
current working geographic decision, with the qualifications below. It is a
reproducible convention, not a claim of a surveyed continental boundary. This
recommendation does not modify the geometry, change its database status, or
authorize a map build.

* **Northern watershed:** Use the chosen HydroBASINS European basin-edge route,
  with the two ArcticDEM-derived 15 m D8 interfaces and their verified source
  intersections. On the tested 100 m transects, the Arctic-derived gap-00 and
  gap-02 lines had opposite modeled drainage classes at 25/26 and 128/130
  Copernicus-screen stations, respectively. Stations are correlated and both
  screens share an outlet crosswalk. Product choice changes the modeled route;
  the comparison does not establish survey accuracy. The prior structured line
  remains an explicit route selector and provides many output coordinates: the
  raw-edge coverage check establishes source fidelity within its numerical test,
  not an independent proof that this route is the intended divide.
* **Headwater:** For a consistent mapped-river convention, use OSM relation
  214415 v122's spring-role node 1385867869 at 54.7035941 N, 59.4185198 E,
  connected to the modeled divide by the existing Copernicus D8 construction.
  The connection contains an approximately 699 m modeled flow path and a
  15.4 m pixel-to-node snap; it is not a surveyed watercourse. A local district
  library describes several source streams between Nazhim and Kruglaya and a
  plaque at one spring, so the plaque is not automatically the only hydrological
  headwater: https://www.uchaly-biblioteka.ru/istoricheskie-mesta-uchalinskogo-rayona/yaik-ural
  The spring-attraction article gives 54°41′40″ N, 59°24′45″ E; that rounded
  published coordinate is approximately 1,090 m WGS84 from the OSM relation's
  spring-role node. It is not an independently surveyed coordinate and must not
  be treated as establishing which stream is principal:
  https://ru.wikipedia.org/wiki/Исток_реки_Урал . The hydrological chapter
  supports the general river boundary but does not establish this local junction:
  https://doi.org/10.1016/B978-0-08-102612-0.00022-5 .
* **River and delta:** Follow the archived OSM relation main-stream graph to its
  canal/coastal endpoint. The 41,669 river edges were matched to the archived
  main-stream ways, and local topology supports the Zolotoy/main-channel and
  canal connection. The relation's mouth-role node lies upstream at the Shagan
  confluence and is not the selected sea endpoint. This is a documented
  cartographic choice; mapped topology alone is not an independent survey of
  distributary dominance or current shoreline position.

V8 uses these as model-dependent cartographic decisions. The headwater
assessment has limited survey evidence, and the cited library and attraction
descriptions may share underlying local sources. The [V8 construction
recipe](../../scripts/ural-audit/REVIEWED-URAL-20261106.md) describes how to
reproduce the selected boundary from the raw sources.
