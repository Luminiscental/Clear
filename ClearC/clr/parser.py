"""
Contains functions and definitions for parsing a list of tokens into a parse tree.
"""

from typing import List, Optional, Union, Tuple, Callable, DefaultDict

import enum
import collections

import clr.lexer as lexer


class Parser:
    """
    A wrapper class for parsing a list of tokens.
    """

    def __init__(self, tokens: List[lexer.Token]) -> None:
        self.tokens = tokens
        self.current = 0

    def done(self) -> bool:
        """
        Returns whether the whole token list has been consumed.
        """
        return self.current == len(self.tokens)

    def prev(self) -> lexer.Token:
        """
        Returns the previous token.
        """
        return self.tokens[self.current - 1]

    def curr(self) -> Optional[lexer.Token]:
        """
        Returns the current token, or None if there are no more tokens to parse.
        """
        return None if self.done() else self.tokens[self.current]

    def backtrack(self) -> None:
        """
        Moves back to the previous token if there is one.
        """
        if self.current > 0:
            self.current -= 1

    def advance(self) -> Optional[lexer.Token]:
        """
        Consumes a token and returns it, if there are no tokens left returns None.
        """
        if self.done():
            return None

        self.current += 1
        return self.prev()

    def check(self, kind: lexer.TokenType) -> bool:
        """
        Checks if the current token is of a given type.
        """
        curr = self.curr()
        if curr:
            return curr.kind == kind
        return False

    def match(self, kind: lexer.TokenType) -> bool:
        """
        Checks if the current token is of a given type, and advances past it if it is.
        """
        result = self.check(kind)
        if result:
            self.current += 1
        return result

    def curr_region(self) -> lexer.SourceView:
        """
        Returns a source view of the current token (or the previous if the parser is done).
        """
        curr = self.curr()
        if curr:
            return curr.lexeme
        return self.prev().lexeme


class ParseError:
    """
    Parse error class, contains a message and a region of source the error applies to.
    """

    def __init__(self, message: str, region: lexer.SourceView) -> None:
        self.message = message
        self.region = region
        print(f"[error] {self.display()}")

    def display(self) -> str:
        """
        Returns a string of information about the error.
        """
        # TODO: Line number, highlight region in context, formatting, e.t.c.
        return f"{self.message}: {self.region}"


class ParseTree:
    """
    The root node of the parse tree, contains a list of declarations.

    ParseTree : ParseDecl* ;
    """

    def __init__(self, decls: List["ParseDecl"]) -> None:
        self.decls = decls

    @staticmethod
    def parse(parser: Parser) -> "ParseTree":
        """
        Parses a ParseTree from a Parser.
        """
        decls = []
        while not parser.done():
            decls.append(ParseDecl.parse(parser))
        return ParseTree(decls)


def parse_tokens(tokens: List[lexer.Token]) -> ParseTree:
    """
    Parses a ParseTree from a list of tokens.
    """
    return ParseTree.parse(Parser(tokens))


class ParseDecl:
    """
    Parse node for a generic declaration.

    ParseDecl : ParseValueDecl | ParseFuncDecl | ParseStmt ;
    """

    def __init__(
        self, decl: Union["ParseValueDecl", "ParseFuncDecl", "ParseStmt"]
    ) -> None:
        self.decl = decl

    @staticmethod
    def parse(parser: Parser) -> "ParseDecl":
        """
        Parses a ParseDecl from a Parser.
        """
        if parser.match(lexer.TokenType.VAL):
            return ParseDecl(ParseValueDecl.finish(parser))
        if parser.match(lexer.TokenType.FUNC):
            return ParseDecl(ParseFuncDecl.finish(parser))
        return ParseDecl(ParseStmt.parse(parser))


