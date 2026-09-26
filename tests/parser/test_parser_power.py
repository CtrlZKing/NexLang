import pytest
from compiler.api import parse_source
from compiler.errors.errors import NexError
from compiler.ast_nodes import nodes as ast


def parse(src):
    return parse_source(src, "<test>")


def test_function_declaration_with_default_param():
    prog = parse('FUNCTION greet(name = "friend")\n    RETURN "Hello, " + name\nEND\n')
    fn = prog.statements[0]
    assert isinstance(fn, ast.FunctionDeclaration)
    assert fn.name == "greet"
    assert [p.name for p in fn.params] == ["name"]
    assert fn.params[0].default is not None
    assert isinstance(fn.body[0], ast.ReturnStatement)


def test_function_call_parses_as_call_node():
    prog = parse('SAY greet("Aditya")\n')
    call = prog.statements[0].expression
    assert isinstance(call, ast.Call)
    assert call.name == "greet"
    assert len(call.args) == 1


def test_list_literal_and_indexing():
    prog = parse("SET x TO [1, 2, 3]\nSAY x[0]\n")
    lit = prog.statements[0].values[0]
    assert isinstance(lit, ast.ListLiteral)
    assert len(lit.elements) == 3
    idx = prog.statements[1].expression
    assert isinstance(idx, ast.IndexExpression)


def test_chained_indexing():
    prog = parse("SAY matrix[0][1]\n")
    idx = prog.statements[0].expression
    assert isinstance(idx, ast.IndexExpression)
    assert isinstance(idx.collection, ast.IndexExpression)


def test_add_to_and_remove_from_statements():
    prog = parse("ADD 5 TO numbers\nREMOVE 5 FROM numbers\n")
    assert isinstance(prog.statements[0], ast.AddToStatement)
    assert isinstance(prog.statements[1], ast.RemoveFromStatement)


def test_for_each_statement():
    prog = parse("FOR EACH item IN numbers\n    SAY item\nEND\n")
    node = prog.statements[0]
    assert isinstance(node, ast.ForEachStatement)
    assert node.var_name == "item"


def test_for_range_ascending_and_descending():
    prog = parse("FOR i FROM 1 TO 10\n    SAY i\nEND\n")
    node = prog.statements[0]
    assert isinstance(node, ast.ForRangeStatement)
    assert node.descending is False

    prog2 = parse("FOR i FROM 10 DOWN TO 1\n    SAY i\nEND\n")
    assert prog2.statements[0].descending is True


def test_try_catch_finally():
    prog = parse("TRY\n    SAY 1\nCATCH err\n    SAY err\nFINALLY\n    SAY 2\nEND\n")
    node = prog.statements[0]
    assert isinstance(node, ast.TryStatement)
    assert node.catch_var == "err"
    assert node.catch_body is not None
    assert node.finally_body is not None


def test_try_without_catch_or_finally_is_an_error():
    with pytest.raises(NexError) as exc_info:
        parse("TRY\n    SAY 1\nEND\n")
    assert exc_info.value.code == "NX213"


def test_try_finally_without_catch_is_allowed():
    prog = parse("TRY\n    SAY 1\nFINALLY\n    SAY 2\nEND\n")
    node = prog.statements[0]
    assert node.catch_body is None
    assert node.finally_body is not None


def test_import_statement():
    prog = parse('IMPORT "lib.nex"\n')
    node = prog.statements[0]
    assert isinstance(node, ast.ImportStatement)


def test_contains_starts_with_ends_with():
    prog = parse('IF x CONTAINS 5 THEN\n    SAY "yes"\nEND\n')
    cond = prog.statements[0].condition
    assert isinstance(cond, ast.BinaryExpression)
    assert cond.operator == "CONTAINS"

    prog2 = parse('IF name STARTS WITH "A" THEN\n    SAY "yes"\nEND\n')
    assert prog2.statements[0].condition.operator == "STARTS_WITH"

    prog3 = parse('IF name ENDS WITH "z" THEN\n    SAY "yes"\nEND\n')
    assert prog3.statements[0].condition.operator == "ENDS_WITH"


def test_is_between_desugars_to_and_of_comparisons():
    prog = parse("IF x IS BETWEEN 1 AND 10 THEN\n    SAY 1\nEND\n")
    cond = prog.statements[0].condition
    assert isinstance(cond, ast.LogicalExpression)
    assert cond.operator == "AND"
    assert cond.left.operator == ">="
    assert cond.right.operator == "<="


def test_is_empty():
    prog = parse("IF x IS EMPTY THEN\n    SAY 1\nEND\n")
    cond = prog.statements[0].condition
    assert isinstance(cond, ast.UnaryExpression)
    assert cond.operator == "IS_EMPTY"


def test_size_of():
    prog = parse("SET n TO SIZE OF numbers\n")
    val = prog.statements[0].values[0]
    assert isinstance(val, ast.UnaryExpression)
    assert val.operator == "SIZE_OF"


def test_file_exists_expression():
    prog = parse('IF FILE "data.txt" EXISTS THEN\n    SAY 1\nEND\n')
    cond = prog.statements[0].condition
    assert isinstance(cond, ast.UnaryExpression)
    assert cond.operator == "EXISTS"
    assert isinstance(cond.operand, ast.FileRef)


def test_read_file_expression():
    prog = parse('SET content TO READ FILE "data.txt"\n')
    val = prog.statements[0].values[0]
    assert isinstance(val, ast.ReadFileExpression)


def test_write_and_append_file_statements():
    prog = parse('WRITE "hi" TO FILE "out.txt"\nAPPEND "more" TO FILE "out.txt"\n')
    assert isinstance(prog.statements[0], ast.WriteFileStatement)
    assert prog.statements[0].append is False
    assert isinstance(prog.statements[1], ast.WriteFileStatement)
    assert prog.statements[1].append is True


def test_delete_file_statement():
    prog = parse('DELETE FILE "out.txt"\n')
    assert isinstance(prog.statements[0], ast.DeleteFileStatement)


def test_return_with_no_value():
    prog = parse("FUNCTION f()\n    RETURN\nEND\n")
    ret = prog.statements[0].body[0]
    assert isinstance(ret, ast.ReturnStatement)
    assert ret.value is None


def test_null_literal_is_nothing():
    prog = parse("SET x TO NULL\n")
    val = prog.statements[0].values[0]
    assert isinstance(val, ast.Literal)
    assert val.value is None


def test_unclosed_function_reports_missing_end():
    with pytest.raises(NexError) as exc_info:
        parse("FUNCTION f()\n    RETURN 1\n")
    assert exc_info.value.code == "NX203"


def test_unclosed_for_reports_missing_end():
    with pytest.raises(NexError) as exc_info:
        parse("FOR EACH x IN y\n    SAY x\n")
    assert exc_info.value.code == "NX203"
