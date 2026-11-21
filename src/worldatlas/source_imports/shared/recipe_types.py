"""Define types shared by source-import recipes and SQL contract generation."""

from typing import Annotated, TypedDict

from pydantic import StringConstraints

# Use the same explicit Unicode White_Space set in every regex engine.
NONBLANK_PATTERN = (
    r"[^\u0009-\u000d\u0020\u0085\u00a0\u1680\u2000-\u200a"
    r"\u2028\u2029\u202f\u205f\u3000]"
)
NonEmptyText = Annotated[str, StringConstraints(pattern=NONBLANK_PATTERN)]
# Mark raw source IDs so the generator can derive database links from the type.
SourceId = Annotated[NonEmptyText, "source-id"]


class FeatureIdentity(TypedDict):
    """Select a provider record and name its output feature."""

    feature_id: NonEmptyText
    source_feature_id: NonEmptyText | int
