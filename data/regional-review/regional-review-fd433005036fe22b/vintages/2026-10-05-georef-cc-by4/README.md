# Georef v2 department source supplement for issue #442

Captured 2026-10-05 from the official complete-departments endpoint:

- URL: `https://apis.datos.gob.ar/georef/api/v2.0/departamentos.geojson`
- Service documentation: `https://www.argentina.gob.ar/georef/descarga-de-la-base-completa`
- Data-origin documentation: `https://www.argentina.gob.ar/georef/origen-de-los-datos`
- Terms and required attribution: `https://www.argentina.gob.ar/georef/condiciones-de-uso-y-licencia`
- Attribution required by the service: **Servicio Georef – argentina.gob.ar/georef**. State modifications and use responsibly. Georef does not guarantee the information. The service states that Georef data is available under CC BY 4.0.
- Retrieval date: 2026-10-05 (UTC; exact retrieval time was not recorded).
- Data-vintage limitation: documentation says the complete data files are updated periodically but does not state the vintage/date of this response. The capture date is not presented as the source data vintage.
- The service identifies IGN as the origin for department geometry. It is an official, reusable cross-check but not an independent boundary authority. Do not treat this capture as proof of precise legal limits, completeness of detached islands/components, or release suitability.

The retained complete-country GeoJSON has 1,193,417 bytes and SHA-256 `31afdfe5983b6d7648eba1eafc7a5a8fe3c591abdca4b17c311c08c75d361e92`. It contains 529 features and 529 distinct department IDs. The capture is reproduced in `departamentos.geojson`; no geometry was simplified or edited by this packet.

## Reproduce

From the repository root with Python 3:

```sh
python3 data/regional-review/regional-review-fd433005036fe22b/vintages/2026-10-05-georef-cc-by4/reproduce_georef.py
```

The script validates the source SHA and exact ordered #442 ID digest, matches normalized department names plus the four explicit aliases recorded by the original comparator, and emits `georef-crosswalk.jsonl` and `georef-crosswalk-summary.json`. Every crosswalk row retains the previous individual assessment classification. This supplement does not upgrade any row to justified or replace the older IGN comparison.

Reproduced results: 241 unique issue IDs; 223 unique normalized-name/expected-province candidates; 15 unique name candidates in a different province (all Entre Ríos, code 30); two ambiguous names with no expected-province candidate (La Paz and Rivadavia); one no-match row (1ro. de Mayo). The prior 36 correction-needed and 205 insufficient-evidence classifications remain unchanged.

## Engineering/source handoff

The earlier packet text said the Rivadavia candidate with department code `86154` was in Salta. That parenthetical interpretation is incorrect: the code and the Georef feature identify Santiago del Estero (province 86); Salta is code 66. Georef returns five same-name Rivadavia candidates (Buenos Aires, Mendoza, Salta, San Juan, Santiago del Estero) and none in Córdoba (code 14); its feature `86154` is explicitly parented to Santiago del Estero. The exact frozen Rivadavia row therefore remains unresolved and must not be reassigned from this name-only crosswalk. Reconcile the earlier IGN candidate/code interpretation and locate an authoritative, dated unit/code source for the Córdoba feature; coordinate with the Southern South America integration owner before any parent or area edit.

This discrepancy is an erratum to the earlier prose, not a modification of its retained source capture or original classifications. The source join is an identity/parent screening only; no inference is made that the current Georef roster is complete for a specific historical or legal date.
