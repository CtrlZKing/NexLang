import io
import pytest
from compiler.api import run_source
from compiler.errors.errors import NexError


def run(src):
    out = io.StringIO()
    run_source(src, filename="<test>", output=out)
    return out.getvalue()


# ---- maps ----

def test_map_literal_and_indexing():
    assert run('SET x TO {"a": 1, "b": 2}\nSAY x["a"]\n') == "1\n"


def test_empty_map():
    assert run("SET x TO {}\nSAY SIZE OF x\n") == "0\n"


def test_map_say_output_format():
    assert run('SAY {"a": 1}\n') == "{a: 1}\n"


def test_map_key_not_found_is_clear_error():
    with pytest.raises(NexError) as exc_info:
        run('SET x TO {"a": 1}\nSAY x["missing"]\n')
    assert exc_info.value.code == "NX221"


def test_map_unhashable_key_is_clear_error():
    with pytest.raises(NexError) as exc_info:
        run('SET x TO {[1, 2]: "bad"}\n')
    assert exc_info.value.code == "NX204"


def test_map_contains_checks_keys():
    assert run('IF {"a": 1} CONTAINS "a" THEN\n    SAY "yes"\nEND\n') == "yes\n"


def test_for_each_key_value_over_map():
    src = 'SET person TO {"name": "Aditya", "age": 15}\nFOR EACH k, v IN person\n    SAY "{k}={v}"\nEND\n'
    out = run(src)
    assert "name=Aditya" in out
    assert "age=15" in out


def test_for_each_key_value_on_non_map_is_clear_error():
    with pytest.raises(NexError) as exc_info:
        run("FOR EACH k, v IN [1, 2, 3]\n    SAY k\nEND\n")
    assert exc_info.value.code == "NX204"


def test_keys_and_values_builtins():
    src = 'SET x TO {"a": 1, "b": 2}\nSAY KEYS(x)\nSAY VALUES(x)\n'
    assert run(src) == "[a, b]\n[1, 2]\n"


def test_keys_on_non_map_is_clear_error():
    with pytest.raises(NexError) as exc_info:
        run("SAY KEYS([1, 2])\n")
    assert exc_info.value.code == "NX204"


def test_nested_map_and_list():
    src = 'SET data TO {"nums": [1, 2, 3]}\nSAY data["nums"][1]\n'
    assert run(src) == "2\n"


# ---- sets ----

def test_set_of_builtin():
    assert run("SAY SET_OF([1, 2, 2, 3])\n") == "{1, 2, 3}\n"


def test_set_membership_and_size():
    src = "SET s TO SET_OF([1, 2, 3])\nIF s CONTAINS 2 THEN\n    SAY \"yes\"\nEND\nSAY SIZE OF s\n"
    assert run(src) == "yes\n3\n"


def test_add_and_remove_from_set():
    src = "SET s TO SET_OF([1, 2])\nADD 3 TO s\nSAY SORTED(LIST_OF(s))\nREMOVE 1 FROM s\nSAY SORTED(LIST_OF(s))\n"
    assert run(src) == "[1, 2, 3]\n[2, 3]\n"


def test_remove_missing_from_set_is_clear_error():
    with pytest.raises(NexError) as exc_info:
        run("SET s TO SET_OF([1])\nREMOVE 99 FROM s\n")
    assert exc_info.value.code == "NX216"


def test_for_each_over_set():
    src = "SET s TO SET_OF([1, 2, 3])\nFOR EACH n IN SORTED(LIST_OF(s))\n    SAY n\nEND\n"
    assert run(src) == "1\n2\n3\n"


# ---- tuples ----

def test_tuple_of_builtin():
    assert run("SAY TUPLE_OF([1, 2, 3])\n") == "(1, 2, 3)\n"


def test_tuple_indexing():
    assert run("SET t TO TUPLE_OF([10, 20, 30])\nSAY t[1]\n") == "20\n"


def test_tuple_is_immutable():
    with pytest.raises(NexError) as exc_info:
        run("SET t TO TUPLE_OF([1, 2])\nADD 3 TO t\n")
    assert exc_info.value.code == "NX204"


def test_list_of_converts_back():
    assert run("SET t TO TUPLE_OF([1, 2])\nSET l TO LIST_OF(t)\nADD 3 TO l\nSAY l\n") == "[1, 2, 3]\n"


# ---- slicing ----

def test_slice_list_both_bounds():
    assert run("SAY [1, 2, 3, 4, 5][1:3]\n") == "[2, 3]\n"


def test_slice_list_open_start():
    assert run("SAY [1, 2, 3][:2]\n") == "[1, 2]\n"


def test_slice_list_open_end():
    assert run("SAY [1, 2, 3][1:]\n") == "[2, 3]\n"


def test_slice_list_full_copy():
    assert run("SET a TO [1, 2, 3]\nSET b TO a[:]\nADD 4 TO b\nSAY a\nSAY b\n") == "[1, 2, 3]\n[1, 2, 3, 4]\n"


def test_slice_text():
    assert run('SAY "hello world"[0:5]\n') == "hello\n"


def test_slice_non_number_bound_is_clear_error():
    with pytest.raises(NexError) as exc_info:
        run('SAY [1, 2, 3]["a":2]\n')
    assert exc_info.value.code == "NX204"


def test_slice_on_map_is_clear_error():
    with pytest.raises(NexError) as exc_info:
        run('SAY {"a": 1}[0:1]\n')
    assert exc_info.value.code == "NX204"


# ---- combining Phase 2 and Phase 3 ----

def test_function_returning_a_map():
    src = (
        "FUNCTION make_person(name, age)\n"
        '    RETURN {"name": name, "age": age}\n'
        "END\n"
        'SET p TO make_person("Aditya", 15)\n'
        'SAY p["name"]\n'
    )
    assert run(src) == "Aditya\n"


def test_try_catch_around_map_key_error():
    src = 'TRY\n    SAY {"a": 1}["missing"]\nCATCH err\n    SAY "caught"\nEND\n'
    assert run(src) == "caught\n"
