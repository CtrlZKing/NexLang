import io
import pytest
from compiler.api import run_source
from compiler.errors.errors import NexError


def run(src):
    out = io.StringIO()
    run_source(src, filename="<test>", output=out)
    return out.getvalue()


# ---- list literals & indexing ----

def test_list_literal_and_say():
    assert run("SET x TO [1, 2, 3]\nSAY x\n") == "[1, 2, 3]\n"


def test_list_indexing():
    assert run("SET x TO [10, 20, 30]\nSAY x[1]\n") == "20\n"


def test_negative_indexing():
    assert run("SET x TO [10, 20, 30]\nSAY x[-1]\n") == "30\n"


def test_index_out_of_range_is_clear_error():
    with pytest.raises(NexError) as exc_info:
        run("SET x TO [1, 2]\nSAY x[5]\n")
    assert exc_info.value.code == "NX221"


def test_nested_list_indexing():
    assert run("SET m TO [[1, 2], [3, 4]]\nSAY m[1][0]\n") == "3\n"


def test_string_indexing():
    assert run('SET s TO "hello"\nSAY s[0]\n') == "h\n"


# ---- ADD / REMOVE ----

def test_add_to_list_mutates_in_place():
    assert run("SET x TO [1, 2]\nADD 3 TO x\nSAY x\n") == "[1, 2, 3]\n"


def test_remove_from_list():
    assert run("SET x TO [1, 2, 3]\nREMOVE 2 FROM x\nSAY x\n") == "[1, 3]\n"


def test_remove_value_not_present_is_clear_error():
    with pytest.raises(NexError) as exc_info:
        run("SET x TO [1, 2]\nREMOVE 99 FROM x\n")
    assert exc_info.value.code == "NX216"


def test_add_to_non_list_is_clear_error():
    with pytest.raises(NexError) as exc_info:
        run("SET x TO 5\nADD 1 TO x\n")
    assert exc_info.value.code == "NX204"


# ---- SIZE OF / IS EMPTY / CONTAINS ----

def test_size_of_list():
    assert run("SET x TO [1, 2, 3]\nSAY SIZE OF x\n") == "3\n"


def test_size_of_text():
    assert run('SAY SIZE OF "hello"\n') == "5\n"


def test_is_empty_true_and_false():
    assert run("SET x TO []\nIF x IS EMPTY THEN\n    SAY \"yes\"\nEND\n") == "yes\n"
    assert run('SET x TO [1]\nIF x IS EMPTY THEN\n    SAY "yes"\nOTHERWISE\n    SAY "no"\nEND\n') == "no\n"


def test_contains_on_list():
    assert run('IF [1, 2, 3] CONTAINS 2 THEN\n    SAY "yes"\nEND\n') == "yes\n"


def test_contains_on_text():
    assert run('IF "hello world" CONTAINS "wor" THEN\n    SAY "yes"\nEND\n') == "yes\n"


def test_starts_with_and_ends_with():
    assert run('IF "hello" STARTS WITH "he" THEN\n    SAY "s"\nEND\n') == "s\n"
    assert run('IF "hello" ENDS WITH "lo" THEN\n    SAY "e"\nEND\n') == "e\n"


def test_is_between():
    assert run('IF 5 IS BETWEEN 1 AND 10 THEN\n    SAY "in"\nEND\n') == "in\n"
    assert run('IF 50 IS BETWEEN 1 AND 10 THEN\n    SAY "in"\nOTHERWISE\n    SAY "out"\nEND\n') == "out\n"


def test_null_is_alias_for_nothing():
    assert run("SET x TO NULL\nSAY x\n") == "nothing\n"
    assert run("SET x TO NULL\nIF x IS NULL THEN\n    SAY \"yes\"\nEND\n") == "yes\n"


# ---- FOR EACH / FOR range ----

def test_for_each_over_list():
    assert run("FOR EACH n IN [1, 2, 3]\n    SAY n\nEND\n") == "1\n2\n3\n"


def test_for_each_over_string():
    assert run('FOR EACH c IN "ab"\n    SAY c\nEND\n') == "a\nb\n"


def test_for_range_ascending():
    assert run("FOR i FROM 1 TO 3\n    SAY i\nEND\n") == "1\n2\n3\n"


def test_for_range_descending():
    assert run("FOR i FROM 3 DOWN TO 1\n    SAY i\nEND\n") == "3\n2\n1\n"


def test_for_each_break():
    src = "FOR EACH n IN [1, 2, 3, 4]\n    IF n IS 3 THEN\n        BREAK\n    END\n    SAY n\nEND\n"
    assert run(src) == "1\n2\n"


def test_for_each_continue():
    src = "FOR EACH n IN [1, 2, 3]\n    IF n IS 2 THEN\n        CONTINUE\n    END\n    SAY n\nEND\n"
    assert run(src) == "1\n3\n"


def test_for_range_break_and_continue():
    src = "FOR i FROM 1 TO 5\n    IF i IS 4 THEN\n        BREAK\n    END\n    IF i IS 2 THEN\n        CONTINUE\n    END\n    SAY i\nEND\n"
    assert run(src) == "1\n3\n"


def test_for_each_scope_does_not_leak():
    with pytest.raises(NexError) as exc_info:
        run("FOR EACH n IN [1]\n    SAY n\nEND\nSAY n\n")
    assert exc_info.value.code == "NX301"


def test_for_each_over_non_iterable_is_clear_error():
    with pytest.raises(NexError) as exc_info:
        run("FOR EACH n IN 5\n    SAY n\nEND\n")
    assert exc_info.value.code == "NX204"


# ---- built-in collection functions ----

def test_sum_average_max_min():
    assert run("SAY SUM([1, 2, 3])\n") == "6\n"
    assert run("SAY AVERAGE([2, 4])\n") == "3.0\n"
    assert run("SAY MAXIMUM([3, 1, 2])\n") == "3\n"
    assert run("SAY MINIMUM([3, 1, 2])\n") == "1\n"


def test_count_sorted_reversed_unique():
    assert run("SAY COUNT([1, 2, 3])\n") == "3\n"
    assert run("SAY SORTED([3, 1, 2])\n") == "[1, 2, 3]\n"
    assert run("SAY REVERSED([1, 2, 3])\n") == "[3, 2, 1]\n"
    assert run("SAY UNIQUE([1, 1, 2, 2, 3])\n") == "[1, 2, 3]\n"


def test_builtin_names_are_case_insensitive():
    assert run("SAY sum([1, 2, 3])\n") == "6\n"
    assert run("SAY Sum([1, 2, 3])\n") == "6\n"


def test_sum_of_empty_list_is_zero():
    assert run("SAY SUM([])\n") == "0\n"


def test_average_of_empty_list_is_clear_error():
    with pytest.raises(NexError) as exc_info:
        run("SAY AVERAGE([])\n")
    assert exc_info.value.code == "NX215"


def test_functions_and_collections_together():
    src = (
        "FUNCTION total_of(numbers)\n    RETURN SUM(numbers)\nEND\n"
        "SET nums TO [1, 2, 3, 4]\n"
        "SAY total_of(nums)\n"
    )
    assert run(src) == "10\n"
