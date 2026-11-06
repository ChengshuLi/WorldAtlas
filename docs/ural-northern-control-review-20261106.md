# Northern Ural: independent watershed control review

The Ural research geometry remains `selected_for_research`; this review does
not change it. Two newly cataloged sources support the broad drainage
interpretation, not exact continental-boundary coordinates:

* The [Komi–Sverdlovsk agreement 176](https://www.pravo.gov66.ru/media/pravo/176_BE13ZIL.pdf),
  Appendix 1, describes the boundary south from Yanygkhachechakhl along the
  Pechora–Lozva watershed. It cites 1:100,000 topographic sheets. That
  description is south of the summit; it does not establish the entire
  gap-02 route to the north. R2 readback SHA-256
  `0b64970b2bc9d841441ce67fd284b1866b98f42fcda237975334326e20addc5c`.
* Russian Ministry of Natural Resources Order 137 of 26 February 2024 has
  sparse Dvina–Pechora and Lower Ob basin-district control points. Its
  [official publication](https://publication.pravo.gov.ru/document/0001202403290026)
  and the scanned [public mirror](https://service.garant.ru/large/objects/2024/4/53f34b8bd40cf0231f4c66c9e8eeb0bd.pdf)
  identify a watershed control north of the central gap and a three-basin
  control near its southern end. Pages 17–18 of the mirror were inspected
  directly. The official PDF download timed out, so byte equivalence between
  the mirror and official PDF is not established. The mirror's R2 readback
  SHA-256 is `e4655ca6122b02cc1fe039291a9b96c1c5cacf1f632b94b3fc61e586aab7d1a7`.

On the research line, `screen_federal_basin_control_points.py` sampled
coordinate-linear segments at up to 20 m WGS84 length: control 144 was about
203 m from the nearest sampled point, and control 146 about 491 m. The first
control lies well south of the gap-00 join; the second is near gap-02. These
are sampled distances, not certified minima. Control-point datum, placement
accuracy and the relationship between administrative districts and the local
natural divide are not established. Do not snap the boundary to these points.

The previously obtained historic topographic image was also overlaid with the
actual selected gap-02 terrain route. Visually it generally follows the mapped
ridge, but its source provenance and registration need further independent
verification; a summit comparison had about 192 m offset. This qualitative
check does not resolve individual joins or independently certify the route.
The existing ArcticDEM route remains the working choice. Gap-00's southern
join and the spring-to-divide connector remain model-dependent.

A public [Chelyabinsk regional prosecutor's description](https://epp.genproc.gov.ru/ru/proc_74/activity/legal-education/explain/e1943166/)
places the Ural source on the slopes of Kruglaya Sopka, which supports the
general headwater area but identifies no surveyed source node or divide join.
No authoritative georeferenced headwater survey was found in this review.

The seven construction inputs and the new supporting citations are distinct:
neither government document supplied coordinates to construct this line. The
prior structured northern line is still the route selector and supplies many
coordinates, while raw-edge fidelity and model outputs are independently
checked as documented in `docs/ural-raw-boundary-research-20261105.md`.
