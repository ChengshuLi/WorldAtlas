import unittest
from scripts.entity_registry_ui import wire_registry_ui

class RegistryWiringTest(unittest.TestCase):
    def test_wiring_uses_registry_and_fails_closed_on_missing_anchors(self):
        app = '''import {makeLegendItems} from '/review/old/legend-model.js';
makeLegendItems(meta.categories,def.counts);
({categories:meta.categories,rule_records:meta.rule_records});
const expectedContinents=[{id:1,name:'Africa'}];
if(presentation.continents.length!==6)throw Error('Water presentation must contain exactly six continent sections');'''
        refs = "export const CONTINENT_ORDER=Object.freeze(['Africa']);\nfunction f(meta){return CONTINENT_ORDER;}"
        wired, references = wire_registry_ui(app, refs)
        self.assertIn("from './legend-model.js'", wired)
        self.assertIn('makeLegendItems(meta,def.counts)', wired)
        self.assertIn('entity_registry:meta.entity_registry', wired)
        self.assertIn('v7ContinentSections(meta)', wired)
        self.assertIn('continentOrder(meta)', references)
        self.assertNotIn("Object.freeze(['Africa'])", references)
        with self.assertRaises(ValueError): wire_registry_ui('', refs)

if __name__ == '__main__': unittest.main()
