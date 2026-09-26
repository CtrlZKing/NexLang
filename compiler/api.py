"""
High-level entry points into the NexLang toolchain.

This module exists so the CLI, REPL, and test suite all share one code
path for "take source text, run it, report errors nicely" instead of each
re-implementing lexer/parser/interpreter wiring.
"""

from __future__ import annotations
from compiler.lexer.lexer import tokenize
from compiler.parser.parser import Parser
from compiler.interpreter.interpreter import Interpreter
from compiler.errors.errors import NexError


def parse_source(source: str, filename: str = "<string>"):
    tokens = tokenize(source, filename)
    return Parser(tokens, source, filename).parse_program()


def run_source(source: str, filename: str = "<string>", output=None, input_fn=None) -> None:
    """Parse and execute NexLang source. Raises NexError on failure."""
    program = parse_source(source, filename)
    interpreter = Interpreter(source, filename, output=output, input_fn=input_fn)
    interpreter.run(program)


def check_source(source: str, filename: str = "<string>", semantic: bool = True):
    """Parse (syntax check) and, by default, also run static semantic
    analysis (Phase 3b - undefined names, duplicate declarations,
    argument-count and type-annotation mismatches; see
    compiler/semantic/analyzer.py). Raises NexError on the first problem
    found. Returns (program, warnings) - warnings is a list of non-fatal
    NexErrors (currently just unreachable-code) when semantic=True, or an
    empty list when semantic=False.

    `run_source` deliberately does NOT run this pass, so semantic
    analysis being added can never change what an already-working `nex
    run`/REPL program does - only what `nex check` reports about it.
    """
    program = parse_source(source, filename)
    warnings: list = []
    if semantic:
        from compiler.semantic.analyzer import SemanticAnalyzer
        analyzer = SemanticAnalyzer(source.splitlines(), filename)
        warnings = analyzer.analyze(program)
    return program, warnings
