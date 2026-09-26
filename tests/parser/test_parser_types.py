import pytest
from compiler.api import parse_source
from compiler.errors.errors import NexError
from compiler.ast_nodes import nodes as ast


def parse(src):
    return parse_source(src, "<test>")


def test_variable_declaration_with_simple_annotation():
    prog = parse("SET age AS NUMBER TO 15\n")
    decl = prog.statements[0]
    assert isinstance(decl, ast.VariableDeclaration)
    assert decl.annotation is not None
    assert decl.annotation.names == ["NUMBER"]


def test_variable_declaration_without_annotation_has_none():
    prog = parse("SET age TO 15\n")
    assert prog.statements[0].annotation is None


def test_union_type_annotation():
    prog = parse("SET label AS TEXT OR NOTHING TO NULL\n")
    decl = prog.statements[0]
    assert decl.annotation.names == ["TEXT", "NOTHING"]


def test_annotation_keyword_type_names_set_function_nothing():
    # SET, FUNCTION, and NOTHING are also existing language keywords -
    # the type-annotation grammar has to special-case them.
    prog = parse("SET a AS SET TO SET_OF([1])\n")
    assert prog.statements[0].annotation.names == ["SET"]

    prog2 = parse("SET b AS FUNCTION TO 1\n")
    assert prog2.statements[0].annotation.names == ["FUNCTION"]

    prog3 = parse("SET c AS NOTHING TO NULL\n")
    assert prog3.statements[0].annotation.names == ["NOTHING"]


def test_unknown_type_name_is_a_clear_parse_error():
    with pytest.raises(NexError) as exc_info:
        parse("SET x AS WEIRDTYPE TO 5\n")
    assert exc_info.value.code == "NX224"


def test_annotation_on_multiple_assignment_is_rejected():
    with pytest.raises(NexError) as exc_info:
        parse("SET a, b AS NUMBER TO 1, 2\n")
    assert exc_info.value.code == "NX225"


def test_function_parameter_annotation():
    prog = parse("FUNCTION combine(a AS NUMBER, b AS NUMBER)\n    RETURN a + b\nEND\n")
    fn = prog.statements[0]
    assert fn.params[0].annotation.names == ["NUMBER"]
    assert fn.params[1].annotation.names == ["NUMBER"]


def test_function_parameter_annotation_with_default():
    prog = parse('FUNCTION greet(name AS TEXT = "friend")\n    RETURN name\nEND\n')
    param = prog.statements[0].params[0]
    assert param.annotation.names == ["TEXT"]
    assert param.default is not None


def test_function_without_annotations_still_works():
    prog = parse("FUNCTION combine(a, b)\n    RETURN a + b\nEND\n")
    fn = prog.statements[0]
    assert fn.params[0].annotation is None
    assert fn.returns is None


def test_function_returns_annotation():
    prog = parse("FUNCTION combine(a, b) RETURNS NUMBER\n    RETURN a + b\nEND\n")
    fn = prog.statements[0]
    assert fn.returns is not None
    assert fn.returns.names == ["NUMBER"]


def test_returns_union_annotation():
    prog = parse("FUNCTION maybe_find(x) RETURNS NUMBER OR NOTHING\n    RETURN x\nEND\n")
    assert prog.statements[0].returns.names == ["NUMBER", "NOTHING"]


def test_type_annotation_str_representation():
    prog = parse("SET x AS NUMBER OR TEXT TO 5\n")
    assert str(prog.statements[0].annotation) == "NUMBER OR TEXT"
