"""Derive construction argument checks from the constructors' typed signatures."""

import argparse
from dataclasses import dataclass
from contextlib import contextmanager
import inspect
import math
from pathlib import Path
import types
from typing import (
    Annotated,
    Any,
    Literal,
    NotRequired,
    Required,
    Union,
    get_args,
    get_origin,
    get_type_hints,
    is_typeddict,
)

NonEmptyText = Annotated[str, "nonempty"]
SourceId = Annotated[str, "source-id"]


@dataclass(frozen=True)
class Runtime:
    """Execution resources and identities, supplied by the command rather than Neon JSON."""

    connect: Any
    storage: Any
    recipe_id: str
    method: str
    work_dir: Path | None = None
    expected_geometry_sha256: str | None = None
    arguments: dict | None = None

    def recipe(self, arguments):
        """Forward bound function arguments to algorithms that consume settings dictionaries."""
        return dict(
            {
                key: value
                for key, value in arguments.items()
                if key != "runtime" and value is not None
            },
            recipe_id=self.recipe_id,
        )

    @contextmanager
    def saving(self, database):
        """Save against the recipe that was actually calculated, holding only a short lock."""
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
    """Only typed keyword-only arguments are stored in a construction."""
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
        if parameter.name == "method":
            raise TypeError("method is supplied by the constructor registry")
        if parameter.default is not inspect.Parameter.empty and not matches(
            parameter.default, hints[parameter.name]
        ):
            raise TypeError("construction defaults must match their annotations")
        result[parameter.name] = (hints[parameter.name], parameter.default)
    return result


def matches(value, annotation):
    """Check JSON-compatible Python values without coercion."""
    origin, args = get_origin(annotation), get_args(annotation)
    if origin is Annotated:
        if args[1:] not in (("nonempty",), ("source-id",)) or args[0] is not str:
            raise TypeError("unsupported construction annotation metadata")
        return matches(value, str) and bool(value.strip(" \t\n\r\f\v"))
    if annotation is Any:
        if value is None or type(value) in (str, bool, int):
            return True
        if type(value) is float:
            return math.isfinite(value)
        if type(value) is list:
            return all(matches(item, Any) for item in value)
        if type(value) is dict:
            return all(
                type(key) is str and matches(item, Any) for key, item in value.items()
            )
        return False
    if origin in (Union, types.UnionType):
        return any(matches(value, choice) for choice in args)
    if origin is Literal:
        return any(type(value) is type(choice) and value == choice for choice in args)
    if annotation is type(None):
        return value is None
    if annotation in (str, bool):
        return type(value) is annotation
    if annotation is int:
        # PostgreSQL JSONB does not distinguish 1 from 1.0.
        return type(value) is int or (
            type(value) is float and math.isfinite(value) and value.is_integer()
        )
    if annotation is float:
        return type(value) in (float, int) and (
            type(value) is int or math.isfinite(value)
        )
    if origin is list:
        return type(value) is list and all(matches(item, args[0]) for item in value)
    if origin is tuple:
        return (
            type(value) is list
            and len(value) == len(args)
            and all(matches(item, kind) for item, kind in zip(value, args))
        )
    if origin is dict:
        return type(value) is dict and all(
            matches(k, args[0]) and matches(v, args[1]) for k, v in value.items()
        )
    if is_typeddict(annotation):
        hints = get_type_hints(annotation, include_extras=True)
        return (
            type(value) is dict
            and annotation.__required_keys__ <= value.keys() <= hints.keys()
            and all(matches(item, hints[key]) for key, item in value.items())
        )
    if origin in (NotRequired, Required):
        return matches(value, args[0])
    raise TypeError(f"unsupported construction annotation: {annotation!r}")


def validate_arguments(constructor, arguments):
    """Validate the stored fields, leaving defaults to ordinary Python argument binding."""
    fields = parameters(constructor)
    if not isinstance(arguments, dict):
        raise ValueError("construction arguments must be an object")
    extra = arguments.keys() - fields.keys()
    if extra:
        raise ValueError("unknown construction fields: " + ", ".join(sorted(extra)))
    for name, (annotation, default) in fields.items():
        if name not in arguments:
            if default is inspect.Parameter.empty:
                raise ValueError(f"missing construction field: {name}")
        elif not matches(arguments[name], annotation):
            raise ValueError(f"invalid construction field: {name}")


def literal(value):
    return "'" + value.replace("'", "''") + "'"


