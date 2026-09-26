import pytest
from compiler.api import check_source
from compiler.errors.errors import NexError


def check(src, filename="<test>", base_dir=None):
    from compiler.api import parse_source
    from compiler.semantic.analyzer import SemanticAnalyzer
    program = parse_source(src, filename)
    analyzer = SemanticAnalyzer(src.splitlines(), filename, base_dir=base_dir)
    warnings = analyzer.analyze(program)
    return warnings


# ---- undefined names ----

def test_undefined_variable_is_caught_statically():
    with pytest.raises(NexError) as exc_info:
        check("SAY totally_unknown_name\n")
    assert exc_info.value.code == "NX401"


def test_undefined_variable_gives_did_you_mean_suggestion():
    with pytest.raises(NexError) as exc_info:
        check("SET username TO \"a\"\nSAY usernme\n")
    assert exc_info.value.code == "NX401"
    assert any("username" in s for s in exc_info.value.suggestions)


def test_defined_variable_is_fine():
    assert check('SET x TO 1\nSAY x\n') == []


def test_variable_defined_in_if_branch_is_not_visible_after():
    with pytest.raises(NexError) as exc_info:
        check('IF 1 IS 1 THEN\n    SET x TO 1\nEND\nSAY x\n')
    assert exc_info.value.code == "NX401"


def test_variable_defined_in_if_branch_is_visible_inside_it():
    assert check('IF 1 IS 1 THEN\n    SET x TO 1\n    SAY x\nEND\n') == []


def test_for_each_loop_variable_scoped_to_loop():
    assert check('FOR EACH item IN [1, 2, 3]\n    SAY item\nEND\n') == []
    with pytest.raises(NexError):
        check('FOR EACH item IN [1, 2, 3]\n    SAY item\nEND\nSAY item\n')


def test_function_parameter_visible_in_body():
    assert check("FUNCTION echo(x)\n    SAY x\nEND\n") == []


def test_function_parameter_not_visible_outside():
    with pytest.raises(NexError):
        check("FUNCTION echo(x)\n    SAY x\nEND\nSAY x\n")


def test_closure_sees_enclosing_function_local():
    src = (
        "FUNCTION outer(base)\n"
        "    FUNCTION inner(x)\n"
        "        SAY base + x\n"
        "    END\n"
        "END\n"
    )
    assert check(src) == []


def test_recursive_function_can_call_itself():
    src = "FUNCTION fact(n)\n    IF n IS AT MOST 1 THEN\n        RETURN 1\n    END\n    RETURN n * fact(n - 1)\nEND\n"
    assert check(src) == []


def test_ask_into_declares_the_variable():
    assert check('ASK "Name?" INTO name\nSAY name\n') == []


def test_try_catch_variable_scoped_to_catch_block():
    assert check('TRY\n    SAY 1\nCATCH err\n    SAY err\nEND\n') == []
    with pytest.raises(NexError):
        check('TRY\n    SAY 1\nCATCH err\n    SAY err\nEND\nSAY err\n')


# ---- unknown functions ----

def test_undefined_function_is_caught_statically():
    with pytest.raises(NexError) as exc_info:
        check("SAY not_a_real_function(1)\n")
    assert exc_info.value.code == "NX402"


def test_builtin_functions_are_recognized():
    assert check("SAY SUM([1, 2, 3])\n") == []
    assert check("SAY sum([1, 2, 3])\n") == []  # case-insensitive, like the interpreter


def test_calling_a_variable_like_a_function_is_an_error():
    with pytest.raises(NexError) as exc_info:
        check("SET x TO 5\nSAY x(1)\n")
    assert exc_info.value.code == "NX402"


def test_user_function_visible_after_its_own_declaration():
    assert check("FUNCTION greet()\n    RETURN 1\nEND\nSAY greet()\n") == []


# ---- duplicate declarations ----

def test_duplicate_parameter_name():
    with pytest.raises(NexError) as exc_info:
        check("FUNCTION f(a, a)\n    RETURN a\nEND\n")
    assert exc_info.value.code == "NX403"