class ParseValueDecl:
    """
    Parse node for a value declaration.

    ParseValueDecl : "val" identifier (ParseType)? "=" ParseExpr ";" ;
    """

    def __init__(
        self,
        ident: Union[lexer.Token, ParseError],
        val_type: Optional["ParseType"],
        expr: Union["ParseExpr", ParseError],
        errors: List[ParseError],
    ):
        self.errors = errors
        self.ident = ident
        self.val_type = val_type
        self.expr = expr

    @staticmethod
    def finish(parser: Parser) -> "ParseValueDecl":
        """
        Parses a ParseValueDecl from a Parser, given that the "val" keyword has already been
        consumed.
        """
        errors = []

        if parser.match(lexer.TokenType.IDENTIFIER):
            ident: Union[lexer.Token, ParseError] = parser.prev()
        else:
            ident = ParseError("missing value name", parser.curr_region())
            errors.append(ident)

        val_type = None
        if not parser.match(lexer.TokenType.EQUALS):
            val_type = ParseType.parse(parser)
            if not parser.match(lexer.TokenType.EQUALS):
                errors.append(
                    ParseError(
                        "missing '=' for value initializer", parser.curr_region()
                    )
                )

        expr = pratt_parse(parser, PRATT_TABLE)
        if isinstance(expr, ParseError):
            errors.append(expr)

        if not parser.match(lexer.TokenType.SEMICOLON):
            errors.append(
                ParseError("missing ';' to end value initializer", parser.curr_region())
            )

        return ParseValueDecl(ident, val_type, expr, errors)


class ParseFuncDecl:
    """
    Parse node for a function declaration.

    ParseFuncDecl : "func" identifier ParseParams ParseType ParseBlockStmt ;
    """

    def __init__(
        self,
        ident: Union[lexer.Token, ParseError],
        params: "ParseParams",
        return_type: "ParseType",
        block: "ParseBlockStmt",
        errors: List[ParseError],
    ) -> None:
        self.errors = errors
        self.ident = ident
        self.params = params
        self.return_type = return_type
        self.block = block

    @staticmethod
    def finish(parser: Parser) -> "ParseFuncDecl":
        """
        Parses a ParseFuncDecl from a Parser, given that the "func" keyword has already been
        consumed.
        """
        errors = []
        if parser.match(lexer.TokenType.IDENTIFIER):
            ident: Union[lexer.Token, ParseError] = parser.prev()
        else:
            ident = ParseError("missing function name", parser.curr_region())
            errors.append(ident)
        params = ParseParams.parse(parser)
        return_type = ParseType.parse(parser)
        block = ParseBlockStmt.parse(parser)
        return ParseFuncDecl(ident, params, return_type, block, errors)


class ParseParams:
    """
    Parse node for a parameter list.

    ParseParams : "(" ( ParseType identifier ( "," ParseType identifier )* )? ")" ;
    """

    def __init__(
        self,
        pairs: List[Tuple["ParseType", Union[lexer.Token, ParseError]]],
        errors: List[ParseError],
    ):
        self.errors = errors
        self.pairs = pairs

    @staticmethod
    def parse(parser: Parser) -> "ParseParams":
        """
        Parses a ParseParams from a Parser.
        """
        errors = []
        pairs: List[Tuple["ParseType", Union[lexer.Token, ParseError]]] = []

        if not parser.match(lexer.TokenType.LEFT_PAREN):
            errors.append(
                ParseError("missing '(' to start parameter list", parser.curr_region())
            )

        opener = parser.prev()

        if parser.match(lexer.TokenType.RIGHT_PAREN):
            return ParseParams(pairs, errors)

        def parse_pair() -> None:
            param_type = ParseType.parse(parser)
            if parser.match(lexer.TokenType.IDENTIFIER):
                param_ident: Union[lexer.Token, ParseError] = parser.prev()
            else:
                param_ident = ParseError("missing parameter name", parser.curr_region())
                errors.append(param_ident)
            pairs.append((param_type, param_ident))

        parse_pair()
        while not parser.match(lexer.TokenType.RIGHT_PAREN):
            before = parser.current
            if parser.done():
                errors.append(
                    ParseError("missing ')' to finish parameters", opener.lexeme)
                )
                break
            if not parser.match(lexer.TokenType.COMMA):
                errors.append(
                    ParseError(
                        "missing ',' to delimit parameters", parser.curr_region()
                    )
                )
            parse_pair()
            if parser.current == before:
                break

        return ParseParams(pairs, errors)


