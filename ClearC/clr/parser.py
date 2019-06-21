"""
Contains functions and definitions for parsing a list of tokens into a parse tree.
"""

from typing import (
    List,
    Optional,
    Union,
    Tuple,
    Callable,
    Dict,
    DefaultDict,
    NamedTuple,
    TypeVar,
    Generic,
)

import enum
import collections

import clr.lexer as lexer
import clr.ast as ast


def parse_tokens(
    tokens: List[lexer.Token]
) -> Tuple["ParseTree", List[lexer.CompileError]]:
    """
    Parses a ParseTree from a list of tokens.
    """
    return ParseTree.parse(Parser(tokens))


T = TypeVar("T")  # pylint: disable=invalid-name


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


class ParseNode(Generic[T]):
    """
    Base class for nodes of the parse tree.
    """

    def to_ast(self) -> Union[T, ast.AstError]:
        """
        Convert the parse node to an ast node.
        """
        raise NotImplementedError()


def indent(orig: str) -> str:
    """
    Indents a string with four spaces.
    """
    return "\n".join(f"    {line}" for line in orig.splitlines())


class ParseTree(ParseNode[ast.Ast]):
    """
    The root node of the parse tree, contains a list of declarations.

    ParseTree : ParseDecl* ;
    """

    def __init__(self, decls: List["ParseDecl"]) -> None:
        self.decls = decls

    def to_ast(self) -> Union[ast.Ast, ast.AstError]:
        return ast.Ast.make([decl.to_ast() for decl in self.decls])

    @staticmethod
    def parse(parser: Parser) -> Tuple["ParseTree", List[lexer.CompileError]]:
        """
        Parses a ParseTree from a Parser.
        """
        decls = []
        errors = []
        while not parser.done():
            decl, errs = ParseDecl.parse(parser)
            decls.append(decl)
            errors.extend(errs)
        return ParseTree(decls), errors


class ParseToken(ParseNode[lexer.Token]):
    """
    Parse node for an identifier token to wrap errors of missing tokens.
    """

    def __init__(self, token: Union[lexer.Token, lexer.CompileError]) -> None:
        self.token = token

    def to_ast(self) -> Union[lexer.Token, ast.AstError]:
        if isinstance(self.token, lexer.CompileError):
            return ast.AstError()
        return self.token

    @staticmethod
    def parse(
        parser: Parser, types: List[lexer.TokenType]
    ) -> Tuple["ParseToken", List[lexer.CompileError]]:
        """
        Parses a ParseIdent from a Parser.
        """
        for token_type in types:
            if parser.match(token_type):
                return ParseToken(parser.prev()), []
        err = lexer.CompileError("missing identifier", parser.curr_region())
        return ParseToken(err), [err]


class ParseDecl(ParseNode[ast.AstDecl]):
    """
    Parse node for a generic declaration.

    ParseDecl : ParseValueDecl | ParseFuncDecl | ParseStmt ;
    """

    def __init__(
        self, decl: Union["ParseValueDecl", "ParseFuncDecl", "ParseStmt"]
    ) -> None:
        self.decl = decl

    def to_ast(self) -> Union[ast.AstDecl, ast.AstError]:
        return self.decl.to_ast()

    @staticmethod
    def parse(parser: Parser) -> Tuple["ParseDecl", List[lexer.CompileError]]:
        """
        Parses a ParseDecl from a Parser.
        """
        if parser.match(lexer.TokenType.VAL):
            val_decl, errs = ParseValueDecl.finish(parser)
            return ParseDecl(val_decl), errs
        if parser.match(lexer.TokenType.FUNC):
            func_decl, errs = ParseFuncDecl.finish(parser)
            return ParseDecl(func_decl), errs
        stmt_decl, errs = ParseStmt.parse(parser)
        return ParseDecl(stmt_decl), errs


