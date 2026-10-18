# Sweden single held key: bounded source research, 2026-10-18

Status: insufficient evidence to remove the hold or declare the repair package complete. No scientific producer was executed and no accepted outcome changed.

## Exact original scope and normative coordinate

Package gb-SWE-ADM2--repair-evaluation: 18,381 originals, 18,380 accepted, one territorial-exclusion hold. Held key x141221/y68544/owner40710; stable source target gb:SWE:ADM2:70781695B21663414086588. Owner's partition is 3 original = 2 supported + 1 held. Original source a1a8c3060a97cfc0648a7412c1662e19fde83f76, selected acceptance PR2414, original independent review https://github.com/ChengshuLi/WorldAtlas/pull/2409#pullrequestreview-5560026847 . That review explicitly preserves incomplete status.

Authenticated accepted cd1886f20f34abdcafe7c327ae0ee768ce5d47ae manifest SHA d9954fa51d18e4ce785679f920e4b6ac1ebd3cf07ce03fa7e7e674cb2a42faba declares grid size 262166 and an immutable normative latitude table. Its encoded SHA ab0becdda100da3473d7bb5d34ccda6510aa1c0490c407082072c7201ad1e147 and decoded SHA 66db3d02ede56a75e9c58426ad1388552be3bf7e5e4477476f198983b7436d23 both match the retained bytes. Longitude is (360*x+180-180*size)/size; latitude is the table's little-endian Float64 at y*8. Centre: longitude 13.921942585995133, latitude 64.81462670284787. See sweden-held-normative-centre.json, SHA 67192ad9621390bf919a9d098bd3a45dd1d1ddbadb570247e2e43f484e472673.

## Historical versus current evidence

The source review found the centre inside retained Norway ADM1 Trøndelag, approximately 0.000473 degrees from that older polygon's boundary. This justifies the existing conservative source exclusion; it does not establish a legal national boundary.

Kartverket's current administrative point endpoint returned HTTP404/no match for the exact centre in explicit EPSG4326. A known Oslo control returned Oslo; a point 0.01 degrees west returned Lierne, Trøndelag; one 0.01 degrees east returned no match. The official complete Lierne area response is 9,415 bytes, SHA c51eafeb024d5555fe01055d11a00cca7974a8f213b4ded4d46c9e84a0d80539. Its nearest boundary segment has endpoints [13.916473744421966,64.81025966101123] and [13.9312733406067,64.82212084194916]. A local equirectangular diagnostic puts the centre only 0.8341159778 metres from this segment. This sub-metre separation cannot establish Swedish ownership without coordinate epoch, boundary accuracy and effective-source qualification. Do not convert no-match into a positive assignment.

Official documented endpoint: https://ws.geonorge.no/kommuneinfo/v1/ ; OpenAPI describes /punkt with nord, ost, koordsys, and /kommuner/{kommunenummer}/omrade with utkoordsys. Queries and exact response receipts are retained next to this report. Dataset metadata describes national cadastral-derived administrative geometry, reference date 1 January 2026, CC BY4.0: https://data.norge.no/nb/datasets/cffde12f-3530-4406-9aa0-d6d4519ef077/administrative-enheter-fylker . This is current representation evidence, not independently demonstrated treaty-effective line geometry.

## Dated official boundary status

Lantmäteriet, 1 April 2026, states that the 2020–24 joint survey documentation, including GML, was delivered in 2025 and formal adoption was still in process: https://www.lantmateriet.se/sv/om-lantmateriet/nyheter-och-sociala-medier/nyheter/oversynen-av-riksgransen-mellan-sverige-och-norge-ar-klar--dokumentation-overlamnad-till-utrikesdepartementet/ . Its survey page explicitly requires governmental approvals and diplomatic exchange before effectiveness: https://www.lantmateriet.se/riksgransoversyn . The page identifies the preceding survey as 1984–87; it does not supply the precise effective segment for this centre. Kartverket's 14 January 2026 announcement confirms the digital survey's delivery and modern GNSS measurements: https://www.kartverket.no/om-kartverket/nyheter/til-lands/2026/januar/riksgrense-utenriksdepartementet-kartverket-nyoppmalinger . No effective revision or legal boundary shift at this centre has been established in this review.

## Completion question and minimum next evidence

Obtain the effective bilateral boundary/cairn segment covering the centre, its CRS/epoch, applicable accuracy and adoption status, plus corroborating Swedish official geometry or an explicit source authority statement. Compare to the exact original held key and preserved historical source scope. If the outcome supports no repair, first identify an existing package-contract disposition that legitimately closes that repair question and independently review it. The physical-review packet contract does not automatically transfer to a repair-evaluation packet. Existing conflict and a label of unresolved cannot alone produce completion credit.

## Swedish access boundary

The official public catalogue at https://api.lantmateriet.se/ogc-features/v1/administrativ-indelning/collections was readable and advertised kommuner, kommuner-2025 and kommuner-2026. The exact bounded feature query against kommuner-2026/items with bbox=13.9219425859,64.8146267027,13.9219425861,64.8146267030&limit=2 returned HTTP401 Unauthorized at approximately 06:44 UTC. That data route was stopped without login, credentials or alternate access. A public catalogue is not proof of feature access. No Swedish feature geometry was retrieved.