class ParseStmt:
    """
    Parse node for a generic statement.

    ParseStmt : ParsePrintStmt
              | ParseBlockStmt
              | ParseIfStmt
              | ParseWhileStmt
              | ParseReturnStmt
              | ParseExprStmt
              ;
    """

    def __init__(
        self,
        stmt: Union[
            "ParsePrintStmt",
            "ParseBlockStmt",
            "ParseIfStmt",
            "ParseWhileStmt",
            "ParseReturnStmt",
            "ParseExprStmt",
        ],
    ) -> None:
        self.stmt = stmt

    @staticmethod
    def parse(parser: Parser) -> "ParseStmt":
        """
        Parses a ParseStmt from a Parser.
        """
        if parser.match(lexer.TokenType.PRINT):
            return ParseStmt(ParsePrintStmt.finish(parser))
        if parser.match(lexer.TokenType.LEFT_BRACE):
            return ParseStmt(ParseBlockStmt.parse(parser))
        if parser.match(lexer.TokenType.IF):
            return ParseStmt(ParseIfStmt.finish(parser))
        if parser.match(lexer.TokenType.WHILE):
            return ParseStmt(ParseWhileStmt.finish(parser))
        if parser.match(lexer.TokenType.RETURN):
            return ParseStmt(ParseReturnStmt.finish(parser))
        return ParseStmt(ParseExprStmt.parse(parser))


class ParsePrintStmt:
    """
    Parse node for a print statement.

    ParsePrintStmt : "print" ParseExpr ";" ;
    """

    def __init__(
        self, expr: Union["ParseExpr", ParseError], errors: List[ParseError]
    ) -> None:
        self.errors = errors
        self.expr = expr

    @staticmethod
    def finish(parser: Parser) -> "ParsePrintStmt":
        """
        Parses a ParsePrintStmt from a Parser, given that the "print" keyword has already been
        consumed.
        """
        errors = []
        expr = pratt_parse(parser, PRATT_TABLE)
        if isinstance(expr, ParseError):
            errors.append(expr)
        if not parser.match(lexer.TokenType.SEMICOLON):
            errors.append(
                ParseError("missing ';' to end print statement", parser.curr_region())
            )
        return ParsePrintStmt(expr, errors)


class ParseBlockStmt:
    """
    Parse node for a block statement.

    ParseBlockStmt : "{" ParseDecl* "}" ;
    """

    def __init__(self, decls: List[ParseDecl], errors: List[ParseError]) -> None:
        self.errors = errors
        self.decls = decls

    @staticmethod
    def parse(parser: Parser) -> "ParseBlockStmt":
        """
        Parses a ParseBlockStmt from a Parser.
        """
        if parser.match(lexer.TokenType.LEFT_BRACE):
            return ParseBlockStmt.finish(parser)

        return ParseBlockStmt(
            decls=[],
            errors=[ParseError("expected '{' to start block", parser.curr_region())],
        )

    @staticmethod
    def finish(parser: Parser) -> "ParseBlockStmt":
        """
        Parses a ParseBlockStmt from a Parser, given that the open brace has already been consumed.
        """
        errors = []
        decls = []
        open_brace = parser.prev()
        while not parser.match(lexer.TokenType.RIGHT_BRACE):
            if parser.done():
                errors.append(ParseError("unclosed block", open_brace.lexeme))
                break
            decls.append(ParseDecl.parse(parser))
        return ParseBlockStmt(decls, errors)


