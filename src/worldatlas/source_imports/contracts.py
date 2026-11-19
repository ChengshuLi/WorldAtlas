"""Derive construction argument checks from the constructors' typed signatures."""

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

NonEmptyText = Annotated[str, StringConstraints(pattern=r"[^ \t\n\r\f\x0b]")]
SourceId = Annotated[NonEmptyText, "source-id"]


@dataclass(frozen=True)
class Runtime:
    """Execution resources and identities, supplied by the command rather than Neon JSON."""

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
    """Describe the JSON argument fields used to generate the SQL checks.

    Return a mapping from field names to (annotation, required) pairs. The
    annotation is the parameter's declared Python type, such as int or
    list[SourceId]. The required flag is true when the parameter has no default.
    The importer supplies runtime separately. Recipe parameters must be typed
    and keyword-only.
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
    """Keep construction objects closed and enforce patterns on mapping keys."""

    def typed_dict_schema(self, schema):
        return super().typed_dict_schema(schema) | {"additionalProperties": False}

    def dict_schema(self, schema):
        result = super().dict_schema(schema)
        if "patternProperties" in result:
            result["additionalProperties"] = False
        return result


def recipe_schema(method, fields):
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
    """Locate source references from declared types, never from field-name guesses."""
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
