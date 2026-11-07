"""SeaVoX field handling across original and WFS-derived shapefiles."""


def feature_id(properties):
    """Return the unique MRGID_SR field regardless of DBF field-name case."""
    if not isinstance(properties, dict):
        raise ValueError('SeaVoX feature properties must be an object')
    values = [value for key, value in properties.items()
              if isinstance(key, str) and key.casefold() == 'mrgid_sr']
    if len(values) != 1 or values[0] is None:
        raise ValueError('SeaVoX feature needs one unambiguous MRGID_SR field')
    return str(values[0])