class ParseIfStmt:
    """
    Parse node for an if statement.

    ParseIfStmt : "if" "(" ParseExpr ")" ParseBlockStmt
                ( "else" "if" "(" ParseExpr ")" ParseBlockStmt )*
                ( "else" ParseBlockStmt )?
                ;
    """

    def __init__(
        self,
        pairs: List[Tuple[Union["ParseExpr", ParseError], ParseBlockStmt]],
        fallback: Optional[ParseBlockStmt],
        errors: List[ParseError],
    ) -> None:
        self.errors = errors
        self.pairs = pairs
        self.fallback = fallback

    @staticmethod
    def finish(parser: Parser) -> "ParseIfStmt":
        """
        Parses a ParseIfStmt from a Parser, given that the "if" keyword has already been consumed.
        """
        errors = []
        pairs = []
        fallback = None

        def parse_cond() -> None:
            if not parser.match(lexer.TokenType.LEFT_PAREN):
                errors.append(
                    ParseError("missing '(' to start condition", parser.curr_region())
                )
            cond = pratt_parse(parser, PRATT_TABLE)
            if isinstance(cond, ParseError):
                errors.append(cond)
            if not parser.match(lexer.TokenType.RIGHT_PAREN):
                errors.append(
                    ParseError("missing ')' to end condition", parser.curr_region())
                )
            block = ParseBlockStmt.parse(parser)
            pairs.append((cond, block))

        # parse the if block
        parse_cond()
        while parser.match(lexer.TokenType.ELSE):
            if parser.match(lexer.TokenType.IF):
                # parse an else if block
                parse_cond()
            else:
                # parse the else block
                fallback = ParseBlockStmt.parse(parser)
                break
        return ParseIfStmt(pairs, fallback, errors)


class ParseWhileStmt:
    """
    Parse node for a while statement.

    ParseWhileStmt : "while" ( "(" ParseExpr ")" )? ParseBlockStmt ;
    """

    def __init__(
        self,
        cond: Optional[Union["ParseExpr", ParseError]],
        block: ParseBlockStmt,
        errors: List[ParseError],
    ) -> None:
        self.errors = errors
        self.cond = cond
        self.block = block

    @staticmethod
    def finish(parser: Parser) -> "ParseWhileStmt":
        """
        Parses a ParseWhileStmt from a Parser, given that the "while" keyword has already been
        consumed.
        """
        errors = []
        cond = None
        if parser.match(lexer.TokenType.LEFT_PAREN):
            cond = pratt_parse(parser, PRATT_TABLE)
            if isinstance(cond, ParseError):
                errors.append(cond)
            if not parser.match(lexer.TokenType.RIGHT_PAREN):
                errors.append(
                    ParseError("missing ')' to end condition", parser.curr_region())
                )
        block = ParseBlockStmt.parse(parser)
        return ParseWhileStmt(cond, block, errors)


class ParseReturnStmt:
    """
    Parse node for a return statement.

    ParseReturnStmt : "return" ParseExpr? ";" ;
    """

    def __init__(
        self, expr: Optional[Union["ParseExpr", ParseError]], errors: List[ParseError]
    ) -> None:
        self.errors = errors
        self.expr = expr

    @staticmethod
    def finish(parser: Parser) -> "ParseReturnStmt":
        """
        Parses a ParseReturnStmt from a Parser, given that the "return" keyword has already been
        consumed.
        """
        errors = []
        expr = None
        if not parser.match(lexer.TokenType.SEMICOLON):
            expr = pratt_parse(parser, PRATT_TABLE)
            if isinstance(expr, ParseError):
                errors.append(expr)
            if not parser.match(lexer.TokenType.SEMICOLON):
                errors.append(
                    ParseError(
                        "missing ';' to end return statement", parser.curr_region()
                    )
                )
        return ParseReturnStmt(expr, errors)