def sql_type(value, annotation, depth=0):
    """Compile annotations to PostgreSQL predicates; CASE guards all type-specific operations."""
    origin, args = get_origin(annotation), get_args(annotation)
    if origin is Annotated:
        base = sql_type(value, args[0], depth)
        if args[1:] not in (("nonempty",), ("source-id",)) or args[0] is not str:
            raise TypeError("unsupported construction annotation metadata")
        return f"({base} AND atlas.nonblank({value} #>> '{{}}'))"
    if annotation is Any:
        return "TRUE"  # Every stored JSONB value is already valid JSON.
    if origin in (Union, types.UnionType):
        return "(" + " OR ".join(sql_type(value, kind, depth) for kind in args) + ")"
    if origin is Literal:
        import json

        return (
            "("
            + " OR ".join(
                f"{value} = {literal(json.dumps(choice))}::jsonb" for choice in args
            )
            + ")"
        )
    if annotation in (str, bool, float, int, type(None)):
        kind = {
            str: "string",
            bool: "boolean",
            float: "number",
            int: "number",
            type(None): "null",
        }[annotation]
        condition = f"jsonb_typeof({value}) = {literal(kind)}"
        if annotation is int:
            number = f"({value} #>> '{{}}')::numeric"
            return (
                f"CASE WHEN {condition} THEN trunc({number}) = {number} ELSE FALSE END"
            )
        return condition
    if origin in (list, tuple):
        if origin is tuple:
            conditions = [f"jsonb_array_length({value}) = {len(args)}"]
            conditions += [
                sql_type(f"({value} -> {i})", kind, depth + 1)
                for i, kind in enumerate(args)
            ]
            body = " AND ".join(conditions)
        else:
            alias = f"item{depth}"
            condition = sql_type(f"{alias}.value", args[0], depth + 1)
            body = f"NOT EXISTS (SELECT 1 FROM jsonb_array_elements({value}) AS {alias}(value) WHERE NOT COALESCE({condition}, FALSE))"
        return f"CASE WHEN jsonb_typeof({value}) = 'array' THEN ({body}) ELSE FALSE END"
    if origin is dict:
        alias = f"item{depth}"
        key = sql_type(f"to_jsonb({alias}.key)", args[0], depth + 1)
        item = sql_type(f"{alias}.value", args[1], depth + 1)
        return (
            f"CASE WHEN jsonb_typeof({value}) = 'object' THEN NOT EXISTS "
            f"(SELECT 1 FROM jsonb_each({value}) AS {alias} WHERE NOT COALESCE(({key} AND {item}), FALSE)) ELSE FALSE END"
        )
    if is_typeddict(annotation):
        hints = get_type_hints(annotation, include_extras=True)
        fields = {
            name: (
                kind,
                inspect.Parameter.empty
                if name in annotation.__required_keys__
                else None,
            )
            for name, kind in hints.items()
        }
        return sql_object(value, fields, depth + 1)
    if origin in (NotRequired, Required):
        return sql_type(value, args[0], depth)
    raise TypeError(f"unsupported construction annotation: {annotation!r}")


def sql_object(value, fields, depth=0):
    allowed = ", ".join(literal(key) for key in fields)
    conditions = [f"{value} - ARRAY[{allowed}]::text[] = '{{}}'::jsonb"]
    for name, (annotation, default) in fields.items():
        expression = sql_type(f"({value} -> {literal(name)})", annotation, depth)
        if default is not inspect.Parameter.empty:
            expression = (
                f"(NOT {value} ? {literal(name)} OR COALESCE({expression}, FALSE))"
            )
        else:
            expression = (
                f"({value} ? {literal(name)} AND COALESCE({expression}, FALSE))"
            )
        conditions.append(expression)
    return (
        f"CASE WHEN jsonb_typeof({value}) = 'object' THEN (\n    "
        + "\n    AND ".join(conditions)
        + ") ELSE FALSE END"
    )


def source_paths(annotation, path="$"):
    """Locate source references from declared types, never from field-name guesses."""
    import json

    origin, args = get_origin(annotation), get_args(annotation)
    if origin is Annotated:
        return [path] if args[1:] == ("source-id",) else []
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

    import json

    choices, sources = [], []
    for method, constructor in sorted(IMPORTERS.items()):
        fields = parameters(constructor)
        choices.append(f"WHEN {literal(method)} THEN {sql_object('arguments', fields)}")
        paths = sorted({path for name, (kind, _) in fields.items()
                        for path in source_paths(kind, '$.' + json.dumps(name))})
        if paths:
            sources.append(
                f"WHEN {literal(method)} THEN ARRAY["
                + ",".join(literal("lax " + path) for path in paths) + "]::jsonpath[]"
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