class ParseValueDecl(ParseNode[ast.AstValueDecl]):
    """
    Parse node for a value declaration.

    ParseValueDecl : "val" identifier (ParseType)? "=" ParseExpr ";" ;
    """

    def __init__(
        self, ident: ParseToken, val_type: Optional["ParseType"], expr: "ParseExpr"
    ):
        self.ident = ident
        self.val_type = val_type
        self.expr = expr

    def to_ast(self) -> Union[ast.AstValueDecl, ast.AstError]:
        return ast.AstValueDecl.make(
            self.ident.to_ast(),
            self.val_type.to_ast() if self.val_type else None,
            self.expr.to_ast(),
        )

    @staticmethod
    def finish(parser: Parser) -> Tuple["ParseValueDecl", List[lexer.CompileError]]:
        """
        Parses a ParseValueDecl from a Parser, given that the "val" keyword has already been
        consumed.
        """
        ident, errors = ParseToken.parse(parser, [lexer.TokenType.IDENTIFIER])

        val_type = None
        if not parser.match(lexer.TokenType.EQUALS):
            val_type, errs = ParseType.parse(parser)
            errors.extend(errs)
            if not parser.match(lexer.TokenType.EQUALS):
                errors.append(
                    lexer.CompileError(
                        "missing '=' for value initializer", parser.curr_region()
                    )
                )

        expr, errs = pratt_parse(parser, PRATT_TABLE)
        errors.extend(errs)

        if not parser.match(lexer.TokenType.SEMICOLON):
            errors.append(
                lexer.CompileError(
                    "missing ';' to end value initializer", parser.curr_region()
                )
            )

        return ParseValueDecl(ident, val_type, expr), errors


class ParseFuncDecl(ParseNode[ast.AstFuncDecl]):
    """
    Parse node for a function declaration.

    ParseFuncDecl : "func" identifier ParseParams ParseType ParseBlockStmt ;
    """

    def __init__(
        self,
        ident: ParseToken,
        params: List[Tuple["ParseType", ParseToken]],
        return_type: "ParseType",
        block: "ParseBlockStmt",
    ) -> None:
        self.ident = ident
        self.params = params
        self.return_type = return_type
        self.block = block

    def to_ast(self) -> Union[ast.AstFuncDecl, ast.AstError]:
        params = []
        for param_type, param_ident in self.params:
            params.append((param_type.to_ast(), param_ident.to_ast()))
        return ast.AstFuncDecl.make(
            self.ident.to_ast(), params, self.return_type.to_ast(), self.block.to_ast()
        )

    @staticmethod
    def finish(parser: Parser) -> Tuple["ParseFuncDecl", List[lexer.CompileError]]:
        """
        Parses a ParseFuncDecl from a Parser, given that the "func" keyword has already been
        consumed.
        """
        ident, errors = ParseToken.parse(parser, [lexer.TokenType.IDENTIFIER])

        def parse_param(parser: Parser) -> Tuple["ParseType", ParseToken]:
            param_type, errs = ParseType.parse(parser)
            errors.extend(errs)
            param_ident, errs = ParseToken.parse(parser, [lexer.TokenType.IDENTIFIER])
            errors.extend(errs)
            return param_type, param_ident

        if not parser.match(lexer.TokenType.LEFT_PAREN):
            errors.append(
                lexer.CompileError(
                    "missing '(' to begin parameters", parser.curr_region()
                )
            )
        params, errs = parse_tuple(parser, parse_param)
        errors.extend(errs)
        return_type, errs = ParseType.parse(parser)
        errors.extend(errs)
        block, errs = ParseBlockStmt.parse(parser)
        errors.extend(errs)
        return ParseFuncDecl(ident, params, return_type, block), errors


