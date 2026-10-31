"""Constituent waters inherit a bounded parent, not the open-ocean fallback.

Names are source lookup keys, not a test that every named bay is bounded.
Open embayments retain the ordinary 22.224 km coastal rule.
"""
FAMILIES = {
 'Gulf of Mexico': (4, ['Bahía de Campeche','Straits of Florida','Yucatan Channel']),
 'Caribbean Sea': (99, ['Gulf of Honduras','Golfo de Urabá','Lago de Maracaibo']),
 'Hudson and Canadian archipelago waters': (4, [
  'Foxe Basin','Ungava Bay','Frobisher Bay','Cumberland Sound','Gulf of Boothia',
  'Viscount Melville Sound',"M’Clure Strait","M'Clure Strait",'Amundsen Gulf',
  'Prince of Wales Strait','Minto Inlet','Richard Collinson Inlet','Prince ALbert Sound',
  'Liddon Gulf','Wynniatt Bay','Hadley Bay','Bathurst Inlet','Goldsmith Channel',
  'Sherman Basin','Wager Bay','Fury and Hecla Strait','Jones Sound','Eclipse Sound']),
 'Bering Sea': (99, ['Bristol Bay','Norton Sound',"Gulf of Anadyr'"]),
 'Alaska bounded inlets': (4, ['Kotzebue Sound','Cook Inlet','Prince William Sound','Baird Inlet']),
 'North American enclosed coastal waters': (4, [
  'Golfo de California','Gulf of Saint Lawrence','Strait of Belle Isle','Bay of Fundy',
  'Chesapeake Bay','Delaware Bay','Long Island Sound','Albemarle Sound','Pamlico Sound',
  'San Francisco Bay','Salish Sea','Queen Charlotte Strait','Hecate Strait','Dixon Entrance',
  'Cordova Bay','Smith Sound','Hamilton Inlet','Lake Pontchartrain',"Bras d'Or Lake"]),
 'Red Sea': (99, ['Gulf of Suez','Gulf of Aqaba','Bab el Mandeb']),
 'Mediterranean Sea': (99, ['Adriatic Sea','Aegean Sea','Ionian Sea','Tyrrhenian Sea','Balearic Sea',
  'Alboran Sea','Ligurian Sea','Sea of Crete','Golfe du Lion','Gulf of Gabès','Gulf of Sidra','Strait of Gibraltar']),
 'Black Sea': (99, ['Sea of Azov','Sea of Marmara','Bosporus','Dardanelles']),
 'Baltic and North Sea': (3, ['Gulf of Bothnia','Gulf of Finland','Gulf of Riga','Skagerrak',
  'Kattegat','Øresund','Waddenzee','Stettiner Haff','Mecklenburger Bucht','Kaliningrad']),
 'East Asian bounded seas': (2, ['Bo Hai','Gulf of Tonkin','Hangzhou Bay','Taiwan Strait','Qiongzhou Strait',
  'Inner Sea','Tsugaru Strait','Tatar Strait','La Pérouse Strait','Korea Strait',
  'Shelikhova Gulf','Uda Bay','Gulf of Sakhalin']),
 'Southeast Asian archipelago waters': (99, ['Molucca Sea','Ceram Sea','Makassar Strait','Halmahera Sea',
  'Bali Sea','Selat Bali','Flores Sea','Savu Sea','Selat Dampier','Gulf of Tomini','Gulf of Buli',
  'Gulf of Kau','Davao Gulf','Sibuyan Sea','Bohol Sea','Surigao Strait','Ragay Gulf','Samar Sea',
  'Tayabas Bay','Leyte Gulf','Visayan Sea','Strait of Singapore']),
 'Andaman Sea': (2, ['Gulf of Martaban']),
 'Nares Strait and Greenland fjords': (4, ['Kane Basin','Hall Basin','Kennedy Channel','Robeson Channel',
  'Murchison Sound','Kangertittivaq','Uummannaq Fjord','Disko Bay']),
 'Norwegian bounded inlets': (3, ['Vestfjorden','Storfjorden','Sognefjorden','Trondheimsfjorden','Boknafjorden']),
 'Asian bounded inlets and passages': (2, ['Strait of Malacca','Palk Strait','Gulf of Ob','Yenisey Gulf',
  'Khatanga Gulf','Chaun Bay','Gulf of Kutch','Gulf of Khambhät',"Vil'kitskogo Strait",'Dmitriy Laptev Strait']),
 'American estuaries and inner passages': (99, ['Río de la Plata','Saint Lawrence River','Baía de São Marcos',
  'Baía de Marajó','Boca Grande','Lagoa dos Patos','Golfo Corcovado','Estrecho de Magellanes',
  'Seno de Skyring','Seno Otway','Bay Inútil','Queen Charlotte Sound']),
 'Australian bounded inlets': (6, ['Shark Bay','Gulf St. Vincent','Joseph Bonaparte Gulf']),
 'Australasian bounded straits': (6, ['Bass Strait','Torres Strait','Cook Strait']),
}

def child_rules():
    result={}
    for parent,(group,names) in FAMILIES.items():
        for name in names:
            if name in result:raise ValueError(f'Duplicate sea {name}')
            result[name]={'family':parent,'group':group}
    return result

# These must not acquire whole-sea continental coverage just because named.
OPEN_WATERS={'Philippine Sea','Arabian Sea','Bay of Bengal','Bay of Biscay','Gulf of Alaska',
 'Norwegian Sea','Greenland Sea','Barents Sea','Kara Sea','Laptev Sea','East Siberian Sea',
 'Chukchi Sea','Beaufort Sea','Lincoln Sea','Baffin Bay','Davis Strait','Labrador Sea',
 'Denmark Strait','Sargasso Sea','Gulf of Guinea','Bight of Benin','Bight of Biafra',
 'Laccadive Sea','Gulf of Yana','Gulf of Maine','Melville Bay','Golfo San Jorge','Gulf of Mannar',
 'Uchiura Bay','Karaginskiy Gulf','Golfo de Panamá','Golfo San Matías','Bahía Grande','Gulf of Olen‘k',
 'Geographe Bay','Bay of Plenty','Golfo de Tehuantepec','Mackenzie Bay','Kronotskiy Gulf',
 'Gulf of Kamchatka','East Korea Bay','Golfo de Guayaquil','Gulf of Masira','Golfo de Penas','Massachusetts Bay'}
assert not (set(child_rules()) & OPEN_WATERS)
