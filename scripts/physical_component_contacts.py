"""Resolve exact source contacts through unchanged full-feature bindings.

The legacy component nearby_locations field does not summarize the new
physical audit's exact_location_contacts. Never interpret it as no contact.
"""
from evidence.immutable import canonical_json, sha256
from physical_gap_crosswalk import membership


def component_contacts(features, records):
    membership(features, records)
    by_id = {f['id']: f for f in features}
    result = []
    for record in sorted(records, key=lambda r: r['id']):
        bindings = []
        for binding in sorted(record['properties']['fragment_bindings'], key=lambda b: b['id']):
            feature = by_id[binding['id']]
            properties = feature['properties']
            present = 'exact_location_contacts' in properties
            contacts = properties.get('exact_location_contacts')
            if present and not isinstance(contacts, list):
                raise ValueError('Exact source contacts must be a complete list')
            bindings.append({'fragment': feature['id'],
                             'feature_sha256': sha256(canonical_json(feature)),
                             'status': 'recorded' if present else 'unknown-not-recorded',
                             'exact_location_contacts': contacts if present else None})
        result.append({'component': record['id'], 'fragment_contacts': bindings,
                       'status': 'complete-recorded-contacts' if all(b['status'] == 'recorded' for b in bindings)
                       else 'incomplete-source-contact-recording',
                       'administrative_assignment': None})
    return result