def parse_tuple(
    parser: Parser, parse_func: Callable[[Parser], T]
) -> Tuple[List[T], List[lexer.CompileError]]:
    """
    Given that the opening '(' has already been consumed, parse the elements of a tuple (a,b,...)
    form into a list using a parameter function to parse each element.
    """
    opener = parser.prev()
    if parser.match(lexer.TokenType.RIGHT_PAREN):
        return [], []
    errors = []
    pairs = [parse_func(parser)]
    while not parser.match(lexer.TokenType.RIGHT_PAREN):
        if parser.done():
            errors.append(lexer.CompileError("unclosed '('", opener.lexeme))
            break
        if not parser.match(lexer.TokenType.COMMA):
            errors.append(
                lexer.CompileError("missing ',' delimiter", parser.curr_region())
            )
        pairs.append(parse_func(parser))
    return pairs, errors


class ParseStmt(ParseNode[ast.AstStmt]):
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

    def to_ast(self) -> Union[ast.AstStmt, ast.AstError]:
        return self.stmt.to_ast()

    @staticmethod
    def parse(parser: Parser) -> Tuple["ParseStmt", List[lexer.CompileError]]:
        """
        Parses a ParseStmt from a Parser.
        """
        if parser.match(lexer.TokenType.PRINT):
            print_stmt, errs = ParsePrintStmt.finish(parser)
            return ParseStmt(print_stmt), errs
        if parser.match(lexer.TokenType.LEFT_BRACE):
            block_stmt, errs = ParseBlockStmt.finish(parser)
            return ParseStmt(block_stmt), errs
        if parser.match(lexer.TokenType.IF):
            if_stmt, errs = ParseIfStmt.finish(parser)
            return ParseStmt(if_stmt), errs
        if parser.match(lexer.TokenType.WHILE):
            while_stmt, errs = ParseWhileStmt.finish(parser)
            return ParseStmt(while_stmt), errs
        if parser.match(lexer.TokenType.RETURN):
            return_stmt, errs = ParseReturnStmt.finish(parser)
            return ParseStmt(return_stmt), errs
        expr_stmt, errs = ParseExprStmt.parse(parser)
        return ParseStmt(expr_stmt), errs


class ParsePrintStmt(ParseNode[ast.AstPrintStmt]):
    """
    Parse node for a print statement.

    ParsePrintStmt : "print" ParseExpr? ";" ;
    """

    def __init__(self, expr: Optional["ParseExpr"]) -> None:
        self.expr = expr

    def to_ast(self) -> Union[ast.AstPrintStmt, ast.AstError]:
        return ast.AstPrintStmt.make(self.expr.to_ast() if self.expr else None)

    @staticmethod
    def finish(parser: Parser) -> Tuple["ParsePrintStmt", List[lexer.CompileError]]:
        """
        Parses a ParsePrintStmt from a Parser, given that the "print" keyword has already been
        consumed.
        """
        if parser.match(lexer.TokenType.SEMICOLON):
            return ParsePrintStmt(None), []
        errors = []
        expr, errs = pratt_parse(parser, PRATT_TABLE)
        errors.extend(errs)
        if not parser.match(lexer.TokenType.SEMICOLON):
            errors.append(
                lexer.CompileError(
                    "missing ';' to end print statement", parser.curr_region()
                )
            )
        return ParsePrintStmt(expr), errors


class ParseBlockStmt(ParseNode[ast.AstBlockStmt]):
    """
    Parse node for a block statement.

    ParseBlockStmt : "{" ParseDecl* "}" ;
    """

    def __init__(self, decls: List[ParseDecl]) -> None:
        self.decls = decls

    def to_ast(self) -> Union[ast.AstBlockStmt, ast.AstError]:
        return ast.AstBlockStmt.make([decl.to_ast() for decl in self.decls])

    @staticmethod
    def parse(parser: Parser) -> Tuple["ParseBlockStmt", List[lexer.CompileError]]:
        """
        Parses a ParseBlockStmt from a Parser.
        """
        if parser.match(lexer.TokenType.LEFT_BRACE):
            return ParseBlockStmt.finish(parser)

        return (
            ParseBlockStmt(decls=[]),
            [lexer.CompileError("expected '{' to start block", parser.curr_region())],
        )

    @staticmethod
    def finish(parser: Parser) -> Tuple["ParseBlockStmt", List[lexer.CompileError]]:
        """
        Parses a ParseBlockStmt from a Parser, given that the open brace has already been consumed.
        """
        errors = []
        decls = []
        open_brace = parser.prev()
        while not parser.match(lexer.TokenType.RIGHT_BRACE):
            if parser.done():
                errors.append(lexer.CompileError("unclosed block", open_brace.lexeme))
                break
            decl, errs = ParseDecl.parse(parser)
            decls.append(decl)
            errors.extend(errs)
        return ParseBlockStmt(decls), errors


