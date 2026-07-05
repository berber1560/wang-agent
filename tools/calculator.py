from __future__ import annotations

import ast
import operator
from typing import Any, Callable

from tools.registry import BaseTool, ToolResult


class CalculatorTool(BaseTool):
    name = "calculator"
    description = "Safely evaluate basic arithmetic expressions."
    parameters = {
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "Arithmetic expression to evaluate.",
            }
        },
        "required": ["expression"],
    }

    _binary_operators: dict[type[ast.operator], Callable[[float, float], float]] = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
    }
    _unary_operators: dict[type[ast.unaryop], Callable[[float], float]] = {
        ast.UAdd: operator.pos,
        ast.USub: operator.neg,
    }

    def run(self, arguments: dict[str, Any]) -> ToolResult:
        expression = arguments.get("expression")
        if not isinstance(expression, str) or not expression.strip():
            return ToolResult(success=False, error="Expression must be a non-empty string.")

        try:
            parsed = ast.parse(expression, mode="eval")
            result = self._evaluate(parsed.body)
        except ZeroDivisionError:
            return ToolResult(success=False, error="Division by zero is not allowed.")
        except (SyntaxError, ValueError, TypeError) as exc:
            return ToolResult(success=False, error=f"Invalid expression: {exc}")

        return ToolResult(success=True, data={"result": result})

    def _evaluate(self, node: ast.AST) -> float:
        if isinstance(node, ast.BinOp):
            return self._evaluate_binary_operation(node)
        if isinstance(node, ast.UnaryOp):
            return self._evaluate_unary_operation(node)
        if isinstance(node, ast.Constant):
            return self._evaluate_constant(node.value)

        raise ValueError(f"unsupported expression node {type(node).__name__}")

    def _evaluate_binary_operation(self, node: ast.BinOp) -> float:
        operator_func = self._binary_operators.get(type(node.op))
        if operator_func is None:
            raise ValueError(f"unsupported operator {type(node.op).__name__}")

        left = self._evaluate(node.left)
        right = self._evaluate(node.right)
        return operator_func(left, right)

    def _evaluate_unary_operation(self, node: ast.UnaryOp) -> float:
        operator_func = self._unary_operators.get(type(node.op))
        if operator_func is None:
            raise ValueError(f"unsupported operator {type(node.op).__name__}")

        return operator_func(self._evaluate(node.operand))

    def _evaluate_constant(self, value: object) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("only numeric constants are allowed")

        return value