class ParseExprStmt:
    """
    Parse node for an expression statement.

    ParseExprStmt : ParseExpr ";" ;
    """

    def __init__(
        self, expr: Union["ParseExpr", ParseError], errors: List[ParseError]
    ) -> None:
        self.errors = errors
        self.expr = expr

    @staticmethod
    def parse(parser: Parser) -> "ParseExprStmt":
        """
        Parses a ParseExprStmt from a Parser.
        """
        errors = []
        expr = pratt_parse(parser, PRATT_TABLE)
        if isinstance(expr, ParseError):
            errors.append(expr)
        if not parser.match(lexer.TokenType.SEMICOLON):
            errors.append(
                ParseError(
                    "missing ';' to end expression statement", parser.curr_region()
                )
            )
        return ParseExprStmt(expr, errors)


class ParseType:
    """
    Parse node for a type.

    ParseType : ( "(" ParseType ")" | ParseFuncType | ParseAtomType ) ( "?" )? ;
    """

    def __init__(self, type_node: Union["ParseFuncType", "ParseAtomType"]) -> None:
        self.type_node = type_node
        self.optional = False
        self.errors: List[ParseError] = []

    @staticmethod
    def parse(parser: Parser) -> "ParseType":
        """
        Parse a ParseType from a Parser.
        """
        if parser.match(lexer.TokenType.LEFT_PAREN):
            result = ParseType.parse(parser)
            if not parser.match(lexer.TokenType.RIGHT_PAREN):
                result.errors.append(
                    ParseError("missing ')' to end type grouping", parser.curr_region())
                )
        elif parser.match(lexer.TokenType.FUNC):
            result = ParseType(ParseFuncType.finish(parser))
        else:
            result = ParseType(ParseAtomType.parse(parser))

        if parser.match(lexer.TokenType.QUESTION_MARK):
            result.optional = True

        return result


class ParseFuncType:
    """
    Parse node for a function type.

    ParseFuncType : "func" "(" ( ParseType ( "," ParseType )* )? ")" ParseType ;
    """

    def __init__(
        self, params: List[ParseType], return_type: ParseType, errors: List[ParseError]
    ) -> None:
        self.params = params
        self.return_type = return_type
        self.errors = errors

    @staticmethod
    def finish(parser: Parser) -> "ParseFuncType":
        """
        Parse a ParseFuncType from a Parser given that the "func" keyword has already been
        consumed.
        """
        errors = []
        params: List[ParseType] = []

        if not parser.match(lexer.TokenType.LEFT_PAREN):
            errors.append(
                ParseError("missing '(' to begin parameter types", parser.curr_region())
            )

        opener = parser.prev()

        if not parser.match(lexer.TokenType.RIGHT_PAREN):

            def parse_param() -> None:
                param_type = ParseType.parse(parser)
                params.append(param_type)

            parse_param()
            while not parser.match(lexer.TokenType.RIGHT_PAREN):
                before = parser.current
                if parser.done():
                    errors.append(
                        ParseError("missing ')' for parameter types", opener.lexeme)
                    )
                    break
                if not parser.match(lexer.TokenType.COMMA):
                    errors.append(
                        ParseError(
                            "missing ',' to delimit parameter types",
                            parser.curr_region(),
                        )
                    )
                parse_param()
                if parser.current == before:
                    break

        return_type = ParseType.parse(parser)
        return ParseFuncType(params, return_type, errors)


class ParseAtomType:
    """
    Parse node for an atomic type.

    ParseAtomType : identifier | "void" ;
    """

    def __init__(
        self, ident: Union[lexer.Token, ParseError], errors: List[ParseError]
    ) -> None:
        self.ident = ident
        self.errors = errors

    @staticmethod
    def parse(parser: Parser) -> "ParseAtomType":
        """
        Parse a ParseAtomType from a Parser.
        """
        errors = []
        if parser.match(lexer.TokenType.IDENTIFIER):
            ident: Union[lexer.Token, ParseError] = parser.prev()
        elif parser.match(lexer.TokenType.VOID):
            ident = parser.prev()
        else:
            ident = ParseError("expected type", parser.curr_region())
            errors.append(ident)
        return ParseAtomType(ident, errors)


