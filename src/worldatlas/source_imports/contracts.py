"""Generate ``database/schema/construction_contracts.sql``.

Read each registered importer's typed signature to generate PostgreSQL
functions that validate stored construction arguments and extract the raw
source IDs they reference. The same SQL defines the shared nonblank check
for ordinary text columns and uses its pattern in construction JSON Schema.

To regenerate from the repository root, run
``python -m worldatlas.source_imports.contracts database/schema/construction_contracts.sql``.
"""

import argparse
from dataclasses import dataclass
from contextlib import contextmanager
import inspect
import json
from pathlib import Path
import types
from typing import (
    Annotated,
    Any,
    NotRequired,
    Required,
    TypedDict,
    Union,
    get_args,
    get_origin,
    get_type_hints,
    is_typeddict,
)

from psycopg.sql import quote
from pydantic import StringConstraints, TypeAdapter
from pydantic.json_schema import GenerateJsonSchema

# Use the same explicit Unicode White_Space set in every regex engine.
NONBLANK_PATTERN = (
    r"[^\u0009-\u000d\u0020\u0085\u00a0\u1680\u2000-\u200a"
    r"\u2028\u2029\u202f\u205f\u3000]"
)
NonEmptyText = Annotated[str, StringConstraints(pattern=NONBLANK_PATTERN)]
# Mark raw source IDs so the generator can derive database links from the type.
SourceId = Annotated[NonEmptyText, "source-id"]


@dataclass(frozen=True)
class Runtime:
    """Give a constructor the resources and record snapshot for one import.

    ``connect`` opens a PostgreSQL connection. ``storage`` provides access
    to raw objects in R2, and ``work_dir`` locates the download cache when
    one is configured. The importer passes this object separately from the
    JSON arguments. ``recipe_id``, ``method``, and ``arguments`` identify
    the record and the settings it used, so ``saving()`` can confirm the
    settings still match when the constructor writes its results.
    """

    connect: Any
    storage: Any
    recipe_id: str
    method: str
    arguments: dict
    work_dir: Path | None = None

    @contextmanager
    def saving(self, database):
        """Check and lock the construction while the caller saves geometry.

        Read the current method and arguments under a shared row lock and
        compare them with the snapshot used for the calculation. The lock
        lasts until the enclosing transaction finishes. An exception inside
        the context rolls back the save.

        Args:
            database: PostgreSQL connection used to save the result.

        Raises:
            ValueError: The construction was edited or deleted during calculation.
        """
        with database.transaction():
            row = database.execute(
                "SELECT method,arguments FROM atlas.construction_records WHERE id=%s FOR SHARE",
                (self.recipe_id,),
            ).fetchone()
            if row != (self.method, self.arguments):
                raise ValueError(
                    "construction changed during calculation; rerun its current settings"
                )
            yield


def parameters(constructor):
    """Return the argument types and presence requirements of a constructor.

    The importer supplies ``runtime`` separately. A parameter's default
    controls whether its JSON key can be omitted, and its type controls
    which values, including JSON null, are allowed when it is present.

    Args:
        constructor: Importer function with ``runtime`` as its first parameter.

    Returns:
        A mapping from stored field names to ``(annotation, required)``.
        The annotation is the declared Python type, such as ``int`` or
        ``list[SourceId]``, with its metadata. ``required`` is true when
        the parameter has no default.

    Raises:
        TypeError: The signature lacks the leading ``runtime`` parameter,
            or a stored parameter lacks a type or is not keyword-only.
    """
    signature = inspect.signature(constructor)
    arguments = list(signature.parameters.values())
    if not arguments or arguments[0].name != "runtime":
        raise TypeError("a constructor must start with runtime")
    hints = get_type_hints(constructor, include_extras=True)
    result = {}
    for parameter in arguments[1:]:
        if (
            parameter.kind != inspect.Parameter.KEYWORD_ONLY
            or parameter.name not in hints
        ):
            raise TypeError(
                "construction parameters must be typed, keyword-only arguments"
            )
        required = parameter.default is inspect.Parameter.empty
        result[parameter.name] = (hints[parameter.name], required)
    return result


class RecipeSchema(GenerateJsonSchema):
    """Customize Pydantic's JSON Schema for construction objects and mappings.

    A ``TypedDict`` declares a fixed set of allowed field names. A ``dict``
    can have names chosen by the recipe, such as the labels in a watershed's
    ``sources`` mapping. The generated schema enforces each kind of key rule.
    """

    def typed_dict_schema(self, schema):
        """Generate a schema that rejects every undeclared field name.

        This catches typos in top-level arguments and nested objects,
        including misspelled optional keys.

        Args:
            schema: Pydantic core schema for a ``TypedDict``.

        Returns:
            A JSON Schema dictionary with ``additionalProperties`` set to false.
        """
        return super().typed_dict_schema(schema) | {"additionalProperties": False}

    def dict_schema(self, schema):
        """Generate JSON Schema for a mapping, enforcing any key pattern.

        ``patternProperties`` validates values under matching keys.
        Setting ``additionalProperties`` to false also rejects keys that
        fail the pattern, such as a blank name in a watershed's ``sources``.

        Args:
            schema: Pydantic core schema for a Python mapping.

        Returns:
            The JSON Schema dictionary with nonmatching keys forbidden
            if there is a key pattern. Otherwise, Pydantic's schema as generated.
        """
        result = super().dict_schema(schema)
        if "patternProperties" in result:
            result["additionalProperties"] = False
        return result


