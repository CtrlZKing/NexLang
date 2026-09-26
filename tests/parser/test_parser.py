import pytest
from compiler.api import parse_source
from compiler.ast_nodes import nodes as ast
from compiler.errors.errors import NexError


def test_variable_declaration():
    prog = parse_source("SET x TO 10")
    assert len(prog.statements) == 1
    decl = prog.statements[0]
    assert isinstance(decl, ast.VariableDeclaration)
    assert decl.names == ["x"]
    assert isinstance(decl.values[0], ast.Literal)
    assert decl.values[0].value == 10


def test_multiple_assignment():
    prog = parse_source("SET x, y TO 10, 20")
    decl = prog.statements[0]
    assert decl.names == ["x", "y"]
    assert [v.value for v in decl.values] == [10, 20]


def test_say_statement():
    prog = parse_source('SAY "hello"')
    stmt = prog.statements[0]
    assert isinstance(stmt, ast.SayStatement)
    assert isinstance(stmt.expression, ast.Literal)
    assert stmt.expression.value == "hello"


def test_arithmetic_precedence():
    prog = parse_source("SET x TO 2 + 3 * 4")
    decl = prog.statements[0]
    expr = decl.values[0]
    assert isinstance(expr, ast.BinaryExpression)
    assert expr.operator == "+"
    assert isinstance(expr.right, ast.BinaryExpression)
    assert expr.right.operator == "*"


def test_power_is_right_associative():
    prog = parse_source("SET x TO 2 ** 3 ** 2")
    expr = prog.statements[0].values[0]
    assert expr.operator == "**"
    assert expr.left.value == 2
    assert isinstance(expr.right, ast.BinaryExpression)
    assert expr.right.left.value == 3
    assert expr.right.right.value == 2


def test_if_then_otherwise_end():
    src = """
IF x IS AT LEAST 18 THEN
    SAY "Adult"
OTHERWISE
    SAY "Minor"
END
"""
    prog = parse_source(src)
    stmt = prog.statements[0]
    assert isinstance(stmt, ast.IfStatement)
    assert isinstance(stmt.condition, ast.BinaryExpression)
    assert stmt.condition.operator == ">="
    assert len(stmt.then_branch) == 1
    assert len(stmt.else_branch) == 1


def test_else_if_chain():
    src = """
IF x IS 1 THEN
    SAY "one"
ELSE IF x IS 2 THEN
    SAY "two"
OTHERWISE
    SAY "other"
END
"""
    prog = parse_source(src)
    top = prog.statements[0]
    assert isinstance(top, ast.IfStatement)
    nested = top.else_branch[0]
    assert isinstance(nested, ast.IfStatement)
    assert nested.condition.right.value == 2
    assert nested.else_branch is not None


def test_while_loop():
    src = """
WHILE x IS BELOW 10
    x = x + 1
END
"""
    prog = parse_source(src)
    stmt = prog.statements[0]
    assert isinstance(stmt, ast.WhileStatement)
    assert stmt.condition.operator == "<"
    assert isinstance(stmt.body[0], ast.Assignment)


def test_repeat_times_loop():
    prog = parse_source("REPEAT 5 TIMES\n    SAY \"hi\"\nEND")
    stmt = prog.statements[0]
    assert isinstance(stmt, ast.RepeatTimesStatement)
    assert stmt.count.value == 5


def test_repeat_until_loop():
    prog = parse_source("REPEAT UNTIL x IS 0\n    x = x - 1\nEND")
    stmt = prog.statements[0]
    assert isinstance(stmt, ast.RepeatUntilStatement)


def test_break_and_continue():
    src = "WHILE TRUE\n    BREAK\nEND"
    prog = parse_source(src)
    body = prog.statements[0].body
    assert isinstance(body[0], ast.BreakStatement)


def test_missing_end_gives_friendly_error():
    with pytest.raises(NexError) as exc_info:
        parse_source("IF x IS 1 THEN\n    SAY \"hi\"")
    assert exc_info.value.code == "NX203"


def test_compound_assignment():
    prog = parse_source("x += 1")
    stmt = prog.statements[0]
    assert isinstance(stmt, ast.CompoundAssignment)
    assert stmt.operator == "+"


def test_increase_decrease_sugar():
    prog = parse_source("INCREASE x BY 5\nDECREASE y BY 2")
    inc, dec = prog.statements
    assert isinstance(inc, ast.CompoundAssignment) and inc.operator == "+"
    assert isinstance(dec, ast.CompoundAssignment) and dec.operator == "-"


def test_logical_operators():
    prog = parse_source("SET x TO TRUE AND FALSE OR NOT TRUE")
    expr = prog.statements[0].values[0]
    assert isinstance(expr, ast.LogicalExpression)
    assert expr.operator == "OR"


def test_grouping():
    prog = parse_source("SET x TO (2 + 3) * 4")
    expr = prog.statements[0].values[0]
    assert expr.operator == "*"
    assert isinstance(expr.left, ast.Grouping)


def test_ask_statement():
    prog = parse_source('ASK "Name?" INTO username')
    stmt = prog.statements[0]
    assert isinstance(stmt, ast.AskStatement)
    assert stmt.target == "username"


def test_interpolated_string_detected():
    prog = parse_source('SAY "Hello {name}"')
    stmt = prog.statements[0]
    assert isinstance(stmt.expression, ast.InterpolatedString)


def test_unexpected_token_error_has_code():
    with pytest.raises(NexError) as exc_info:
        parse_source("SET TO 10")
    assert exc_info.value.code.startswith("NX2")
