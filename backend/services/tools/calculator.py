import ast
import operator

from .types import ToolResult, ToolSpec


ALLOWED_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

MAX_EXPRESSION_LENGTH = 200
MAX_ABSOLUTE_VALUE = 10 ** 12


def evaluate_node(node):
    if isinstance(node, ast.Expression):
        return evaluate_node(node.body)

    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value

    if isinstance(node, ast.BinOp) and type(node.op) in ALLOWED_OPERATORS:
        left = evaluate_node(node.left)
        right = evaluate_node(node.right)
        result = ALLOWED_OPERATORS[type(node.op)](left, right)
        validate_result_size(result)
        return result

    if isinstance(node, ast.UnaryOp) and type(node.op) in ALLOWED_OPERATORS:
        result = ALLOWED_OPERATORS[type(node.op)](evaluate_node(node.operand))
        validate_result_size(result)
        return result

    raise ValueError("unsupported or unsafe expression")


def validate_result_size(value):
    if abs(value) > MAX_ABSOLUTE_VALUE:
        raise ValueError("result is too large")


def execute_calculator(arguments: dict) -> ToolResult:
    expression = arguments.get("expression")

    if not isinstance(expression, str) or not expression.strip():
        return ToolResult(
            ok=False,
            error="expression is required",
        )

    if len(expression) > MAX_EXPRESSION_LENGTH:
        return ToolResult(
            ok=False,
            error="expression is too long",
        )

    try:
        tree = ast.parse(expression, mode="eval")
        result = evaluate_node(tree)
        return ToolResult(
            ok=True,
            result={
                "expression": expression,
                "value": result,
            },
        )
    except Exception as exc:
        return ToolResult(
            ok=False,
            error=str(exc),
        )


def get_calculator_tool() -> ToolSpec:
    return ToolSpec(
        name="calculator",
        description="Safely evaluate a basic math expression.",
        args_schema={
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Math expression using numbers and + - * / ** % ().",
                }
            },
            "required": ["expression"],
            "additionalProperties": False,
        },
        executor=execute_calculator,
    )
