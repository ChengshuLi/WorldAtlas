"""Small input-contract fixtures; no external sources or geographic decisions."""


def selection():
    return dict(
        schema="worldatlas-input-selection-v4",
        raw_sources=[],
        construction_records=[],
        geography=dict(
            schema="worldatlas-geographic-division-v2",
            levels=[dict(id="world", parent_id=None)],
            entities=[
                dict(
                    id=0,
                    name="World",
                    level_id="world",
                    parent_id=None,
                    physical_class="mixed",
                    color_rgb=None,
                )
            ],
            features=[],
            category_bindings=[],
            rules=[],
            rule_features=[],
            rule_targets=[],
            rule_sources=[],
            construction_sources=[],
            sources=[],
        ),
    )