ParseExpr = Union["ParseUnaryExpr", "ParseBinaryExpr", "ParseAtomExpr"]


class ParseUnaryExpr:
    """
    Prefix expression for a unary operator.
    """

    def __init__(self, parser: Parser) -> None:
        self.operator = parser.prev()
        self.target = pratt_parse(parser, PRATT_TABLE)


class ParseBinaryExpr:
    """
    Infix expression for a binary operator.
    """

    def __init__(self, parser: Parser, lhs: ParseExpr) -> None:
        self.left = lhs
        self.operator = parser.prev()
        self.right = pratt_parse(parser, PRATT_TABLE)


class ParseAtomExpr:
    """
    Prefix expression for an atomic value expression.
    """

    def __init__(self, parser: Parser) -> None:
        self.token = parser.prev()


@enum.unique
class Precedence(enum.Enum):
    """
    Enumerates the different precedences of infix expressions. The values respect the ordering.
    """

    NONE = 0
    TERM = 1
    CALL = 2


class PrattRule:
    """
    Represents a rule for parsing a token within an expression.
    """

    def __init__(
        self,
        prefix: Optional[Callable[[Parser], ParseExpr]] = None,
        infix: Optional[Callable[[Parser, ParseExpr], ParseExpr]] = None,
        precedence: Precedence = Precedence.NONE,
    ) -> None:
        self.prefix = prefix
        self.infix = infix
        self.precedence = precedence


PRATT_TABLE: DefaultDict[lexer.TokenType, PrattRule] = collections.defaultdict(
    PrattRule,
    {
        lexer.TokenType.MINUS: PrattRule(
            prefix=ParseUnaryExpr, infix=ParseBinaryExpr, precedence=Precedence.TERM
        ),
        lexer.TokenType.PLUS: PrattRule(
            infix=ParseBinaryExpr, precedence=Precedence.TERM
        ),
        lexer.TokenType.STR_LITERAL: PrattRule(prefix=ParseAtomExpr),
        lexer.TokenType.NUM_LITERAL: PrattRule(prefix=ParseAtomExpr),
        lexer.TokenType.INT_LITERAL: PrattRule(prefix=ParseAtomExpr),
        lexer.TokenType.IDENTIFIER: PrattRule(prefix=ParseAtomExpr),
    },
)


def pratt_parse(
    parser: Parser, table: DefaultDict[lexer.TokenType, PrattRule]
) -> Union[ParseExpr, ParseError]:
    """
    Given a table of pratt rules parses an expression from a parser.
    """
    start_token = parser.advance()
    if not start_token:
        return ParseError("expected expression", parser.curr_region())
    if start_token.kind not in table:
        return ParseError("unexpected token", start_token.lexeme)
    prefix_rule = table[start_token.kind]
    if not prefix_rule.prefix:
        return ParseError("unexpected token for prefix expression", start_token.lexeme)
    expr = prefix_rule.prefix(parser)

    def next_rule() -> Optional[Union[PrattRule, ParseError]]:
        token = parser.advance()
        if not token or token.kind not in table:
            parser.backtrack()
            return None
        return table[token.kind]

    infix_rule = next_rule()
    if not infix_rule:
        return expr
    if isinstance(infix_rule, ParseError):
        return infix_rule
    while infix_rule.precedence.value >= prefix_rule.precedence.value:
        if not infix_rule.infix:
            return ParseError(
                "unexpected token for infix expression", parser.prev().lexeme
            )
        expr = infix_rule.infix(parser, expr)
        infix_rule = next_rule()
        if not infix_rule:
            return expr
        if isinstance(infix_rule, ParseError):
            return infix_rule
    return expr
