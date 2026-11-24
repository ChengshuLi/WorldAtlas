"""Define types shared by source-import recipes and SQL contract generation."""

from typing import Annotated, TypedDict

from worldatlas.shared.text import NonEmptyText

# Mark raw source IDs so the generator can derive database links from the type.
SourceId = Annotated[NonEmptyText, "source-id"]


class FeatureIdentity(TypedDict):
    """Select a provider record and name its output feature."""

    feature_id: NonEmptyText
    source_feature_id: NonEmptyText | int