class ParseIfStmt(ParseNode[ast.AstIfStmt]):
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
    ) -> None:
        self.pairs = pairs
        self.fallback = fallback

    def to_ast(self) -> Union[ast.AstIfStmt, ast.AstError]:
        cond_pairs = [(pair[0].to_ast(), pair[1].to_ast()) for pair in self.pairs]
        if not cond_pairs:  # There should be at least an if condition
            return ast.AstError()
        return ast.AstIfStmt.make(
            cond_pairs[0],
            cond_pairs[1:],
            self.fallback.to_ast() if self.fallback else None,
        )

    @staticmethod
    def finish(parser: Parser) -> Tuple["ParseIfStmt", List[lexer.CompileError]]:
        """
        Parses a ParseIfStmt from a Parser, given that the "if" keyword has already been consumed.
        """
        errors = []
        pairs = []
        fallback = None

        def parse_cond() -> None:
            if not parser.match(lexer.TokenType.LEFT_PAREN):
                errors.append(
                    lexer.CompileError(
                        "missing '(' to start condition", parser.curr_region()
                    )
                )
            cond, errs = pratt_parse(parser, PRATT_TABLE)
            errors.extend(errs)
            if not parser.match(lexer.TokenType.RIGHT_PAREN):
                errors.append(
                    lexer.CompileError(
                        "missing ')' to end condition", parser.curr_region()
                    )
                )
            block, errs = ParseBlockStmt.parse(parser)
            errors.extend(errs)
            pairs.append((cond, block))

        # parse the if block
        parse_cond()
        while parser.match(lexer.TokenType.ELSE):
            if parser.match(lexer.TokenType.IF):
                # parse an else if block
                parse_cond()
            else:
                # parse the else block
                fallback, errs = ParseBlockStmt.parse(parser)
                errors.extend(errs)
                break
        return ParseIfStmt(pairs, fallback), errors


class ParseWhileStmt(ParseNode[ast.AstWhileStmt]):
    """
    Parse node for a while statement.

    ParseWhileStmt : "while" ( "(" ParseExpr ")" )? ParseBlockStmt ;
    """

    def __init__(self, cond: Optional["ParseExpr"], block: ParseBlockStmt) -> None:
        self.cond = cond
        self.block = block

    def to_ast(self) -> Union[ast.AstWhileStmt, ast.AstError]:
        return ast.AstWhileStmt.make(
            self.cond.to_ast() if self.cond else None, self.block.to_ast()
        )

    @staticmethod
    def finish(parser: Parser) -> Tuple["ParseWhileStmt", List[lexer.CompileError]]:
        """
        Parses a ParseWhileStmt from a Parser, given that the "while" keyword has already been
        consumed.
        """
        errors = []
        cond = None
        if parser.match(lexer.TokenType.LEFT_PAREN):
            cond, errs = pratt_parse(parser, PRATT_TABLE)
            errors.extend(errs)
            if not parser.match(lexer.TokenType.RIGHT_PAREN):
                errors.append(
                    lexer.CompileError(
                        "missing ')' to end condition", parser.curr_region()
                    )
                )
        block, errs = ParseBlockStmt.parse(parser)
        errors.extend(errs)
        return ParseWhileStmt(cond, block), errors


