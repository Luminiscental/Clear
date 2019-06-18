"""
Contains functions and definitions for parsing a list of tokens into a parse tree.
"""

from typing import (
    List,
    Optional,
    Union,
    Tuple,
    Callable,
    DefaultDict,
    Iterable,
    NamedTuple,
)

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
        # TODO:
        # Refactor error propogation when parsing
        # (i.e. return (node, errors) instead of storing errors in nodes)
        print(f"[error] {self.display()}")

    def display(self) -> str:
        """
        Returns a string of information about the error.
        """
        # TODO:
        # Line number, highlight region in context, formatting, e.t.c.
        return f"{self.message}: {self.region}"


class ParseNode:
    """
    Base class for nodes of the parse tree.
    """

    def pprint(self) -> str:
        """
        Pretty prints the node back as a part of valid Clear code.
        """
        raise NotImplementedError()


def indent(orig: str) -> str:
    """
    Indents a string with four spaces.
    """
    return "\n".join(f"    {line}" for line in orig.splitlines())


class ParseTree(ParseNode):
    """
    The root node of the parse tree, contains a list of declarations.

    ParseTree : ParseDecl* ;
    """

    def __init__(self, decls: List["ParseDecl"]) -> None:
        self.decls = decls

    def pprint(self) -> str:
        return "\n".join(decl.pprint() for decl in self.decls)

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


class ParseDecl(ParseNode):
    """
    Parse node for a generic declaration.

    ParseDecl : ParseValueDecl | ParseFuncDecl | ParseStmt ;
    """

    def __init__(
        self, decl: Union["ParseValueDecl", "ParseFuncDecl", "ParseStmt"]
    ) -> None:
        self.decl = decl

    def pprint(self) -> str:
        return self.decl.pprint()

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


class ParseValueDecl(ParseNode):
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

    def pprint(self) -> str:
        ident_str = "<error>" if isinstance(self.ident, ParseError) else str(self.ident)
        type_str = self.val_type.pprint() if self.val_type else ""
        init_str = (
            "<error>" if isinstance(self.expr, ParseError) else self.expr.pprint()
        )
        return f"val {ident_str} {type_str} = {init_str};"

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


class ParseFuncDecl(ParseNode):
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

    def pprint(self) -> str:
        ident_str = "<error>" if isinstance(self.ident, ParseError) else str(self.ident)
        return f"func {ident_str}{self.params.pprint()} {self.return_type.pprint()} {self.block.pprint()}"

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


class ParseParams(ParseNode):
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

    def pprint(self) -> str:
        def pairs() -> Iterable[str]:
            for param_type, param_ident in self.pairs:
                ident_str = (
                    "<error>"
                    if isinstance(param_ident, ParseError)
                    else str(param_ident)
                )
                yield f"{param_type.pprint()} {ident_str}"

        inner_str = ", ".join(pairs())
        return f"({inner_str})"

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


class ParseStmt(ParseNode):
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

    def pprint(self) -> str:
        return self.stmt.pprint()

    @staticmethod
    def parse(parser: Parser) -> "ParseStmt":
        """
        Parses a ParseStmt from a Parser.
        """
        if parser.match(lexer.TokenType.PRINT):
            return ParseStmt(ParsePrintStmt.finish(parser))
        if parser.match(lexer.TokenType.LEFT_BRACE):
            return ParseStmt(ParseBlockStmt.finish(parser))
        if parser.match(lexer.TokenType.IF):
            return ParseStmt(ParseIfStmt.finish(parser))
        if parser.match(lexer.TokenType.WHILE):
            return ParseStmt(ParseWhileStmt.finish(parser))
        if parser.match(lexer.TokenType.RETURN):
            return ParseStmt(ParseReturnStmt.finish(parser))
        return ParseStmt(ParseExprStmt.parse(parser))


class ParsePrintStmt(ParseNode):
    """
    Parse node for a print statement.

    ParsePrintStmt : "print" ParseExpr ";" ;
    """

    def __init__(
        self, expr: Union["ParseExpr", ParseError], errors: List[ParseError]
    ) -> None:
        self.errors = errors
        self.expr = expr

    def pprint(self) -> str:
        expr_str = (
            "<error>" if isinstance(self.expr, ParseError) else self.expr.pprint()
        )
        return f"print {expr_str};"

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


class ParseBlockStmt(ParseNode):
    """
    Parse node for a block statement.

    ParseBlockStmt : "{" ParseDecl* "}" ;
    """

    def __init__(self, decls: List[ParseDecl], errors: List[ParseError]) -> None:
        self.errors = errors
        self.decls = decls

    def pprint(self) -> str:
        inner_str = indent("\n".join(decl.pprint() for decl in self.decls))
        return f"{{\n{inner_str}\n}}"

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