def test_duplicate_function_declaration():
    with pytest.raises(NexError) as exc_info:
        check("FUNCTION f()\n    RETURN 1\nEND\nFUNCTION f()\n    RETURN 2\nEND\n")
    assert exc_info.value.code == "NX403"


def test_set_colliding_with_existing_function_name():
    with pytest.raises(NexError) as exc_info:
        check("FUNCTION f()\n    RETURN 1\nEND\nSET f TO 5\n")
    assert exc_info.value.code == "NX403"


def test_plain_reassignment_is_not_a_duplicate():
    assert check("SET x TO 1\nSET x TO 2\nSAY x\n") == []


def test_shadowing_in_a_nested_scope_is_allowed():
    # A loop variable with the same name as an outer variable shadows it
    # for the loop body only - this mirrors real interpreter scoping
    # (each block is a fresh child Environment) and is not an error.
    src = "SET item TO 99\nFOR EACH item IN [1, 2]\n    SAY item\nEND\nSAY item\n"
    assert check(src) == []


# ---- argument-count mismatches ----

def test_too_few_arguments_is_a_static_error():
    with pytest.raises(NexError) as exc_info:
        check("FUNCTION f(a, b)\n    RETURN a\nEND\nSAY f(1)\n")
    assert exc_info.value.code == "NX404"


def test_too_many_arguments_is_a_static_error():
    with pytest.raises(NexError) as exc_info:
        check("FUNCTION f(a)\n    RETURN a\nEND\nSAY f(1, 2, 3)\n")
    assert exc_info.value.code == "NX404"


def test_default_parameters_make_argument_optional():
    assert check('FUNCTION f(a, b = 10)\n    RETURN a + b\nEND\nSAY f(1)\n') == []


def test_builtin_arity_is_not_statically_checked():
    # Builtins validate their own arity at runtime; the static analyzer
    # doesn't second-guess them (avoids duplicating that logic here).
    assert check("SAY SUM([1, 2, 3])\n") == []


# ---- type mismatches ----

def test_set_annotation_matching_literal_is_fine():
    assert check("SET age AS NUMBER TO 15\n") == []


def test_set_annotation_mismatched_literal_is_an_error():
    with pytest.raises(NexError) as exc_info:
        check('SET age AS NUMBER TO "fifteen"\n')
    assert exc_info.value.code == "NX405"


def test_set_annotation_with_unknowable_expression_is_not_flagged():
    # Calling a function whose return type isn't annotated is "unknown"
    # to the checker - it must not guess and produce a false positive.
    src = "FUNCTION make()\n    RETURN 5\nEND\nSET x AS TEXT TO make()\n"
    assert check(src) == []


def test_union_annotation_accepts_either_type():
    assert check("SET x AS NUMBER OR TEXT TO 5\n") == []
    assert check('SET x AS NUMBER OR TEXT TO "five"\n') == []


def test_optional_annotation_accepts_null():
    assert check("SET x AS NUMBER OR NOTHING TO NULL\n") == []


def test_optional_annotation_rejects_wrong_type():
    with pytest.raises(NexError) as exc_info:
        check('SET x AS NUMBER OR NOTHING TO "text"\n')
    assert exc_info.value.code == "NX405"


def test_any_annotation_accepts_everything():
    assert check('SET x AS ANY TO "anything"\n') == []
    assert check("SET x AS ANY TO 5\n") == []


def test_function_parameter_type_mismatch_at_call_site():
    src = "FUNCTION combine(a AS NUMBER, b AS NUMBER)\n    RETURN a + b\nEND\nSAY combine(1, \"x\")\n"
    with pytest.raises(NexError) as exc_info:
        check(src)
    assert exc_info.value.code == "NX405"


def test_function_parameter_type_match_at_call_site_is_fine():
    src = "FUNCTION combine(a AS NUMBER, b AS NUMBER)\n    RETURN a + b\nEND\nSAY combine(1, 2)\n"
    assert check(src) == []


