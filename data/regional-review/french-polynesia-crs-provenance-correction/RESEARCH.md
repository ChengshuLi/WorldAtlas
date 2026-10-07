# RGPF provenance and sensitivity correction

## Scope and result

This superseding erratum addresses exactly PYF-4963 through PYF-4967. It preserves the five stable feature IDs, names, parent IDs, source exports and previously published measurements. The three retained DAF archives each contain a `.prj` that declares GCS_RGPF, D_Reseau_Geodesique_de_la_Polynesie_Francaise and GRS_1980; pyproj resolves each to EPSG:4687. The earlier packet's EPSG:4326 label and WGS84 method therefore do not describe the source coordinate reference system.

The official DAF describes RGPF as the geodetic system made official for government services by arrêté 510/CM (2018). That establishes the source datum context; it does not document the conversion used by the prior export. Mapshaper 0.6.121's default GeoJSON output has no CRS member and no datum transformation. Explicit `-proj wgs84` changed 1,296,757 vertices by at most 2.84e-14 degrees (3.19e-9 m), consistent with machine precision and not a meaningful datum operation. RFC 7946 GeoJSON uses WGS84 longitude/latitude; emitting native RGPF numeric values as though they were WGS84 is semantically mismatched.

## Sensitivity scenario

The prior inputs were independently reproduced byte-for-byte. EPSG operation 8828 (`RGPF to WGS 84 (1)`, 0.5 m stated accuracy, to original Transit WGS84) is used only as a traceable sensitivity scenario. The EPSG database also offers operation 15833, a no-op approximation stated at ±1 m. DAF has not been shown to endorse either operation. The sampled 8828 displacement is 0.713 m; the 15833 sample is unchanged. Neither operation is selected as production policy.

| Subject | Metric | Value | Units |
|---|---|---:|---|
| PYF-4963 Windward Islands | Raw IoU | 0.73494582 | fraction |
| PYF-4963 Windward Islands | EPSG:8828 IoU | 0.73489603 | fraction |
| PYF-4963 Windward Islands | Delta IoU | -0.00004979 | fraction |
| PYF-4963 Windward Islands | Delta intersection area | -38884.32 | m² |
| PYF-4964 Leeward Islands | Raw IoU | 0.54776912 | fraction |
| PYF-4964 Leeward Islands | EPSG:8828 IoU | 0.54773596 | fraction |
| PYF-4964 Leeward Islands | Delta IoU | -0.00003316 | fraction |
| PYF-4964 Leeward Islands | Delta intersection area | -9787.52 | m² |
| PYF-4965 Tuamotu-Gambier | Raw IoU | 0.04777381 | fraction |
| PYF-4965 Tuamotu-Gambier | EPSG:8828 IoU | 0.04777366 | fraction |
| PYF-4965 Tuamotu-Gambier | Delta IoU | -0.00000015 | fraction |
| PYF-4965 Tuamotu-Gambier | Delta intersection area | -164.61 | m² |
| PYF-4966 Austral Islands | Raw IoU | 0.12245925 | fraction |
| PYF-4966 Austral Islands | EPSG:8828 IoU | 0.12245182 | fraction |
| PYF-4966 Austral Islands | Delta IoU | -0.00000743 | fraction |
| PYF-4966 Austral Islands | Delta intersection area | -3048.05 | m² |
| PYF-4967 Marquesas Islands | Raw IoU | 0.65760307 | fraction |
| PYF-4967 Marquesas Islands | EPSG:8828 IoU | 0.65752129 | fraction |
| PYF-4967 Marquesas Islands | Delta IoU | -0.00008178 | fraction |
| PYF-4967 Marquesas Islands | Delta intersection area | -64665.82 | m² |

These are source-relative diagnostics, not legal-boundary or completeness evidence. The assignment membership remains unchanged (125 assigned objects; IDs 61, 122 and 128 remain unassigned). The largest-overlap rule and union exclude municipal-only objects and unassigned objects. Ratios change by less than 0.000082; they do not resolve the prior large coverage discrepancies.

## Territorial meaning and limits

The five DAF polygons are explicitly figurative administrative group divisions. The names overlap physical-geography usage: Windward and Leeward are divisions within the Society Islands, while Tuamotu-Gambier is a combined grouping. The 2005 and 2022 state decrees define administrative subdivisions by communes, not these five source polygons. Their roster counts do not validate polygon boundaries. DAF catalog publication is 2022-02-28; the group features were acquired 2018-09-05 and edited 2020-03-09. No evidence here establishes 2026 legal currency. The island layer includes islands, atolls, banks and reefs; municipal association does not form a complete roster of uninhabited objects.

The archived sources and prior results are preserved. No official DAF conversion directive, current boundary certification, comprehensive island inventory, or source-page reuse license was established beyond the catalog's CC BY label (version unspecified). No geography approval, source import or production conversion choice is requested or implied. Engineering follow-up: before any future WGS84 publication, determine the intended operation from an authoritative DAF specification and document its epoch/realization, accuracy, axis order, area semantics and output metadata; retain both native and transformed coordinates and rerun validation.

### Stable hierarchy

| ID | Name | Existing parent ID |
|---|---|---|
| PYF-4963 | Windward Islands | `framework:province:windward-islands:f00645bd9827` |
| PYF-4964 | Leeward Islands | `framework:province:leeward-islands:f1d53af78fed` |
| PYF-4965 | Tuamotu-Gambier | `framework:province:tuamotu-gambier:f6a7d4ec9817` |
| PYF-4966 | Austral Islands | `framework:province:austral-islands:280986970614` |
| PYF-4967 | Marquesas Islands | `framework:province:marquesas-islands:0beb7fe5d3cd` |
