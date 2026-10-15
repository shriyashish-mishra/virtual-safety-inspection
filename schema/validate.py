#!/usr/bin/env python3
"""Validate a JSON file against one of the schemas in this folder. Standard library only.

    python3 schema/validate.py evidence samples/pass.json
    python3 schema/validate.py --all          # every sample and example in the repo

Supports the JSON Schema keywords the v0.1 schemas use: type, const, enum, required,
properties, additionalProperties, items, minItems, maxItems, minimum, maximum, pattern,
and local $ref. Any standard draft 2020-12 validator gives the same answer.
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
KINDS = ("capture", "geometry", "evidence", "checker_report")
TYPES = {
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
    "string": lambda v: isinstance(v, str),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "null": lambda v: v is None,
}
# Which files --all checks, and against which schema.
ALL = [
    ("evidence", "samples/pass.json"),
    ("evidence", "samples/fail.json"),
    ("checker_report", "samples/pass.checker_report.json"),
    ("checker_report", "samples/fail.checker_report.json"),
    ("capture", "schema/examples/capture.json"),
    ("geometry", "schema/examples/geometry.json"),
]


def check(value, schema, root, path, errors):
    if "$ref" in schema:
        node = root
        for part in schema["$ref"].lstrip("#/").split("/"):
            node = node[part]
        return check(value, node, root, path, errors)
    if "type" in schema:
        allowed = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        if not any(TYPES[t](value) for t in allowed):
            errors.append(f"{path}: expected {' or '.join(allowed)}, got {json.dumps(value)[:40]}")
            return
    if "const" in schema and value != schema["const"]:
        errors.append(f"{path}: must be {json.dumps(schema['const'])}")
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: {json.dumps(value)} is not one of {schema['enum']}")
    if TYPES["number"](value):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{path}: {value} is below {schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            errors.append(f"{path}: {value} is above {schema['maximum']}")
    if isinstance(value, str) and "pattern" in schema and not re.search(schema["pattern"], value):
        errors.append(f"{path}: {value!r} does not match {schema['pattern']}")
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            errors.append(f"{path}: needs at least {schema['minItems']} items")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            errors.append(f"{path}: allows at most {schema['maxItems']} items")
        if "items" in schema:
            for i, item in enumerate(value):
                check(item, schema["items"], root, f"{path}[{i}]", errors)
    if isinstance(value, dict):
        props = schema.get("properties", {})
        for key in schema.get("required", []):
            if key not in value:
                errors.append(f"{path}: missing {key}")
        extra = schema.get("additionalProperties", True)
        for key, item in value.items():
            if key in props:
                check(item, props[key], root, f"{path}.{key}", errors)
            elif extra is False:
                errors.append(f"{path}: unexpected field {key}")
            elif isinstance(extra, dict):
                check(item, extra, root, f"{path}.{key}", errors)


def validate(kind, file):
    schema = json.loads((HERE / f"{kind}.schema.json").read_text())
    errors = []
    check(json.loads(Path(file).read_text()), schema, schema, "$", errors)
    return errors


def main(argv):
    if argv == ["--all"]:
        pairs = [(k, ROOT / f) for k, f in ALL]
    elif len(argv) == 2 and argv[0] in KINDS:
        pairs = [(argv[0], Path(argv[1]))]
    else:
        print(__doc__)
        return 2
    failed = 0
    for kind, file in pairs:
        errors = validate(kind, file)
        print(f"{'ok  ' if not errors else 'FAIL'} {kind:<15} {file}")
        for e in errors:
            print(f"     {e}")
        failed += bool(errors)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