class ParseReturnStmt(ParseNode[ast.AstReturnStmt]):
    """
    Parse node for a return statement.

    ParseReturnStmt : "return" ParseExpr? ";" ;
    """

    def __init__(self, expr: Optional["ParseExpr"]) -> None:
        self.expr = expr

    def to_ast(self) -> Union[ast.AstReturnStmt, ast.AstError]:
        return ast.AstReturnStmt.make(self.expr.to_ast() if self.expr else None)

    @staticmethod
    def finish(parser: Parser) -> Tuple["ParseReturnStmt", List[lexer.CompileError]]:
        """
        Parses a ParseReturnStmt from a Parser, given that the "return" keyword has already been
        consumed.
        """
        errors = []
        expr = None
        if not parser.match(lexer.TokenType.SEMICOLON):
            expr, errs = pratt_parse(parser, PRATT_TABLE)
            errors.extend(errs)
            if not parser.match(lexer.TokenType.SEMICOLON):
                errors.append(
                    lexer.CompileError(
                        "missing ';' to end return statement", parser.curr_region()
                    )
                )
        return ParseReturnStmt(expr), errors


class ParseExprStmt(ParseNode[ast.AstExprStmt]):
    """
    Parse node for an expression statement.

    ParseExprStmt : ParseExpr ";" ;
    """

    def __init__(self, expr: "ParseExpr") -> None:
        self.expr = expr

    def to_ast(self) -> Union[ast.AstExprStmt, ast.AstError]:
        return ast.AstExprStmt.make(self.expr.to_ast())

    @staticmethod
    def parse(parser: Parser) -> Tuple["ParseExprStmt", List[lexer.CompileError]]:
        """
        Parses a ParseExprStmt from a Parser.
        """
        errors = []
        expr, errs = pratt_parse(parser, PRATT_TABLE)
        errors.extend(errs)
        if not parser.match(lexer.TokenType.SEMICOLON):
            errors.append(
                lexer.CompileError(
                    "missing ';' to end expression statement", parser.curr_region()
                )
            )
        return ParseExprStmt(expr), errors


class ParseType(ParseNode[ast.AstType]):
    """
    Parse node for a type.

    ParseType : ( "(" ParseType ")" | ParseFuncType | ParseAtomType ) ( "?" )? ;
    """

    def __init__(
        self,
        type_node: Union["ParseFuncType", "ParseAtomType"],
        region: lexer.SourceView,
    ) -> None:
        self.type_node = type_node
        self.optional = False
        self.region = region

    def to_ast(self) -> Union[ast.AstType, ast.AstError]:
        return (
            ast.AstOptionalType.make(self.type_node.to_ast(), self.region)
            if self.optional
            else self.type_node.to_ast()
        )

    @staticmethod
    def parse(parser: Parser) -> Tuple["ParseType", List[lexer.CompileError]]:
        """
        Parse a ParseType from a Parser.
        """
        errors = []

        if parser.match(lexer.TokenType.LEFT_PAREN):
            start = parser.prev().lexeme
            result, errs = ParseType.parse(parser)
            errors.extend(errs)
            if not parser.match(lexer.TokenType.RIGHT_PAREN):
                errors.append(
                    lexer.CompileError(
                        "missing ')' to end type grouping", parser.curr_region()
                    )
                )
            end = parser.prev().lexeme
            result.region = lexer.SourceView.range(start, end)
            return result, errors

        if parser.match(lexer.TokenType.FUNC):
            start = parser.prev().lexeme
            func_type, errs = ParseFuncType.finish(parser)
            errors.extend(errs)
            type_node: Union["ParseFuncType", "ParseAtomType"] = func_type
        else:
            atom_type, errs = ParseAtomType.parse(parser)
            start = (
                atom_type.token.token.lexeme
                if isinstance(atom_type.token.token, lexer.Token)
                else parser.prev().lexeme
            )
            errors.extend(errs)
            type_node = atom_type

        if parser.match(lexer.TokenType.QUESTION_MARK):
            result.optional = True

        end = parser.prev().lexeme
        region = lexer.SourceView.range(start, end)

        return ParseType(type_node, region), errors


