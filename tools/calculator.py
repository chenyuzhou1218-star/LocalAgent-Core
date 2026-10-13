from __future__ import annotations

import ast
import math
import operator
import re


_BINOPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY = {ast.UAdd: operator.pos, ast.USub: operator.neg}
_FUNCTIONS = {
    "abs": abs,
    "round": round,
    "sqrt": math.sqrt,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "log": math.log,
    "log10": math.log10,
    "ceil": math.ceil,
    "floor": math.floor,
}


def _eval(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY:
        return _UNARY[type(node.op)](_eval(node.operand))
    if isinstance(node, ast.BinOp) and type(node.op) in _BINOPS:
        left, right = _eval(node.left), _eval(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > 100:
            raise ValueError("指数过大")
        return _BINOPS[type(node.op)](left, right)
    if isinstance(node, ast.Name) and node.id in {"pi", "e"}:
        return getattr(math, node.id)
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in _FUNCTIONS:
        return _FUNCTIONS[node.func.id](*[_eval(arg) for arg in node.args])
    raise ValueError("只支持安全的数学表达式和白名单函数")


def calculate_expression(expression: str):
    expression = str(expression or "").strip().replace("^", "**")
    if not expression or len(expression) > 300:
        return {"success": False, "error": "表达式为空或过长"}
    try:
        value = _eval(ast.parse(expression, mode="eval").body)
        if not math.isfinite(float(value)):
            raise ValueError("结果不是有限数")
        return {"success": True, "expression": expression, "result": round(value, 12)}
    except Exception as exc:
        return {"success": False, "error": f"无法计算：{exc}"}


_UNITS = {
    "长度": {"米": 1, "千米": 1000, "厘米": 0.01, "毫米": 0.001, "英尺": 0.3048, "英寸": 0.0254},
    "质量": {"千克": 1, "克": 0.001, "毫克": 0.000001, "磅": 0.45359237},
    "时间": {"秒": 1, "分钟": 60, "小时": 3600, "天": 86400},
    "速度": {"米/秒": 1, "千米/小时": 1 / 3.6, "英里/小时": 0.44704},
}


def convert_units(value: float, from_unit: str, to_unit: str, category: str = ""):
    from_unit, to_unit = str(from_unit).strip(), str(to_unit).strip()
    category = str(category or "").strip()
    if not category:
        category = next((name for name, units in _UNITS.items() if from_unit in units and to_unit in units), "")
    units = _UNITS.get(category)
    if not units or from_unit not in units or to_unit not in units:
        return {"success": False, "error": "暂不支持这组单位。支持长度、质量、时间、速度。"}
    result = float(value) * units[from_unit] / units[to_unit]
    return {"success": True, "category": category, "value": value, "from": from_unit, "to": to_unit, "result": round(result, 10)}
