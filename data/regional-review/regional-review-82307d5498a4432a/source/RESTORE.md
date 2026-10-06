# Source restoration instructions

## geoBoundaries RUS ADM2

The global source object was inspected on 2026-10-05 America/Los_Angeles from geoBoundaries repository commit `9469f09` (full commit response retained as `geoboundaries-9469f09-commit.json`). Its LFS pointer is retained in `geoBoundaries-RUS-ADM2-2017.lfs-pointer.txt` and records SHA-256/LFS OID `74012237384e53061aa63b6e20b9be24f94facfe615b52bbe72e62a81fa68ff0`, size 120,489,189 bytes. To restore, fetch the exact repository revision and path:

`https://media.githubusercontent.com/media/wmgeolab/geoBoundaries/9469f09/releaseData/gbOpen/RUS/ADM2/geoBoundaries-RUS-ADM2.geojson`

Verify the restored bytes against the pointer before analysis. The file is released under ODbL 1.0 per its retained metadata; retain attribution and applicable share-alike obligations. The much smaller `issue-396-scoped-geoboundaries-features.geojson` is the original 34-feature extract used for the reproduction and is retained in this packet.

## Kemerovo regional legal references

The Law 104-OZ consolidated reference PDF was inspected from the Kemerovo regional urban-planning portal (`https://mgis42.ru/`), filename “Закон Кемеровской области от 17 декабря 2004 г N 104-ОЗ (приложение 1-2) (ред. от 05.05.2025).pdf”. It was not committed because redistribution terms for the consolidated compilation were unclear. The inspected PDF SHA-256 was `d398adb702b6bf29a0de4e533208000d616df4c4dcfbf9ebf6f901df989093c3` (914,345 bytes); deterministic `pypdf` text extraction SHA-256 was `9e90921e6c6d6213da4f5ff24f0d4bc874aa2e0d5b9de84dea213bada471ff52`. Use the portal to locate the document and verify the revision and hashes if it remains available. Prefer the official publication portal and current legal register when validating any present-day boundary.

Law 215-OZ administrative-territorial framework is indexed at `https://www.kemer-gov.ru/doc/12311`; official publication portal records and amendments should be checked for the effective date of any proposed correction. Law 46-OZ official publication: `https://publication.pravo.gov.ru/document/4200202405070003`. Law 45-OZ official publication: `https://publication.pravo.gov.ru/document/4200202504250005`. Law 47-OZ secondary copy inspected: `https://kemerovo-pravo.ru/zakon/2024/05/06/n-47-oz/`; locate its official promulgation before relying on it for engineering changes.
