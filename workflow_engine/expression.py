from __future__ import annotations

import ast
import re
from typing import Any


_EXACT = re.compile(r"^\$\{(.+)\}$", re.DOTALL)


def resolve(path: str, inputs: dict, state: dict, schemas: dict, error: Any = None) -> Any:
    path = path.strip()
    roots = {
        "input": inputs,
        "state": state,
        "schemas": schemas,
        "error": error,
    }
    parts = path.split(".")
    if parts[0] not in roots:
        raise KeyError(f"Unknown expression root: {parts[0]}")
    value = roots[parts[0]]
    for part in parts[1:]:
        if isinstance(value, dict):
            value = value.get(part)
        else:
            value = getattr(value, part)
    return value


def interpolate(value: Any, inputs: dict, state: dict, schemas: dict, error: Any = None) -> Any:
    if not isinstance(value, str):
        if isinstance(value, dict):
            return {k: interpolate(v, inputs, state, schemas, error) for k, v in value.items()}
        if isinstance(value, list):
            return [interpolate(v, inputs, state, schemas, error) for v in value]
        return value

    match = _EXACT.match(value.strip())
    if match:
        return resolve(match.group(1), inputs, state, schemas, error)

    def replace(match_obj: re.Match[str]) -> str:
        resolved = resolve(match_obj.group(1), inputs, state, schemas, error)
        return str(resolved)

    return re.sub(r"\$\{([^}]+)\}", replace, value)


def _length(value: Any) -> int:
    return 0 if value is None else len(value)


def _eval_node(node: ast.AST, inputs: dict, state: dict, schemas: dict, error: Any) -> Any:
    if isinstance(node, ast.Constant):
        return node.value

    if isinstance(node, ast.Name):
        roots = {
            "input": inputs,
            "state": state,
            "schemas": schemas,
            "error": error,
        }
        if node.id in roots:
            return roots[node.id]
        if node.id in {"True", "False", "None"}:
            return {"True": True, "False": False, "None": None}[node.id]
        raise ValueError(f"Unsupported name: {node.id}")

    if isinstance(node, ast.Attribute):
        base = _eval_node(node.value, inputs, state, schemas, error)
        if isinstance(base, dict):
            return base.get(node.attr)
        return getattr(base, node.attr)

    if isinstance(node, ast.Subscript):
        base = _eval_node(node.value, inputs, state, schemas, error)
        index = _eval_node(node.slice, inputs, state, schemas, error)
        return base[index]

    if isinstance(node, ast.List):
        return [_eval_node(x, inputs, state, schemas, error) for x in node.elts]

    if isinstance(node, ast.Tuple):
        return tuple(_eval_node(x, inputs, state, schemas, error) for x in node.elts)

    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name):
            raise ValueError("Only simple function calls are supported")
        if node.func.id == "length":
            if len(node.args) != 1:
                raise ValueError("length() takes exactly one argument")
            return _length(_eval_node(node.args[0], inputs, state, schemas, error))
        raise ValueError(f"Unsupported function: {node.func.id}")

    if isinstance(node, ast.BoolOp):
        if isinstance(node.op, ast.And):
            for value_node in node.values:
                if not _eval_node(value_node, inputs, state, schemas, error):
                    return False
            return True
        for value_node in node.values:
            if _eval_node(value_node, inputs, state, schemas, error):
                return True
        return False

    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        return not _eval_node(node.operand, inputs, state, schemas, error)

    if isinstance(node, ast.Compare):
        left = _eval_node(node.left, inputs, state, schemas, error)
        for op, comparator in zip(node.ops, node.comparators):
            right = _eval_node(comparator, inputs, state, schemas, error)
            if isinstance(op, ast.Eq):
                ok = left == right
            elif isinstance(op, ast.NotEq):
                ok = left != right
            elif isinstance(op, ast.Lt):
                ok = left < right
            elif isinstance(op, ast.LtE):
                ok = left <= right
            elif isinstance(op, ast.Gt):
                ok = left > right
            elif isinstance(op, ast.GtE):
                ok = left >= right
            elif isinstance(op, ast.In):
                ok = left in right
            elif isinstance(op, ast.NotIn):
                ok = left not in right
            else:
                raise ValueError(f"Unsupported comparison: {type(op).__name__}")
            if not ok:
                return False
            left = right
        return True

    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return _eval_node(node.left, inputs, state, schemas, error) + _eval_node(
            node.right, inputs, state, schemas, error
        )

    raise ValueError(f"Unsupported expression node: {type(node).__name__}")


def evaluate(expression: str, inputs: dict, state: dict, schemas: dict, error: Any = None) -> Any:
    expression = expression.strip()
    if expression.startswith("="):
        expression = expression[1:].strip()
    # Convert the workflow DSL's length(...) to our safe Python evaluator.
    tree = ast.parse(expression, mode="eval")
    return _eval_node(tree.body, inputs, state, schemas, error)