class ParseFuncType(ParseNode[ast.AstFuncType]):
    """
    Parse node for a function type.

    ParseFuncType : "func" "(" ( ParseType ( "," ParseType )* )? ")" ParseType ;
    """

    def __init__(
        self, params: List[ParseType], return_type: ParseType, region: lexer.SourceView
    ) -> None:
        self.params = params
        self.return_type = return_type
        self.region = region

    def to_ast(self) -> Union[ast.AstFuncType, ast.AstError]:
        return ast.AstFuncType.make(
            [param.to_ast() for param in self.params],
            self.return_type.to_ast(),
            self.region,
        )

    @staticmethod
    def finish(parser: Parser) -> Tuple["ParseFuncType", List[lexer.CompileError]]:
        """
        Parse a ParseFuncType from a Parser given that the "func" keyword has already been
        consumed.
        """
        errors = []
        start = parser.prev().lexeme

        if not parser.match(lexer.TokenType.LEFT_PAREN):
            errors.append(
                lexer.CompileError(
                    "missing '(' to begin parameter types", parser.curr_region()
                )
            )

        def parse_param(parser: Parser) -> ParseType:
            param_type, errs = ParseType.parse(parser)
            errors.extend(errs)
            return param_type

        params, errs = parse_tuple(parser, parse_param)
        errors.extend(errs)

        return_type, errs = ParseType.parse(parser)
        errors.extend(errs)

        end = parser.prev().lexeme
        region = lexer.SourceView.range(start, end)

        return ParseFuncType(params, return_type, region), errors


class ParseAtomType(ParseNode[ast.AstAtomType]):
    """
    Parse node for an atomic type.

    ParseAtomType : identifier | "void" ;
    """

    def __init__(self, token: ParseToken) -> None:
        self.token = token

    def to_ast(self) -> Union[ast.AstAtomType, ast.AstError]:
        return ast.AstAtomType.make(self.token.to_ast())

    @staticmethod
    def parse(parser: Parser) -> Tuple["ParseAtomType", List[lexer.CompileError]]:
        """
        Parse a ParseAtomType from a Parser.
        """
        token, errors = ParseToken.parse(
            parser, [lexer.TokenType.IDENTIFIER, lexer.TokenType.VOID]
        )
        return ParseAtomType(token), errors


class ParseExpr(ParseNode[ast.AstExpr]):
    """
    Parse node for an expression.
    """

    def __init__(
        self,
        expr: Union[
            "ParseUnaryExpr",
            "ParseBinaryExpr",
            "ParseAtomExpr",
            "ParseCallExpr",
            lexer.CompileError,
        ],
        region: lexer.SourceView,
    ) -> None:
        self.expr = expr
        self.region = region

    def to_ast(self) -> Union[ast.AstExpr, ast.AstError]:
        if isinstance(self.expr, lexer.CompileError):
            return ast.AstError()
        return self.expr.to_ast()


class ParseUnaryExpr(ParseNode[ast.AstUnaryExpr]):
    """
    Prefix expression for a unary operator.
    """

    def __init__(self, operator: lexer.Token, target: ParseExpr) -> None:
        self.operator = operator
        self.target = target

    def to_ast(self) -> Union[ast.AstUnaryExpr, ast.AstError]:
        return ast.AstUnaryExpr.make(
            self.operator,
            self.target.to_ast(),
            lexer.SourceView.range(self.operator.lexeme, self.target.region),
        )

    @staticmethod
    def finish(parser: Parser) -> Tuple["ParseExpr", List[lexer.CompileError]]:
        """
        Parse a unary expression from a Parser given that the operator has already been consumed.
        """
        operator = parser.prev()
        target, errs = pratt_parse(parser, PRATT_TABLE, precedence=Precedence.UNARY)
        region = lexer.SourceView.range(operator.lexeme, target.region)
        return ParseExpr(ParseUnaryExpr(operator, target), region), errs


