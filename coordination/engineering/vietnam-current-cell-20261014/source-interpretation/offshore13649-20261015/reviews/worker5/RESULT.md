# Worker 5 completed native-scene interpretation

All frozen assigned scenes 4,8,12,16,20,24,28,32 are complete: 4,216 distinct exact original keys, 72 complete source blocks and 216 native RGB/NIR/centre frames read. There are 3,070 dated water-location answers, 54 dated terrestrial-location answers, 696 cloud/halo/shadow questions and 396 reef/shore/mixed questions.

| Scene | Keys | Water | Terrestrial | Cloud/halo/shadow | Reef/shore/mixed | Blocks |
|---:|---:|---:|---:|---:|---:|---:|
| 4 | 832 | 780 | 0 | 50 | 2 | 14 |
| 8 | 368 | 293 | 0 | 8 | 67 | 14 |
| 12 | 193 | 88 | 0 | 83 | 22 | 6 |
| 16 | 144 | 58 | 0 | 67 | 19 | 5 |
| 20 | 70 | 66 | 0 | 4 | 0 | 5 |
| 24 | 39 | 36 | 0 | 3 | 0 | 2 |
| 28 | 14 | 8 | 0 | 6 | 0 | 1 |
| 32 | 2556 | 1741 | 54 | 475 | 286 | 25 |

The eight scene-NN.json files retain every original record, exact centre and source-array/interval position, literal red/green/blue/NIR/SCL values and masks with 3×3 neighbourhoods, exact native source pixels/subpixels, block/frame paths and hashes, explicit answer or remaining question. All input memberships, unchanged records, literal retained observations and file/hash identities passed the task-local check in identity-check.json.

Scene 32 depicts a built and vegetated terrestrial island in block-03-04. Fifty-four unchanged centres fall in its manually selected conservative interior; exact indices appear in terrestrial_indices. The position polygon in scene32-manual-view-checkpoint.json is image-reading notation, not an extracted shoreline or native-cell geometry. Some literal SCL labels disagree with that visually coherent island interior: 10 label 9, 8 label 8, 3 label 6, 13 label 5, 15 label 4 and 5 label 7. Independent adoption must assess this actual image/label disagreement; no label was rewritten or silently used as truth.

Water answers describe the dated exact-centre locality. They do not assert annual persistence, depth, salinity, legal marine extent or the whole native-cell surface. Nearby visible islands or reef structure do not classify a centre elsewhere. Cloud/reef exceptions follow manual native-image spatial reading, including coherent local groups; no spectral threshold or automatic surface classifier ran.

Root independent adoption remains pending. Original territorial/foreign-reference/ownership holds are unchanged; repair and qualification credit is zero. No remote reread, raster replay, source producer, build, shoreline extraction or authority operation ran.