class ParseIfStmt(ParseNode):
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

    def pprint(self) -> str:
        def conds() -> Iterable[str]:
            first = True
            for cond_expr, cond_block in self.pairs:
                expr_str = (
                    "<error>"
                    if isinstance(cond_expr, ParseError)
                    else cond_expr.pprint()
                )
                else_str = "else" if not first else ""
                yield f"{else_str} if ({expr_str}) {cond_block.pprint()}"
                first = False

        conds_str = " ".join(conds())
        else_str = f"else {self.fallback.pprint()}" if self.fallback else ""
        return f"{conds_str} {else_str}"

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


class ParseWhileStmt(ParseNode):
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

    def pprint(self) -> str:
        if not self.cond:
            cond_str = ""
        elif isinstance(self.cond, ParseError):
            cond_str = "(<error>) "
        else:
            cond_str = f"({self.cond.pprint()})"
        return f"while {cond_str}{self.block.pprint()}"

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


class ParseReturnStmt(ParseNode):
    """
    Parse node for a return statement.

    ParseReturnStmt : "return" ParseExpr? ";" ;
    """

    def __init__(
        self, expr: Optional[Union["ParseExpr", ParseError]], errors: List[ParseError]
    ) -> None:
        self.errors = errors
        self.expr = expr

    def pprint(self) -> str:
        if not self.expr:
            return "return;"
        expr_str = (
            "<error>" if isinstance(self.expr, ParseError) else self.expr.pprint()
        )
        return f"return {expr_str};"

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


class ParseExprStmt(ParseNode):
    """
    Parse node for an expression statement.

    ParseExprStmt : ParseExpr ";" ;
    """

    def __init__(
        self, expr: Union["ParseExpr", ParseError], errors: List[ParseError]
    ) -> None:
        self.errors = errors
        self.expr = expr

    def pprint(self) -> str:
        expr_str = (
            "<error>" if isinstance(self.expr, ParseError) else self.expr.pprint()
        )
        return f"{expr_str};"

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


class ParseType(ParseNode):
    """
    Parse node for a type.

    ParseType : ( "(" ParseType ")" | ParseFuncType | ParseAtomType ) ( "?" )? ;
    """

    def __init__(self, type_node: Union["ParseFuncType", "ParseAtomType"]) -> None:
        self.type_node = type_node
        self.optional = False
        self.errors: List[ParseError] = []

    def pprint(self) -> str:
        if self.optional:
            return f"({self.type_node.pprint()})?"
        return self.type_node.pprint()

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


class ParseFuncType(ParseNode):
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

    def pprint(self) -> str:
        params_str = ", ".join(param.pprint() for param in self.params)
        return f"func({params_str}) {self.return_type.pprint()}"

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


class ParseAtomType(ParseNode):
    """
    Parse node for an atomic type.

    ParseAtomType : identifier | "void" ;
    """

    def __init__(
        self, token: Union[lexer.Token, ParseError], errors: List[ParseError]
    ) -> None:
        self.token = token
        self.errors = errors

    def pprint(self) -> str:
        return "<error>" if isinstance(self.token, ParseError) else str(self.token)

    @staticmethod
    def parse(parser: Parser) -> "ParseAtomType":
        """
        Parse a ParseAtomType from a Parser.
        """
        errors = []
        if parser.match(lexer.TokenType.IDENTIFIER):
            token: Union[lexer.Token, ParseError] = parser.prev()
        elif parser.match(lexer.TokenType.VOID):
            token = parser.prev()
        else:
            token = ParseError("expected type", parser.curr_region())
            errors.append(token)
        return ParseAtomType(token, errors)


ParseExpr = Union["ParseUnaryExpr", "ParseBinaryExpr", "ParseAtomExpr"]


class ParseUnaryExpr(ParseNode):
    """
    Prefix expression for a unary operator.
    """

    def __init__(self, parser: Parser) -> None:
        self.operator = parser.prev()
        self.target = pratt_parse(parser, PRATT_TABLE, precedence=Precedence.UNARY)

    def pprint(self) -> str:
        target_str = (
            "<error>" if isinstance(self.target, ParseError) else self.target.pprint()
        )
        return f"{self.operator}({target_str})"


class ParseBinaryExpr(ParseNode):
    """
    Infix expression for a binary operator.
    """

    def __init__(self, parser: Parser, lhs: ParseExpr) -> None:
        self.left = lhs
        self.operator = parser.prev()
        prec = PRATT_TABLE[self.operator.kind].precedence
        self.right = pratt_parse(parser, PRATT_TABLE, prec.next())

    def pprint(self) -> str:
        right_str = (
            "<error>" if isinstance(self.right, ParseError) else self.right.pprint()
        )
        return f"({self.left.pprint()}){self.operator}({right_str})"


class ParseAtomExpr(ParseNode):
    """
    Prefix expression for an atomic value expression.
    """

    def __init__(self, parser: Parser) -> None:
        self.token = parser.prev()

    def pprint(self) -> str:
        return str(self.token)


Comparison = Union[bool, "NotImplemented"]


