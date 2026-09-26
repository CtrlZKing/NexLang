"""
NexLang Parser
==============

A hand-written recursive-descent parser. This is the "simplest robust
approach" for a language at this stage: no parser-generator dependency,
easy to read, easy to extend statement-by-statement, and easy to attach
rich error messages to.

See docs/GRAMMAR.md for the formal grammar this implements.

Precedence (low to high):
    or
    and
    not
    comparison (== != < > <= >= IS IS NOT IS AT LEAST/MOST IS ABOVE/BELOW IN)
    additive (+ -)
    multiplicative (* / // %)
    unary (- NOT)
    power (**)
    primary (literals, identifiers, grouping)
"""

from __future__ import annotations
from typing import List, Optional

from compiler.lexer.tokens import Token, TokenType
from compiler.errors.errors import NexError, SourceLocation, closest_match
from compiler.ast_nodes import nodes as ast


class ParseError(NexError):
    pass


# Tokens that may legitimately begin a new statement - used for panic-mode
# recovery style error messages ("did you forget END?").
BLOCK_ENDERS = {TokenType.END, TokenType.OTHERWISE, TokenType.ELSE, TokenType.EOF}


class Parser:
    def __init__(self, tokens: List[Token], source: str, filename: str = "<string>"):
        self.tokens = tokens
        self.source_lines = source.splitlines()
        self.filename = filename
        self.pos = 0

    # ---- token stream helpers ----

    def _peek(self, offset: int = 0) -> Token:
        idx = min(self.pos + offset, len(self.tokens) - 1)
        return self.tokens[idx]

    def _advance(self) -> Token:
        tok = self.tokens[self.pos]
        if self.pos < len(self.tokens) - 1:
            self.pos += 1
        return tok

    def _check(self, *types: TokenType) -> bool:
        return self._peek().type in types

    def _match(self, *types: TokenType) -> Optional[Token]:
        if self._check(*types):
            return self._advance()
        return None

    def _source_line_text(self, line_no: int) -> str:
        if 1 <= line_no <= len(self.source_lines):
            return self.source_lines[line_no - 1]
        return ""

    def _error(self, code, title, explanation, token: Token = None, suggestions=None,
               help_topic=None, length=None) -> ParseError:
        token = token or self._peek()
        col = token.column
        lex_len = length if length is not None else max(len(str(token.lexeme or token.value or "")), 1)
        return ParseError(
            code=code,
            title=title,
            explanation=explanation,
            location=SourceLocation(self.filename, token.line, col, lex_len),
            suggestions=suggestions or [],
            source_line=self._source_line_text(token.line),
            help_topic=help_topic,
        )

    def _expect(self, type_: TokenType, human_name: str, help_topic=None) -> Token:
        if self._check(type_):
            return self._advance()
        got = self._peek()
        raise self._error(
            "NX201",
            f"Expected {human_name}",
            f"Expected {human_name} but found `{got.lexeme or got.value or got.type.name}` instead.",
            token=got,
            help_topic=help_topic,
        )

    def _skip_newlines(self):
        while self._match(TokenType.NEWLINE):
            pass

    def _end_statement(self):
        """A statement must be terminated by a newline (or be at EOF)."""
        if self._check(TokenType.EOF):
            return
        if not self._match(TokenType.NEWLINE):
            got = self._peek()
            raise self._error(
                "NX202",
                "Unexpected extra input",
                "Each statement must be on its own line in NexLang.",
                token=got,
                suggestions=["Put this on a new line."],
                help_topic="syntax",
            )

    # ---- entry point ----

    def parse_program(self) -> ast.Program:
        statements = []
        self._skip_newlines()
        while not self._check(TokenType.EOF):
            statements.append(self._statement())
            self._skip_newlines()
        return ast.Program(statements=statements)

    def _block(self, terminators) -> List[ast.Node]:
        """Parse statements until one of the given terminator token types is seen."""
        stmts = []
        self._skip_newlines()
        while not self._check(*terminators):
            if self._check(TokenType.EOF):
                raise self._error(
                    "NX203",
                    "Missing END",
                    "Reached the end of the file while still inside a block. "
                    "Every IF / WHILE / REPEAT / FOR / FUNCTION / TRY block must be closed with `END`.",
                    token=self._peek(),
                    suggestions=["END"],
                    help_topic="blocks",
                )
            stmts.append(self._statement())
            self._skip_newlines()
        return stmts

    # ---- statements ----

    def _statement(self) -> ast.Node:
        tok = self._peek()

        if tok.type == TokenType.SET:
            return self._var_declaration()
        if tok.type == TokenType.SAY:
            return self._say_statement()
        if tok.type == TokenType.ASK:
            return self._ask_statement()
        if tok.type == TokenType.IF:
            return self._if_statement()
        if tok.type == TokenType.WHILE:
            return self._while_statement()
        if tok.type == TokenType.REPEAT:
            return self._repeat_statement()
        if tok.type == TokenType.BREAK:
            self._advance()
            node = ast.BreakStatement(line=tok.line, column=tok.column)
            self._end_statement()
            return node
        if tok.type == TokenType.CONTINUE:
            self._advance()
            node = ast.ContinueStatement(line=tok.line, column=tok.column)
            self._end_statement()
            return node
        if tok.type == TokenType.INCREASE:
            return self._increase_decrease("+")
        if tok.type == TokenType.DECREASE:
            return self._increase_decrease("-")
        if tok.type == TokenType.FUNCTION:
            return self._function_declaration()
        if tok.type == TokenType.RETURN:
            return self._return_statement()
        if tok.type == TokenType.FOR:
            return self._for_statement()
        if tok.type == TokenType.TRY:
            return self._try_statement()
        if tok.type == TokenType.IMPORT:
            return self._import_statement()
        if tok.type == TokenType.ADD:
            return self._add_to_statement()
        if tok.type == TokenType.REMOVE:
            return self._remove_from_statement()
        if tok.type == TokenType.WRITE:
            return self._write_file_statement(append=False)
        if tok.type == TokenType.APPEND:
            return self._write_file_statement(append=True)
        if tok.type == TokenType.DELETE:
            return self._delete_file_statement()
        if tok.type == TokenType.IDENTIFIER:
            return self._identifier_led_statement()

        raise self._error(
            "NX204",
            "Unexpected token",
            f"`{tok.lexeme or tok.value}` cannot begin a statement here.",
            token=tok,
            help_topic="syntax",
        )

    def _var_declaration(self) -> ast.Node:
        set_tok = self._advance()  # SET
        names = [self._expect(TokenType.IDENTIFIER, "a variable name", help_topic="variables").value]
        while self._match(TokenType.COMMA):
            names.append(self._expect(TokenType.IDENTIFIER, "a variable name", help_topic="variables").value)

        # Optional "AS TYPE" annotation (Phase 3b) - only for a single name;
        # `SET a, b AS NUMBER TO 1, 2` is ambiguous (which name does the
        # type apply to?) so it's rejected with a clear error instead of a
        # guess.
        annotation = None
        if self._check(TokenType.AS):
            as_tok = self._peek()
            if len(names) > 1:
                raise self._error(
                    "NX225", "Type annotation on multiple assignment",
                    "`AS TYPE` only works when assigning to a single name - "
                    "it isn't clear which of several names it would describe.",
                    token=as_tok,
                    suggestions=[f"SET {names[0]} AS TYPE TO ...   # annotate one at a time"],
                    help_topic="types",
                )
            self._advance()
            annotation = self._type_annotation()

        self._expect(TokenType.TO, "`TO`", help_topic="variables")
        values = [self._expression()]
        while self._match(TokenType.COMMA):
            values.append(self._expression())

        if len(names) != len(values) and len(values) != 1:
            raise self._error(
                "NX205",
                "Mismatched multiple assignment",
                f"You are assigning to {len(names)} name(s) but provided {len(values)} value(s).",
                token=set_tok,
                suggestions=[
                    "SET a, b TO 1, 2",
                    "SET a, b TO some_pair   # unpacks a 2-item value",
                ],
                help_topic="variables",
            )

        node = ast.VariableDeclaration(names=names, values=values, line=set_tok.line, column=set_tok.column,
                                        annotation=annotation)
        self._end_statement()
        return node

    # ---- Phase 3b: type annotations ----

    KNOWN_TYPE_NAMES = {
        "NUMBER", "TEXT", "BOOLEAN", "NOTHING", "LIST", "MAP", "SET",
        "TUPLE", "FUNCTION", "ERROR", "ANY",
    }

    def _type_annotation(self) -> ast.TypeAnnotation:
        first = self._advance()  # first type name
        names = [self._type_name_from_token(first)]
        tok = first
        while self._check(TokenType.OR):
            self._advance()
            nxt = self._advance()
            names.append(self._type_name_from_token(nxt))
        return ast.TypeAnnotation(names=names, line=tok.line, column=tok.column)

    def _type_name_from_token(self, tok) -> str:
        # A handful of type names collide with existing keywords (FUNCTION,
        # NOTHING, SET), so those are recognized by token type; everything
        # else must be a plain identifier spelling a known type name.
        keyword_types = {
            TokenType.FUNCTION: "FUNCTION",
            TokenType.NOTHING: "NOTHING",
            TokenType.SET: "SET",
        }
        if tok.type in keyword_types:
            return keyword_types[tok.type]
        if tok.type == TokenType.IDENTIFIER and tok.value.upper() in self.KNOWN_TYPE_NAMES:
            return tok.value.upper()
        raise self._error(
            "NX224", "Unknown type name",
            f"`{tok.lexeme or tok.value}` isn't a NexLang type. "
            f"Known types: {', '.join(sorted(self.KNOWN_TYPE_NAMES))}.",
            token=tok,
            suggestions=["SET age AS NUMBER TO 15"],
            help_topic="types",
        )

    def _say_statement(self) -> ast.Node:
        tok = self._advance()
        expr = self._expression()
        node = ast.SayStatement(expression=expr, line=tok.line, column=tok.column)
        self._end_statement()
        return node

    def _ask_statement(self) -> ast.Node:
        tok = self._advance()
        prompt = self._expression()
        self._expect(TokenType.INTO, "`INTO`", help_topic="input")
        target = self._expect(TokenType.IDENTIFIER, "a variable name", help_topic="input").value
        node = ast.AskStatement(prompt=prompt, target=target, line=tok.line, column=tok.column)
        self._end_statement()
        return node

    def _if_statement(self) -> ast.Node:
        tok = self._advance()  # IF
        condition = self._expression()
        self._expect(TokenType.THEN, "`THEN`", help_topic="conditionals")
        then_branch = self._block({TokenType.OTHERWISE, TokenType.ELSE, TokenType.END})

        else_branch = None
        if self._check(TokenType.ELSE):
            self._advance()
            self._expect(TokenType.IF, "`IF` (as part of `ELSE IF`)", help_topic="conditionals")
            else_branch = [self._if_statement_tail(tok)]
            return ast.IfStatement(condition=condition, then_branch=then_branch,
                                    else_branch=else_branch, line=tok.line, column=tok.column)
        elif self._check(TokenType.OTHERWISE):
            self._advance()
            self._skip_newlines()
            if self._check(TokenType.IF):
                else_branch = [self._if_statement_tail(tok)]
            else:
                else_branch = self._block({TokenType.END})
                self._expect(TokenType.END, "`END` (closing this IF)", help_topic="conditionals")
        else:
            self._expect(TokenType.END, "`END` (closing this IF)", help_topic="conditionals")

        return ast.IfStatement(condition=condition, then_branch=then_branch,
                                else_branch=else_branch, line=tok.line, column=tok.column)

    def _if_statement_tail(self, outer_tok: Token) -> ast.Node:
        """Parses the rest of an ELSE IF chain without consuming a duplicate END;
        the outermost `_if_statement` call is the one that consumes the final END."""
        condition = self._expression()
        self._expect(TokenType.THEN, "`THEN`", help_topic="conditionals")
        then_branch = self._block({TokenType.OTHERWISE, TokenType.ELSE, TokenType.END})

        else_branch = None
        if self._check(TokenType.ELSE):
            self._advance()
            self._expect(TokenType.IF, "`IF` (as part of `ELSE IF`)", help_topic="conditionals")
            else_branch = [self._if_statement_tail(outer_tok)]
        elif self._check(TokenType.OTHERWISE):
            self._advance()
            self._skip_newlines()
            if self._check(TokenType.IF):
                else_branch = [self._if_statement_tail(outer_tok)]
            else:
                else_branch = self._block({TokenType.END})
                self._expect(TokenType.END, "`END` (closing this IF)", help_topic="conditionals")
        else:
            self._expect(TokenType.END, "`END` (closing this IF)", help_topic="conditionals")

        return ast.IfStatement(condition=condition, then_branch=then_branch,
                                else_branch=else_branch, line=outer_tok.line, column=outer_tok.column)

    def _while_statement(self) -> ast.Node:
        tok = self._advance()
        condition = self._expression()
        body = self._block({TokenType.END})
        self._expect(TokenType.END, "`END` (closing this WHILE)", help_topic="loops")
        return ast.WhileStatement(condition=condition, body=body, line=tok.line, column=tok.column)

    def _repeat_statement(self) -> ast.Node:
        tok = self._advance()  # REPEAT
        if self._match(TokenType.UNTIL):
            condition = self._expression()
            body = self._block({TokenType.END})
            self._expect(TokenType.END, "`END` (closing this REPEAT UNTIL)", help_topic="loops")
            return ast.RepeatUntilStatement(condition=condition, body=body, line=tok.line, column=tok.column)

        count = self._expression()
        self._expect(TokenType.TIMES, "`TIMES`", help_topic="loops")
        body = self._block({TokenType.END})
        self._expect(TokenType.END, "`END` (closing this REPEAT)", help_topic="loops")
        return ast.RepeatTimesStatement(count=count, body=body, line=tok.line, column=tok.column)

    def _increase_decrease(self, op: str) -> ast.Node:
        tok = self._advance()  # INCREASE / DECREASE
        name_tok = self._expect(TokenType.IDENTIFIER, "a variable name", help_topic="operators")
        self._expect(TokenType.BY, "`BY`", help_topic="operators")
        amount = self._expression()
        node = ast.CompoundAssignment(name=name_tok.value, operator=op, value=amount,
                                       line=tok.line, column=tok.column)
        self._end_statement()
        return node

    # ---- Phase 2 ("POWER"): functions ----

    def _function_declaration(self) -> ast.Node:
        tok = self._advance()  # FUNCTION
        name_tok = self._expect(TokenType.IDENTIFIER, "a function name", help_topic="functions")
        self._expect(TokenType.LPAREN, "`(`", help_topic="functions")
        params: List[ast.Param] = []
        if not self._check(TokenType.RPAREN):
            params.append(self._parameter())
            while self._match(TokenType.COMMA):
                params.append(self._parameter())
        self._expect(TokenType.RPAREN, "`)`", help_topic="functions")
        returns = None
        if self._check(TokenType.RETURNS):
            self._advance()
            returns = self._type_annotation()
        self._end_statement()
        body = self._block({TokenType.END})
        self._expect(TokenType.END, "`END` (closing this FUNCTION)", help_topic="functions")
        return ast.FunctionDeclaration(name=name_tok.value, params=params, body=body,
                                        line=tok.line, column=tok.column, returns=returns)

    def _parameter(self) -> ast.Param:
        name_tok = self._expect(TokenType.IDENTIFIER, "a parameter name", help_topic="functions")
        annotation = None
        if self._check(TokenType.AS):
            self._advance()
            annotation = self._type_annotation()
        default = None
        if self._match(TokenType.EQ):
            default = self._expression()
        return ast.Param(name=name_tok.value, default=default, annotation=annotation)

    def _return_statement(self) -> ast.Node:
        tok = self._advance()  # RETURN
        value = None
        if not self._check(TokenType.NEWLINE, TokenType.EOF):
            value = self._expression()
        node = ast.ReturnStatement(value=value, line=tok.line, column=tok.column)
        self._end_statement()
        return node

    # ---- Phase 2: collections ----

    def _add_to_statement(self) -> ast.Node:
        tok = self._advance()  # ADD
        value = self._expression()
        self._expect(TokenType.TO, "`TO`", help_topic="collections")
        target_tok = self._expect(TokenType.IDENTIFIER, "a list variable", help_topic="collections")
        node = ast.AddToStatement(value=value, target=target_tok.value, line=tok.line, column=tok.column)
        self._end_statement()
        return node

    def _remove_from_statement(self) -> ast.Node:
        tok = self._advance()  # REMOVE
        value = self._expression()
        self._expect(TokenType.FROM, "`FROM`", help_topic="collections")
        target_tok = self._expect(TokenType.IDENTIFIER, "a list variable", help_topic="collections")
        node = ast.RemoveFromStatement(value=value, target=target_tok.value, line=tok.line, column=tok.column)
        self._end_statement()
        return node

    # ---- Phase 2: control flow ----

    def _for_statement(self) -> ast.Node:
        tok = self._advance()  # FOR
        if self._match(TokenType.EACH):
            var_tok = self._expect(TokenType.IDENTIFIER, "a loop variable name", help_topic="loops")
            if self._match(TokenType.COMMA):
                value_tok = self._expect(TokenType.IDENTIFIER, "a second loop variable name (for the value)",
                                          help_topic="loops")
                self._expect(TokenType.IN, "`IN`", help_topic="loops")
                iterable = self._expression()
                body = self._block({TokenType.END})
                self._expect(TokenType.END, "`END` (closing this FOR EACH)", help_topic="loops")
                return ast.ForEachPairStatement(key_name=var_tok.value, value_name=value_tok.value,
                                                 iterable=iterable, body=body, line=tok.line, column=tok.column)
            self._expect(TokenType.IN, "`IN`", help_topic="loops")
            iterable = self._expression()
            body = self._block({TokenType.END})
            self._expect(TokenType.END, "`END` (closing this FOR EACH)", help_topic="loops")
            return ast.ForEachStatement(var_name=var_tok.value, iterable=iterable, body=body,
                                         line=tok.line, column=tok.column)

        var_tok = self._expect(TokenType.IDENTIFIER, "a loop variable name", help_topic="loops")
        self._expect(TokenType.FROM, "`FROM`", help_topic="loops")
        start = self._expression()
        descending = bool(self._match(TokenType.DOWN))
        self._expect(TokenType.TO, "`TO`", help_topic="loops")
        end = self._expression()
        body = self._block({TokenType.END})
        self._expect(TokenType.END, "`END` (closing this FOR)", help_topic="loops")
        return ast.ForRangeStatement(var_name=var_tok.value, start=start, end=end,
                                      descending=descending, body=body, line=tok.line, column=tok.column)

    # ---- Phase 2: error handling ----

    def _try_statement(self) -> ast.Node:
        tok = self._advance()  # TRY
        self._end_statement()
        try_body = self._block({TokenType.CATCH, TokenType.FINALLY, TokenType.END})

        catch_var = None
        catch_body = None
        if self._match(TokenType.CATCH):
            if self._check(TokenType.IDENTIFIER):
                catch_var = self._advance().value
            self._end_statement()
            catch_body = self._block({TokenType.FINALLY, TokenType.END})

        finally_body = None
        if self._match(TokenType.FINALLY):
            self._end_statement()
            finally_body = self._block({TokenType.END})

        if catch_body is None and finally_body is None:
            raise self._error(
                "NX213", "TRY needs CATCH or FINALLY",
                "A `TRY` block must be followed by `CATCH` and/or `FINALLY` - "
                "otherwise there is nothing for it to do.",
                token=tok,
                suggestions=["TRY\n    ...\nCATCH error\n    SAY error\nEND"],
                help_topic="errors",
            )

        self._expect(TokenType.END, "`END` (closing this TRY)", help_topic="errors")
        return ast.TryStatement(try_body=try_body, catch_var=catch_var, catch_body=catch_body,
                                 finally_body=finally_body, line=tok.line, column=tok.column)

    # ---- Phase 2: modules ----

    def _import_statement(self) -> ast.Node:
        tok = self._advance()  # IMPORT
        path = self._expression()
        node = ast.ImportStatement(path=path, line=tok.line, column=tok.column)
        self._end_statement()
        return node

    # ---- Phase 2: filesystem ----

    def _write_file_statement(self, append: bool) -> ast.Node:
        tok = self._advance()  # WRITE / APPEND
        value = self._expression()
        self._expect(TokenType.TO, "`TO`", help_topic="files")
        self._expect(TokenType.FILE, "`FILE`", help_topic="files")
        path = self._expression()
        node = ast.WriteFileStatement(value=value, path=path, append=append, line=tok.line, column=tok.column)
        self._end_statement()
        return node

    def _delete_file_statement(self) -> ast.Node:
        tok = self._advance()  # DELETE
        self._expect(TokenType.FILE, "`FILE`", help_topic="files")
        path = self._expression()
        node = ast.DeleteFileStatement(path=path, line=tok.line, column=tok.column)
        self._end_statement()
        return node

    def _identifier_led_statement(self) -> ast.Node:
        """An identifier at the start of a statement is either:
        - a concise assignment:      x = expr
        - a compound assignment:     x += expr (etc.)
        - or just an expression statement (e.g. a bare function call, future phase)
        """
        start_tok = self._peek()
        name = start_tok.value

        # Look ahead without consuming, to decide which production applies.
        nxt = self._peek(1)
        compound_ops = {
            TokenType.PLUS_EQ: "+", TokenType.MINUS_EQ: "-", TokenType.STAR_EQ: "*",
            TokenType.SLASH_EQ: "/", TokenType.DOUBLE_SLASH_EQ: "//", TokenType.PERCENT_EQ: "%",
        }
        if nxt.type == TokenType.EQ:
            self._advance()  # identifier
            self._advance()  # '='
            value = self._expression()
            node = ast.Assignment(name=name, value=value, line=start_tok.line, column=start_tok.column)
            self._end_statement()
            return node
        if nxt.type in compound_ops:
            self._advance()
            op_tok = self._advance()
            value = self._expression()
            node = ast.CompoundAssignment(name=name, operator=compound_ops[op_tok.type],
                                           value=value, line=start_tok.line, column=start_tok.column)
            self._end_statement()
            return node

        expr = self._expression()
        node = ast.ExpressionStatement(expression=expr, line=start_tok.line, column=start_tok.column)
        self._end_statement()
        return node

    # ---- expressions (precedence climbing) ----

    def _expression(self) -> ast.Node:
        return self._or_expr()

    def _or_expr(self) -> ast.Node:
        left = self._and_expr()
        while self._check(TokenType.OR):
            tok = self._advance()
            right = self._and_expr()
            left = ast.LogicalExpression(operator="OR", left=left, right=right, line=tok.line, column=tok.column)
        return left

    def _and_expr(self) -> ast.Node:
        left = self._not_expr()
        while self._check(TokenType.AND):
            tok = self._advance()
            right = self._not_expr()
            left = ast.LogicalExpression(operator="AND", left=left, right=right, line=tok.line, column=tok.column)
        return left

    def _not_expr(self) -> ast.Node:
        if self._check(TokenType.NOT):
            tok = self._advance()
            operand = self._not_expr()
            return ast.UnaryExpression(operator="NOT", operand=operand, line=tok.line, column=tok.column)
        return self._comparison()

    def _comparison(self) -> ast.Node:
        left = self._additive()

        # readable comparison phrases: IS [NOT] / IS AT LEAST / IS AT MOST / IS ABOVE / IS BELOW
        if self._check(TokenType.IS):
            tok = self._advance()
            if self._match(TokenType.EMPTY):
                return ast.UnaryExpression(operator="IS_EMPTY", operand=left, line=tok.line, column=tok.column)
            if self._match(TokenType.BETWEEN):
                low = self._additive()
                self._expect(TokenType.AND, "`AND`", help_topic="operators")
                high = self._additive()
                # Desugared to (left >= low) AND (left <= high) rather than a
                # dedicated AST node - NexLang's own readable phrase, but no
                # new evaluation semantics beyond >= / <= are needed for it.
                lower = ast.BinaryExpression(operator=">=", left=left, right=low, line=tok.line, column=tok.column)
                upper = ast.BinaryExpression(operator="<=", left=left, right=high, line=tok.line, column=tok.column)
                return ast.LogicalExpression(operator="AND", left=lower, right=upper, line=tok.line, column=tok.column)
            if self._match(TokenType.NOT):
                right = self._additive()
                return ast.BinaryExpression(operator="!=", left=left, right=right, line=tok.line, column=tok.column)
            if self._match(TokenType.AT):
                if self._match(TokenType.LEAST):
                    right = self._additive()
                    return ast.BinaryExpression(operator=">=", left=left, right=right, line=tok.line, column=tok.column)
                if self._match(TokenType.MOST):
                    right = self._additive()
                    return ast.BinaryExpression(operator="<=", left=left, right=right, line=tok.line, column=tok.column)
                raise self._error(
                    "NX206", "Incomplete comparison",
                    "`IS AT` must be followed by `LEAST` or `MOST`.",
                    token=self._peek(),
                    suggestions=["x IS AT LEAST 10", "x IS AT MOST 10"],
                    help_topic="operators",
                )
            if self._match(TokenType.ABOVE):
                right = self._additive()
                return ast.BinaryExpression(operator=">", left=left, right=right, line=tok.line, column=tok.column)
            if self._match(TokenType.BELOW):
                right = self._additive()
                return ast.BinaryExpression(operator="<", left=left, right=right, line=tok.line, column=tok.column)
            right = self._additive()
            return ast.BinaryExpression(operator="==", left=left, right=right, line=tok.line, column=tok.column)

        if self._check(TokenType.CONTAINS):
            tok = self._advance()
            right = self._additive()
            return ast.BinaryExpression(operator="CONTAINS", left=left, right=right, line=tok.line, column=tok.column)
        if self._check(TokenType.STARTS):
            tok = self._advance()
            self._expect(TokenType.WITH, "`WITH` (as part of `STARTS WITH`)", help_topic="operators")
            right = self._additive()
            return ast.BinaryExpression(operator="STARTS_WITH", left=left, right=right, line=tok.line, column=tok.column)
        if self._check(TokenType.ENDS):
            tok = self._advance()
            self._expect(TokenType.WITH, "`WITH` (as part of `ENDS WITH`)", help_topic="operators")
            right = self._additive()
            return ast.BinaryExpression(operator="ENDS_WITH", left=left, right=right, line=tok.line, column=tok.column)
        if self._check(TokenType.EXISTS):
            tok = self._advance()
            return ast.UnaryExpression(operator="EXISTS", operand=left, line=tok.line, column=tok.column)

        symbolic = {
            TokenType.EQEQ: "==", TokenType.NEQ: "!=", TokenType.LT: "<",
            TokenType.GT: ">", TokenType.LE: "<=", TokenType.GE: ">=",
        }
        if self._peek().type in symbolic:
            tok = self._advance()
            right = self._additive()
            return ast.BinaryExpression(operator=symbolic[tok.type], left=left, right=right,
                                         line=tok.line, column=tok.column)
        return left

    def _additive(self) -> ast.Node:
        left = self._multiplicative()
        while self._peek().type in (TokenType.PLUS, TokenType.MINUS):
            tok = self._advance()
            right = self._multiplicative()
            op = "+" if tok.type == TokenType.PLUS else "-"
            left = ast.BinaryExpression(operator=op, left=left, right=right, line=tok.line, column=tok.column)
        return left

    def _multiplicative(self) -> ast.Node:
        left = self._unary()
        ops = {TokenType.STAR: "*", TokenType.SLASH: "/", TokenType.DOUBLE_SLASH: "//", TokenType.PERCENT: "%"}
        while self._peek().type in ops:
            tok = self._advance()
            right = self._unary()
            left = ast.BinaryExpression(operator=ops[tok.type], left=left, right=right, line=tok.line, column=tok.column)
        return left

    def _unary(self) -> ast.Node:
        if self._check(TokenType.MINUS):
            tok = self._advance()
            operand = self._unary()
            return ast.UnaryExpression(operator="-", operand=operand, line=tok.line, column=tok.column)
        if self._check(TokenType.SIZE):
            tok = self._advance()
            self._expect(TokenType.OF, "`OF` (as part of `SIZE OF`)", help_topic="operators")
            operand = self._unary()
            return ast.UnaryExpression(operator="SIZE_OF", operand=operand, line=tok.line, column=tok.column)
        return self._power()

    def _power(self) -> ast.Node:
        left = self._primary()
        if self._check(TokenType.DOUBLE_STAR):
            tok = self._advance()
            right = self._unary()  # right-associative
            return ast.BinaryExpression(operator="**", left=left, right=right, line=tok.line, column=tok.column)
        return left

    def _primary(self) -> ast.Node:
        """Postfix layer: function calls `name(args)` and indexing `expr[i]`,
        which may chain (e.g. `matrix[0][1]`, `make_list()[0]`)."""
        node = self._atom()
        while True:
            if self._check(TokenType.LPAREN) and isinstance(node, ast.Identifier):
                node = self._finish_call(node)
            elif self._check(TokenType.LBRACKET):
                tok = self._advance()
                if self._check(TokenType.COLON):
                    self._advance()
                    end = None if self._check(TokenType.RBRACKET) else self._expression()
                    self._expect(TokenType.RBRACKET, "`]`", help_topic="collections")
                    node = ast.SliceExpression(collection=node, start=None, end=end, line=tok.line, column=tok.column)
                else:
                    first = self._expression()
                    if self._match(TokenType.COLON):
                        end = None if self._check(TokenType.RBRACKET) else self._expression()
                        self._expect(TokenType.RBRACKET, "`]`", help_topic="collections")
                        node = ast.SliceExpression(collection=node, start=first, end=end, line=tok.line, column=tok.column)
                    else:
                        self._expect(TokenType.RBRACKET, "`]`", help_topic="collections")
                        node = ast.IndexExpression(collection=node, index=first, line=tok.line, column=tok.column)
            else:
                break
        return node

    def _finish_call(self, callee: ast.Identifier) -> ast.Node:
        self._advance()  # '('
        args: List[ast.Node] = []
        if not self._check(TokenType.RPAREN):
            args.append(self._expression())
            while self._match(TokenType.COMMA):
                args.append(self._expression())
        self._expect(TokenType.RPAREN, "`)`", help_topic="functions")
        return ast.Call(name=callee.name, args=args, line=callee.line, column=callee.column)

    def _map_entry(self):
        key = self._expression()
        self._expect(TokenType.COLON, "`:` (between a map key and its value)", help_topic="collections")
        value = self._expression()
        return key, value

    def _atom(self) -> ast.Node:
        tok = self._peek()

        if tok.type == TokenType.NUMBER:
            self._advance()
            return ast.Literal(value=tok.value, line=tok.line, column=tok.column)
        if tok.type == TokenType.STRING:
            self._advance()
            if "{" in tok.value and "}" in tok.value:
                return ast.InterpolatedString(raw=tok.value, line=tok.line, column=tok.column)
            return ast.Literal(value=tok.value, line=tok.line, column=tok.column)
        if tok.type == TokenType.TRUE:
            self._advance()
            return ast.Literal(value=True, line=tok.line, column=tok.column)
        if tok.type == TokenType.FALSE:
            self._advance()
            return ast.Literal(value=False, line=tok.line, column=tok.column)
        if tok.type == TokenType.NOTHING:
            self._advance()
            return ast.Literal(value=None, line=tok.line, column=tok.column)
        if tok.type == TokenType.LBRACKET:
            self._advance()
            elements: List[ast.Node] = []
            self._skip_newlines()
            if not self._check(TokenType.RBRACKET):
                elements.append(self._expression())
                self._skip_newlines()
                while self._match(TokenType.COMMA):
                    self._skip_newlines()
                    elements.append(self._expression())
                    self._skip_newlines()
            self._expect(TokenType.RBRACKET, "`]` (closing this list)", help_topic="collections")
            return ast.ListLiteral(elements=elements, line=tok.line, column=tok.column)
        if tok.type == TokenType.LBRACE:
            self._advance()
            keys: List[ast.Node] = []
            values: List[ast.Node] = []
            self._skip_newlines()
            if not self._check(TokenType.RBRACE):
                k, v = self._map_entry()
                keys.append(k)
                values.append(v)
                self._skip_newlines()
                while self._match(TokenType.COMMA):
                    self._skip_newlines()
                    if self._check(TokenType.RBRACE):
                        break  # allow a trailing comma before `}`
                    k, v = self._map_entry()
                    keys.append(k)
                    values.append(v)
                    self._skip_newlines()
            self._expect(TokenType.RBRACE, "`}` (closing this map)", help_topic="collections")
            return ast.MapLiteral(keys=keys, values=values, line=tok.line, column=tok.column)
        if tok.type == TokenType.FILE:
            self._advance()
            path = self._additive()
            return ast.FileRef(path=path, line=tok.line, column=tok.column)
        if tok.type == TokenType.READ:
            self._advance()
            self._expect(TokenType.FILE, "`FILE` (as part of `READ FILE`)", help_topic="files")
            path = self._additive()
            return ast.ReadFileExpression(path=path, line=tok.line, column=tok.column)
        if tok.type == TokenType.IDENTIFIER:
            self._advance()
            return ast.Identifier(name=tok.value, line=tok.line, column=tok.column)
        if tok.type == TokenType.LPAREN:
            self._advance()
            expr = self._expression()
            self._expect(TokenType.RPAREN, "`)`", help_topic="syntax")
            return ast.Grouping(expression=expr, line=tok.line, column=tok.column)

        raise self._error(
            "NX207",
            "Expected an expression",
            f"Expected a value, variable, or `(` here but found "
            f"`{tok.lexeme or tok.value or tok.type.name}` instead.",
            token=tok,
            help_topic="syntax",
        )


def parse(source: str, filename: str = "<string>"):
    from compiler.lexer.lexer import tokenize
    tokens = tokenize(source, filename)
    return Parser(tokens, source, filename).parse_program()