def test_function_return_type_mismatch():
    with pytest.raises(NexError) as exc_info:
        check('FUNCTION f() RETURNS NUMBER\n    RETURN "not a number"\nEND\n')
    assert exc_info.value.code == "NX405"


def test_function_return_type_match_is_fine():
    assert check("FUNCTION f() RETURNS NUMBER\n    RETURN 5\nEND\n") == []


def test_bare_return_with_returns_annotation_must_be_nothing_compatible():
    with pytest.raises(NexError) as exc_info:
        check("FUNCTION f() RETURNS NUMBER\n    RETURN\nEND\n")
    assert exc_info.value.code == "NX405"


def test_bare_return_is_fine_when_returns_allows_nothing():
    assert check("FUNCTION f() RETURNS NUMBER OR NOTHING\n    RETURN\nEND\n") == []


def test_default_parameter_value_type_checked_against_annotation():
    with pytest.raises(NexError) as exc_info:
        check('FUNCTION f(a AS NUMBER = "not a number")\n    RETURN a\nEND\n')
    assert exc_info.value.code == "NX405"


def test_arithmetic_inference_for_type_checking():
    # `1 + 2` statically infers to NUMBER, so this should be fine...
    assert check("SET x AS NUMBER TO 1 + 2\n") == []
    # ...and this should be flagged (TEXT expected, NUMBER given).
    with pytest.raises(NexError):
        check("SET x AS TEXT TO 1 + 2\n")


def test_comparison_infers_boolean():
    assert check("SET x AS BOOLEAN TO 1 IS 1\n") == []


# ---- unreachable code (warnings, not errors) ----

def test_code_after_return_is_a_warning_not_an_error():
    src = 'FUNCTION f()\n    RETURN 1\n    SAY "dead"\nEND\n'
    warnings = check(src)
    assert len(warnings) == 1
    assert warnings[0].code == "NX406"


def test_code_after_break_is_a_warning():
    src = "FOR EACH x IN [1, 2]\n    BREAK\n    SAY x\nEND\n"
    warnings = check(src)
    assert len(warnings) == 1
    assert warnings[0].code == "NX406"


def test_no_warning_when_return_is_last_statement():
    assert check("FUNCTION f()\n    RETURN 1\nEND\n") == []


def test_only_one_warning_per_block_even_with_multiple_dead_statements():
    src = 'FUNCTION f()\n    RETURN 1\n    SAY "a"\n    SAY "b"\nEND\n'
    warnings = check(src)
    assert len(warnings) == 1


# ---- IMPORT resolution ----

def test_import_brings_static_names_into_scope(tmp_path):
    (tmp_path / "lib.nex").write_text("FUNCTION doubled(x)\n    RETURN x * 2\nEND\nSET shared TO 1\n")
    src = 'IMPORT "lib.nex"\nSAY doubled(21)\nSAY shared\n'
    assert check(src, base_dir=str(tmp_path)) == []


def test_import_brings_typed_signature_into_scope(tmp_path):
    (tmp_path / "lib.nex").write_text("FUNCTION doubled(x AS NUMBER) RETURNS NUMBER\n    RETURN x * 2\nEND\n")
    src = 'IMPORT "lib.nex"\nSAY doubled("not a number")\n'
    with pytest.raises(NexError) as exc_info:
        check(src, base_dir=str(tmp_path))
    assert exc_info.value.code == "NX405"


def test_missing_import_file_suppresses_false_positives_rather_than_guessing(tmp_path):
    src = 'IMPORT "does_not_exist.nex"\nSAY whatever_this_import_would_have_defined\n'
    assert check(src, base_dir=str(tmp_path)) == []


def test_dynamic_import_path_suppresses_false_positives(tmp_path):
    src = 'SET path TO "lib.nex"\nIMPORT path\nSAY whatever_this_would_define\n'
    assert check(src, base_dir=str(tmp_path)) == []