@enum.unique
class Precedence(enum.Enum):
    """
    Enumerates the different precedences of infix expressions. The values respect the ordering.
    """

    NONE = 0
    ASSIGNMENT = 1
    OR = 2
    AND = 3
    EQUALITY = 4
    COMPARISON = 5
    TERM = 6
    FACTOR = 7
    UNARY = 8
    CALL = 9
    MAX = 10

    def __lt__(self, other: object) -> Comparison:
        if not isinstance(other, Precedence):
            return NotImplemented
        return self.value < other.value

    def __le__(self, other: object) -> Comparison:
        if not isinstance(other, Precedence):
            return NotImplemented
        return self.value <= other.value

    def __gt__(self, other: object) -> Comparison:
        if not isinstance(other, Precedence):
            return NotImplemented
        return self.value > other.value

    def __ge__(self, other: object) -> Comparison:
        if not isinstance(other, Precedence):
            return NotImplemented
        return self.value >= other.value

    def next(self) -> "Precedence":
        """
        Returns the next highest precedence.
        """
        next_value = self.value + 1
        return Precedence(min(next_value, Precedence.MAX.value))


class PrattRule(NamedTuple):
    """
    Represents a rule for parsing a token within an expression.
    """

    prefix: Optional[Callable[[Parser], ParseExpr]] = None
    infix: Optional[Callable[[Parser, ParseExpr], ParseExpr]] = None
    precedence: Precedence = Precedence.NONE


PRATT_TABLE: DefaultDict[lexer.TokenType, PrattRule] = collections.defaultdict(
    PrattRule,
    {
        lexer.TokenType.MINUS: PrattRule(
            prefix=ParseUnaryExpr, infix=ParseBinaryExpr, precedence=Precedence.TERM
        ),
        lexer.TokenType.PLUS: PrattRule(
            infix=ParseBinaryExpr, precedence=Precedence.TERM
        ),
        lexer.TokenType.STAR: PrattRule(
            infix=ParseBinaryExpr, precedence=Precedence.FACTOR
        ),
        lexer.TokenType.SLASH: PrattRule(
            infix=ParseBinaryExpr, precedence=Precedence.FACTOR
        ),
        lexer.TokenType.OR: PrattRule(infix=ParseBinaryExpr, precedence=Precedence.OR),
        lexer.TokenType.AND: PrattRule(
            infix=ParseBinaryExpr, precedence=Precedence.AND
        ),
        lexer.TokenType.STR_LITERAL: PrattRule(prefix=ParseAtomExpr),
        lexer.TokenType.NUM_LITERAL: PrattRule(prefix=ParseAtomExpr),
        lexer.TokenType.INT_LITERAL: PrattRule(prefix=ParseAtomExpr),
        lexer.TokenType.IDENTIFIER: PrattRule(prefix=ParseAtomExpr),
    },
)


def pratt_prefix(
    parser: Parser, table: DefaultDict[lexer.TokenType, PrattRule]
) -> Union[ParseExpr, ParseError]:
    """
    Parses a prefix expression from a Parser using a pratt table.
    """
    start_token = parser.advance()
    if not start_token:
        return ParseError("unexpected EOF; expected expression", parser.curr_region())
    rule = table[start_token.kind]
    if not rule.prefix:
        return ParseError("unexpected token; expected expression", start_token.lexeme)
    expr = rule.prefix(parser)
    return expr


def pratt_infix(
    parser: Parser,
    table: DefaultDict[lexer.TokenType, PrattRule],
    expr: ParseExpr,
    precedence: Precedence,
) -> Optional[Union[ParseExpr, ParseError]]:
    """
    Given an initial expression and precedence parses an infix expression from a Parser using a
    pratt table if there are no infix extensions bound by the precedence returns None.
    """
    # See if there's an infix token
    # If not, there's no expression to parse
    token = parser.curr()
    if not token:
        return None
    rule = table[token.kind]
    if not rule.infix:
        return None
    # While the infix token is bound by the precedence of the expression
    while rule.precedence >= precedence:
        # Advance past the infix token and run its rule
        parser.advance()
        if rule.infix:  # Should always be true but mypy can't tell
            expr = rule.infix(parser, expr)
        # See if there's another infix token
        # If not, the expression is finished
        token = parser.curr()
        if not token:
            break
        rule = table[token.kind]
        if not rule.infix:
            break
    return expr


def pratt_parse(
    parser: Parser,
    table: DefaultDict[lexer.TokenType, PrattRule],
    precedence: Precedence = Precedence.ASSIGNMENT,
) -> Union[ParseExpr, ParseError]:
    """
    Parses an expression bound by a given precedence from a Parser using a pratt table.
    """
    prefix_parse = pratt_prefix(parser, table)
    if isinstance(prefix_parse, ParseError):
        return prefix_parse
    infix_parse = pratt_infix(parser, table, prefix_parse, precedence)
    return infix_parse or prefix_parse
