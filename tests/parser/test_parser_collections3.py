import pytest
from compiler.api import parse_source
from compiler.errors.errors import NexError
from compiler.ast_nodes import nodes as ast


def parse(src):
    return parse_source(src, "<test>")


def test_map_literal():
    prog = parse('SET x TO {"a": 1, "b": 2}\n')
    lit = prog.statements[0].values[0]
    assert isinstance(lit, ast.MapLiteral)
    assert len(lit.keys) == 2


def test_empty_map_literal():
    prog = parse("SET x TO {}\n")
    lit = prog.statements[0].values[0]
    assert isinstance(lit, ast.MapLiteral)
    assert lit.keys == []


def test_map_literal_trailing_comma():
    prog = parse('SET x TO {"a": 1, "b": 2,}\n')
    lit = prog.statements[0].values[0]
    assert len(lit.keys) == 2


def test_map_literal_can_span_multiple_lines():
    prog = parse('SET x TO {\n    "a": 1,\n    "b": 2\n}\n')
    lit = prog.statements[0].values[0]
    assert len(lit.keys) == 2


def test_map_indexing_reuses_index_expression():
    prog = parse('SAY person["name"]\n')
    idx = prog.statements[0].expression
    assert isinstance(idx, ast.IndexExpression)


def test_slice_both_bounds():
    prog = parse("SAY numbers[1:3]\n")
    node = prog.statements[0].expression
    assert isinstance(node, ast.SliceExpression)
    assert node.start is not None and node.end is not None


def test_slice_open_start():
    prog = parse("SAY numbers[:3]\n")
    node = prog.statements[0].expression
    assert node.start is None
    assert node.end is not None


def test_slice_open_end():
    prog = parse("SAY numbers[3:]\n")
    node = prog.statements[0].expression
    assert node.start is not None
    assert node.end is None


def test_slice_both_open():
    prog = parse("SAY numbers[:]\n")
    node = prog.statements[0].expression
    assert node.start is None
    assert node.end is None


def test_for_each_key_value():
    prog = parse("FOR EACH k, v IN person\n    SAY k\nEND\n")
    node = prog.statements[0]
    assert isinstance(node, ast.ForEachPairStatement)
    assert node.key_name == "k"
    assert node.value_name == "v"


def test_for_each_single_still_works():
    prog = parse("FOR EACH item IN numbers\n    SAY item\nEND\n")
    node = prog.statements[0]
    assert isinstance(node, ast.ForEachStatement)


def test_unclosed_map_reports_missing_brace():
    with pytest.raises(NexError):
        parse('SET x TO {"a": 1\n')