class ParseBinaryExpr(ParseNode[ast.AstBinaryExpr]):
    """
    Infix expression for a binary operator.
    """

    def __init__(
        self, left: ParseExpr, operator: lexer.Token, right: ParseExpr
    ) -> None:
        self.left = left
        self.operator = operator
        self.right = right

    def to_ast(self) -> Union[ast.AstBinaryExpr, ast.AstError]:
        return ast.AstBinaryExpr.make(
            self.operator,
            self.left.to_ast(),
            self.right.to_ast(),
            lexer.SourceView.range(self.left.region, self.right.region),
        )

    @staticmethod
    def finish(
        parser: Parser, lhs: ParseExpr
    ) -> Tuple["ParseExpr", List[lexer.CompileError]]:
        """
        Parse the right hand side of a binary expression from a Parser given that the operator has
        already been consumed.
        """
        left = lhs
        operator = parser.prev()
        prec = PRATT_TABLE[operator.kind].precedence
        right, errs = pratt_parse(parser, PRATT_TABLE, prec.next())
        region = lexer.SourceView.range(left.region, right.region)
        return ParseExpr(ParseBinaryExpr(left, operator, right), region), errs


class ParseCallExpr(ParseNode[ast.AstCallExpr]):
    """
    Infix expression for a function call.
    """

    def __init__(
        self, function: ParseExpr, args: List[ParseExpr], region: lexer.SourceView
    ) -> None:
        self.function = function
        self.args = args
        self.region = region

    def to_ast(self) -> Union[ast.AstCallExpr, ast.AstError]:
        return ast.AstCallExpr.make(
            self.function.to_ast(), [arg.to_ast() for arg in self.args], self.region
        )

    @staticmethod
    def finish(
        parser: Parser, lhs: ParseExpr
    ) -> Tuple["ParseExpr", List[lexer.CompileError]]:
        """
        Parse the call part of a function call expression given that the open parenthesis has
        already been consumed.
        """
        function = lhs
        errors = []

        def parse_arg(parser: Parser) -> ParseExpr:
            parse, errs = pratt_parse(parser, PRATT_TABLE)
            errors.extend(errs)
            return parse

        args, errs = parse_tuple(parser, parse_arg)
        errors.extend(errs)

        region = lexer.SourceView.range(function.region, parser.prev().lexeme)
        return ParseExpr(ParseCallExpr(function, args, region), region), errors


class ParseAtomExpr(ParseNode[ast.AstAtomExpr]):
    """
    Prefix expression for an atomic value expression.
    """

    def __init__(self, token: lexer.Token) -> None:
        self.token = token

    def to_ast(self) -> Union[ast.AstAtomExpr, ast.AstError]:
        token_exprs: Dict[lexer.TokenType, Callable[[lexer.Token], ast.AstAtomExpr]] = {
            lexer.TokenType.INT_LITERAL: ast.AstIntExpr,
            lexer.TokenType.NUM_LITERAL: ast.AstNumExpr,
            lexer.TokenType.STR_LITERAL: ast.AstStrExpr,
            lexer.TokenType.IDENTIFIER: ast.AstIdentExpr,
            lexer.TokenType.TRUE: ast.AstBoolExpr,
            lexer.TokenType.FALSE: ast.AstBoolExpr,
        }
        if self.token.kind in token_exprs:
            return token_exprs[self.token.kind](self.token)
        return ast.AstError()

    @staticmethod
    def finish(parser: Parser) -> Tuple["ParseExpr", List[lexer.CompileError]]:
        """
        Parse an atomic value expression from a Parser given that the token has already been
        consumed.
        """
        # TODO: Sanitize for size and precision with num/int literals
        token = parser.prev()
        return ParseExpr(ParseAtomExpr(token), token.lexeme), []


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


PrefixRule = Callable[[Parser], Tuple[ParseExpr, List[lexer.CompileError]]]
InfixRule = Callable[[Parser, ParseExpr], Tuple[ParseExpr, List[lexer.CompileError]]]


class PrattRule(NamedTuple):
    """
    Represents a rule for parsing a token within an expression.
    """

    prefix: Optional[PrefixRule] = None
    infix: Optional[InfixRule] = None
    precedence: Precedence = Precedence.NONE


