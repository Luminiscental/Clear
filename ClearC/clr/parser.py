"""
Contains functions and definitions for parsing a list of tokens into a parse tree.
"""

from typing import List, Optional, Union, Tuple

import lexer


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
        Returns a source view from the previous token's region to the current.
        """
        curr = self.curr()
        if curr:
            return lexer.SourceView.range(self.prev().region, curr.region)
        return self.prev().region


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
        expr: "ParseExpr",
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

        expr = ParseExpr.parse(parser)

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
            if not parser.match(lexer.TokenType.COMMA):
                errors.append(
                    ParseError(
                        "missing ',' to delimit parameters", parser.curr_region()
                    )
                )
            parse_pair()

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

    def __init__(self, expr: "ParseExpr", errors: List[ParseError]) -> None:
        self.errors = errors
        self.expr = expr

    @staticmethod
    def finish(parser: Parser) -> "ParsePrintStmt":
        """
        Parses a ParsePrintStmt from a Parser, given that the "print" keyword has already been
        consumed.
        """
        errors = []
        expr = ParseExpr.parse(parser)
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
                errors.append(ParseError("unclosed block", open_brace.region))
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
        pairs: List[Tuple["ParseExpr", ParseBlockStmt]],
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
            cond = ParseExpr.parse(parser)
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
        cond: Optional["ParseExpr"],
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
            cond = ParseExpr.parse(parser)
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

    def __init__(self, expr: Optional["ParseExpr"], errors: List[ParseError]) -> None:
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
            expr = ParseExpr.parse(parser)
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

    def __init__(self, expr: "ParseExpr", errors: List[ParseError]) -> None:
        self.errors = errors
        self.expr = expr

    @staticmethod
    def parse(parser: Parser) -> "ParseExprStmt":
        """
        Parses a ParseExprStmt from a Parser.
        """
        errors = []
        expr = ParseExpr.parse(parser)
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
    """

    def __init__(
        self, token: Union[lexer.Token, ParseError], errors: List[ParseError]
    ) -> None:
        # FIXME
        self.errors = errors
        self.token = token

    @staticmethod
    def parse(parser: Parser) -> "ParseType":
        """
        Parse a ParseType from a Parser.
        """
        token = parser.advance()
        if token:
            return ParseType(token, [])
        err = ParseError("expected type before EOF", parser.curr_region())
        return ParseType(err, [err])


class ParseExpr:
    """
    Parse node for an expression.
    """

    def __init__(
        self, token: Union[lexer.Token, ParseError], errors: List[ParseError]
    ) -> None:
        # FIXME
        self.errors = errors
        self.token = token

    @staticmethod
    def parse(parser: Parser) -> "ParseExpr":
        """
        Parse a ParseExpr from a Parser.
        """
        token = parser.advance()
        if token:
            return ParseExpr(token, [])
        err = ParseError("expected expression before EOF", parser.curr_region())
        return ParseExpr(err, [err])


def parse_tokens(tokens: List[lexer.Token]) -> ParseTree:
    """
    Parses a ParseTree from a list of tokens.
    """
    return ParseTree.parse(Parser(tokens))