def recipe_schema(method, fields):
    """Return the Draft 2020-12 JSON Schema for one method's arguments.

    Build a temporary ``TypedDict`` with ``NotRequired`` for fields with
    defaults, then pass it to Pydantic's schema generator.

    Args:
        method: Registered method name used as the schema title.
        fields: Field types and presence requirements from ``parameters()``.

    Returns:
        A Python dictionary describing the stored ``arguments`` object.
    """
    arguments = TypedDict(
        method,
        {
            name: kind if required else NotRequired[kind]
            for name, (kind, required) in fields.items()
        },
    )
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        **TypeAdapter(arguments).json_schema(schema_generator=RecipeSchema),
    }


def source_paths(annotation, path="$"):
    """Return the PostgreSQL JSON paths to values declared as ``SourceId``.

    For example, ``list[SourceId]`` at ``$."way_source_ids"`` yields
    ``$."way_source_ids"[*]``. PostgreSQL uses those paths to extract IDs
    from the actual JSON arguments. The type marker controls extraction
    even when the field has a name like ``source_id``.

    Args:
        annotation: Declared Python type of the value at ``path``.
        path: JSON path prefix, starting at ``$`` by default.

    Returns:
        A list of paths through unions, containers, and typed objects to
        source ID strings. An annotation with no source IDs yields an empty list.

    Raises:
        TypeError: A mapping declares source IDs as keys.
    """
    origin, args = get_origin(annotation), get_args(annotation)
    if origin is Annotated:
        return [path] if "source-id" in args[1:] else []
    if origin in (Union, types.UnionType):
        return sorted({p for kind in args for p in source_paths(kind, path)})
    if origin in (NotRequired, Required):
        return source_paths(args[0], path)
    if origin is list:
        return source_paths(args[0], path + "[*]")
    if origin is tuple:
        return [p for i, kind in enumerate(args)
                for p in source_paths(kind, path + f"[{i}]")]
    if origin is dict:
        if source_paths(args[0]):
            raise TypeError("source IDs must be values, not JSON object keys")
        return source_paths(args[1], path + ".*")
    if is_typeddict(annotation):
        return [p for name, kind in get_type_hints(annotation, include_extras=True).items()
                for p in source_paths(kind, path + "." + json.dumps(name))]
    return []


def database_checks():
    """Generate SQL checks and source reference extraction for the registry.

    ``atlas.nonblank`` uses the same Unicode whitespace pattern as
    ``NonEmptyText`` so plain SQL columns and JSON arguments agree.

    ``atlas.valid_construction_record`` picks the registered method's JSON
    Schema and validates ``arguments`` with ``pg_jsonschema``. The table's
    check constraint uses this function to reject unknown methods and
    malformed arguments on insert or update.

    ``atlas.construction_source_ids`` applies the declared source paths to
    the arguments and returns distinct source ID strings. The source-link
    trigger uses them to maintain ``atlas.construction_sources``, whose
    foreign key requires each ID to exist in ``atlas.source_assets``.

    Sort the method names and paths so ``--check`` can compare the output
    with the committed SQL byte for byte.

    Returns:
        The SQL script containing all three generated function definitions.
    """
    from worldatlas.source_imports.run_import import IMPORTERS

    choices, sources = [], []
    for method, constructor in sorted(IMPORTERS.items()):
        fields = parameters(constructor)
        schema = quote(json.dumps(recipe_schema(method, fields), separators=(",", ":")))
        choices.append(
            f"WHEN {quote(method)} THEN public.jsonb_matches_schema({schema}::json, arguments)"
        )
        paths = sorted({path for name, (kind, _) in fields.items()
                        for path in source_paths(kind, '$.' + json.dumps(name))})
        if paths:
            sources.append(
                f"WHEN {quote(method)} THEN ARRAY["
                + ",".join(quote("lax " + path) for path in paths) + "]::jsonpath[]"
            )
    return (
        "-- Generated from constructor signatures. Do not edit; see source_imports.contracts.\n"
        "CREATE FUNCTION atlas.nonblank(value text) RETURNS boolean\n"
        "LANGUAGE sql IMMUTABLE STRICT PARALLEL SAFE AS $nonblank$\n"
        f' SELECT value COLLATE "C" ~ {quote(NONBLANK_PATTERN)};\n'
        "$nonblank$;\n\n"
        "CREATE FUNCTION atlas.valid_construction_record(method text, arguments jsonb)\n"
        "RETURNS boolean LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $contract$\n"
        "SELECT CASE method\n"
        + "\n".join(choices)
        + "\nELSE FALSE END;\n$contract$;\n"
        "\nCREATE FUNCTION atlas.construction_source_ids(method text, arguments jsonb)\n"
        "RETURNS SETOF text LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $sources$\n"
        "SELECT DISTINCT value #>> '{}' FROM unnest(CASE method\n"
        + "\n".join(sources)
        + "\nELSE ARRAY[]::jsonpath[] END) AS paths(path)\n"
        "CROSS JOIN LATERAL jsonb_path_query(arguments,path,'{}'::jsonb,true) AS refs(value)\n"
        "WHERE jsonb_typeof(value)='string';\n"
        "$sources$;\n"
    )


def main():
    """Generate the construction SQL at the output path supplied on the command line.

    With ``--check``, compare the generated text with the existing file and
    exit with an error if they differ. Without it, write the generated text
    to the requested file.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--check", action="store_true", help="fail if the committed SQL differs"
    )
    args = parser.parse_args()
    generated = database_checks()
    if args.check:
        if args.output.read_text() != generated:
            parser.exit(
                1,
                "Construction checks are stale; regenerate " + str(args.output) + "\n",
            )
    else:
        args.output.write_text(generated)


if __name__ == "__main__":
    main()