PRATT_TABLE: DefaultDict[lexer.TokenType, PrattRule] = collections.defaultdict(
    PrattRule,
    {
        lexer.TokenType.LEFT_PAREN: PrattRule(
            infix=ParseCallExpr.finish, precedence=Precedence.CALL
        ),
        lexer.TokenType.MINUS: PrattRule(
            prefix=ParseUnaryExpr.finish,
            infix=ParseBinaryExpr.finish,
            precedence=Precedence.TERM,
        ),
        lexer.TokenType.PLUS: PrattRule(
            infix=ParseBinaryExpr.finish, precedence=Precedence.TERM
        ),
        lexer.TokenType.STAR: PrattRule(
            infix=ParseBinaryExpr.finish, precedence=Precedence.FACTOR
        ),
        lexer.TokenType.SLASH: PrattRule(
            infix=ParseBinaryExpr.finish, precedence=Precedence.FACTOR
        ),
        lexer.TokenType.OR: PrattRule(
            infix=ParseBinaryExpr.finish, precedence=Precedence.OR
        ),
        lexer.TokenType.AND: PrattRule(
            infix=ParseBinaryExpr.finish, precedence=Precedence.AND
        ),
        lexer.TokenType.STR_LITERAL: PrattRule(prefix=ParseAtomExpr.finish),
        lexer.TokenType.NUM_LITERAL: PrattRule(prefix=ParseAtomExpr.finish),
        lexer.TokenType.INT_LITERAL: PrattRule(prefix=ParseAtomExpr.finish),
        lexer.TokenType.IDENTIFIER: PrattRule(prefix=ParseAtomExpr.finish),
        lexer.TokenType.TRUE: PrattRule(prefix=ParseAtomExpr.finish),
        lexer.TokenType.FALSE: PrattRule(prefix=ParseAtomExpr.finish),
    },
)


def pratt_prefix(
    parser: Parser, table: DefaultDict[lexer.TokenType, PrattRule]
) -> Tuple[ParseExpr, List[lexer.CompileError]]:
    """
    Parses a prefix expression from a Parser using a pratt table.
    """
    start_token = parser.advance()
    if not start_token:
        err = lexer.CompileError(
            "unexpected EOF; expected expression", parser.curr_region()
        )
        # TODO: Do something more elegant with the region here
        return ParseExpr(err, region=lexer.SourceView.all("<error>")), [err]
    rule = table[start_token.kind]
    if not rule.prefix:
        err = lexer.CompileError(
            "unexpected token; expected expression", start_token.lexeme
        )
        return ParseExpr(err, region=lexer.SourceView.all("<error>")), [err]
    return rule.prefix(parser)


def pratt_infix(
    parser: Parser,
    table: DefaultDict[lexer.TokenType, PrattRule],
    expr: ParseExpr,
    precedence: Precedence,
) -> Optional[Tuple[ParseExpr, List[lexer.CompileError]]]:
    """
    Given an initial expression and precedence parses an infix expression from a Parser using a
    pratt table. If there are no infix extensions bound by the precedence returns None.
    """
    errors = []
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
            expr, errs = rule.infix(parser, expr)
            errors.extend(errs)
        # See if there's another infix token
        # If not, the expression is finished
        token = parser.curr()
        if not token:
            break
        rule = table[token.kind]
        if not rule.infix:
            break
    return expr, errors


def pratt_parse(
    parser: Parser,
    table: DefaultDict[lexer.TokenType, PrattRule],
    precedence: Precedence = Precedence.ASSIGNMENT,
) -> Tuple[ParseExpr, List[lexer.CompileError]]:
    """
    Parses an expression bound by a given precedence from a Parser using a pratt table.
    """
    prefix_expr, errs = pratt_prefix(parser, table)
    infix_parse = pratt_infix(parser, table, prefix_expr, precedence)
    if infix_parse:
        return infix_parse[0], errs + infix_parse[1]
    return prefix_expr, errs
