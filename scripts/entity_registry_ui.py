"""Fail-closed wiring for recovered V7 UI sources; never edits hosted assets."""
import re


def replace_once(source, old, new):
    if source.count(old) != 1:
        raise ValueError(f'Expected one V7 UI anchor: {old[:90]}')
    return source.replace(old, new)


def wire_registry_ui(app, references):
    app, count = re.subn(
        r"from ['\"]/review/[^'\"]+/legend-model\.js['\"]",
        "from './legend-model.js'", app)
    if count != 1:
        raise ValueError('Expected one hosted V7 legend import')
    app = "import {v7ContinentSections} from './v7-entity-adapter.js';\n" + app
    app = replace_once(app, 'makeLegendItems(meta.categories,def.counts)', 'makeLegendItems(meta,def.counts)')
    app = replace_once(app, 'categories:meta.categories,rule_records:meta.rule_records',
                       'categories:meta.categories,entity_registry:meta.entity_registry,rule_records:meta.rule_records')
    app, count = re.subn(r'const expectedContinents=\[[^;]+\];',
                         'const expectedContinents=v7ContinentSections(meta);', app)
    if count != 1:
        raise ValueError('Expected one V7 presentation section index')
    app = replace_once(app, 'presentation.continents.length!==6',
                       'presentation.continents.length!==expectedContinents.length')
    app = app.replace('Water presentation must contain exactly six continent sections',
                      'Water presentation does not match registry continent sections')
    references, count = re.subn(r'export const CONTINENT_ORDER=Object.freeze\(\[[^;]+\]\);',
        "import {v7ContinentSections} from './v7-entity-adapter.js';\n"
        'function continentOrder(meta){return v7ContinentSections(meta).map(section=>section.name);}', references)
    if count != 1:
        raise ValueError('Expected one recovered reference continent index')
    references = references.replace('CONTINENT_ORDER', 'continentOrder(meta)')
    references = references.replace('must contain all six continents', 'must contain all registry continent sections')
    return app, references
