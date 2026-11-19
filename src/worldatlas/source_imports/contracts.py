"""Generate PostgreSQL construction checks and source references from Python types.

Each construction record stores a registered method name and a JSON object
of arguments. The method's signature defines which arguments are required,
their types, and which values refer to raw sources. Regenerating the SQL
updates both database functions from those declarations.
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

# Require at least one character outside the listed whitespace characters.
NonEmptyText = Annotated[str, StringConstraints(pattern=r"[^ \t\n\r\f\x0b]")]
# Keep the string constraint and mark this value as a reference to source_assets.id.
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
        """Check the recipe and hold it stable while the caller saves geometry.

        Read the current method and arguments under a shared row lock and
        compare them with the snapshot used for the calculation. Raise
        ValueError before saving if the recipe changed or was deleted.

        The caller writes the geometry inside this context. The row lock
        prevents recipe edits until the enclosing transaction finishes.
        An exception inside the context rolls back the save.
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

    Each entry maps a JSON field name to ``(annotation, required)``. The
    annotation is the declared Python type, such as ``int`` or
    ``list[SourceId]``, including metadata used for validation and reference
    extraction. ``required`` is true when the parameter has no default.
    A type that permits ``None`` controls whether JSON null is allowed
    when the key is present. The default controls whether the key can be omitted.

    Raise ``TypeError`` if the first parameter is missing or has a name
    other than ``runtime``, or if any subsequent parameter lacks a type
    annotation or is not keyword-only. The importer supplies ``runtime``
    separately, so it is excluded from the returned fields.
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

        Pydantic supplies the field types and required keys. The extra
        restriction catches typos even when the intended field is optional.
        It applies to the top-level arguments and to nested typed objects.
        """
        return super().typed_dict_schema(schema) | {"additionalProperties": False}

    def dict_schema(self, schema):
        """Require each mapping key to match Pydantic's pattern when present.

        ``patternProperties`` validates values under matching keys. JSON
        Schema still allows nonmatching keys by default. Setting
        ``additionalProperties`` to false rejects them, so a watershed
        source named ``"primary"`` can have a valid source reference, while
        a source named ``"   "`` fails the nonblank key constraint. Mappings
        without a key pattern keep Pydantic's generated value rules.
        """
        result = super().dict_schema(schema)
        if "patternProperties" in result:
            result["additionalProperties"] = False
        return result


def recipe_schema(method, fields):
    """Return the Draft 2020-12 JSON Schema for one method's arguments.

    ``fields`` is the mapping returned by ``parameters()``. Use it to build
    a temporary ``TypedDict``, wrapping fields with defaults in
    ``NotRequired``. Pydantic converts that object type into JSON Schema
    using ``RecipeSchema``. ``method`` names the type and appears as the
    schema title. The database stores it separately from ``arguments``.
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

    ``annotation`` is a declared Python type and ``path`` identifies the
    JSON value at that type, starting at ``$`` for the root. For example,
    an ``osm_way_chain`` argument typed as ``list[SourceId]`` yields
    ``$."way_source_ids"[*]`` when starting at ``$."way_source_ids"``.

    Follow each union alternative, unwrap required and optional fields,
    and descend through list elements, tuple positions, mapping values,
    and typed object fields. Raise ``TypeError`` for source IDs declared
    as mapping keys. A field named ``source_id`` contributes a path only
    if its type carries the source reference marker.

    These paths describe where to look. PostgreSQL later applies them to
    the actual JSON arguments to collect the IDs for the source links.
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
    """Return the complete SQL text generated from the importer registry.

    ``atlas.valid_construction_record`` picks the registered method's JSON
    Schema and validates ``arguments`` with ``pg_jsonschema``. The table's
    check constraint uses this function to reject unknown methods and
    malformed arguments on insert or update.

    ``atlas.construction_source_ids`` applies the declared source paths to
    the arguments and returns distinct source ID strings. The source-link
    trigger uses them to maintain ``atlas.construction_sources``, whose
    foreign key requires each ID to exist in ``atlas.source_assets``.

    Sort the method names and paths so the output can be compared directly
    with the committed ``database/schema/construction_contracts.sql`` file.
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
        "CREATE FUNCTION atlas.valid_construction_record(method text, arguments jsonb)\n"
        "RETURNS boolean LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $contract$\n"
        "SELECT CASE method\n"
        + "\n".join(choices)
        + "\nELSE FALSE END;\n$contract$;\n"
        "ALTER TABLE atlas.construction_records ADD CONSTRAINT construction_arguments_valid\n"
        "CHECK (atlas.valid_construction_record(method, arguments));\n"
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
