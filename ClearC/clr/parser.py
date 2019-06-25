"""
Contains functions and definitions for parsing a list of tokens into a parse tree.
"""

from typing import (
    List,
    Sequence,
    Iterable,
    Optional,
    Union,
    Tuple,
    Callable,
    DefaultDict,
    NamedTuple,
    TypeVar,
)

import enum
import collections

import clr.errors as er
import clr.lexer as lx
import clr.ast as ast


def parse_tokens(tokens: Sequence[lx.Token]) -> Union[ast.Ast, er.CompileError]:
    """
    Parses an ast from a list of tokens.
    """
    return parse_ast(Parser(tokens))


T = TypeVar("T")  # pylint: disable=invalid-name


class Parser:
    """
    A wrapper class for parsing a list of tokens.
    """

    def __init__(self, tokens: Sequence[lx.Token]) -> None:
        self.tokens = tokens
        self.current = 0

    def done(self) -> bool:
        """
        Returns whether the whole token list has been consumed.
        """
        return self.current == len(self.tokens)

    def prev(self) -> lx.Token:
        """
        Returns the previous token.
        """
        return self.tokens[self.current - 1]

    def curr(self) -> Optional[lx.Token]:
        """
        Returns the current token, or None if there are no more tokens to parse.
        """
        return None if self.done() else self.tokens[self.current]

    def advance(self) -> Optional[lx.Token]:
        """
        Consumes a token and returns it, if there are no tokens left returns None.
        """
        if self.done():
            return None

        self.current += 1
        return self.prev()

    def check(self, kind: lx.TokenType) -> bool:
        """
        Checks if the current token is of a given type.
        """
        curr = self.curr()
        if curr:
            return curr.kind == kind
        return False

    def match(self, kind: lx.TokenType) -> bool:
        """
        Checks if the current token is of a given type, and advances past it if it is.
        """
        result = self.check(kind)
        if result:
            self.current += 1
        return result

    def curr_region(self) -> er.SourceView:
        """
        Returns a source view of the current token (or the previous if the parser is done).
        """
        curr = self.curr()
        if curr:
            return curr.lexeme
        return self.prev().lexeme


def indent(orig: str) -> str:
    """
    Indents a string with four spaces.
    """
    return "\n".join(f"    {line}" for line in orig.splitlines())


def parse_ast(parser: Parser) -> Union[ast.Ast, er.CompileError]:
    """
    Parse the ast from a parser or return an error.

    Ast : AstDecl* ;
    """
    decls = []
    while not parser.done():
        decl = parse_decl(parser)
        if isinstance(decl, er.CompileError):
            return decl
        decls.append(decl)
    return ast.Ast(decls)


def parse_token(parser: Parser, kinds: Iterable[lx.TokenType]) -> Optional[lx.Token]:
    """
    Parses a token from a given iterable of token types to check, and if none of the types match
    returns None.
    """
    for kind in kinds:
        if parser.match(kind):
            return parser.prev()
    return None


def parse_decl(parser: Parser) -> Union[ast.AstDecl, er.CompileError]:
    """
    Parse a declaration from the parser or return an error.

    AstDecl : AstValueDecl | AstFuncDecl | AstStmt ;
    """
    if parser.match(lx.TokenType.VAL):
        return finish_value_decl(parser)
    if parser.match(lx.TokenType.FUNC):
        return finish_func_decl(parser)
    return parse_stmt(parser)


def finish_value_decl(parser: Parser) -> Union[ast.AstValueDecl, er.CompileError]:
    """
    Parse a value declaration from the parser or return an error. Assumes that the "val" token has
    already been consumed.

    AstValueDecl : "val" IDENTIFIER AstType? "=" AstExpr ";" ;
    """
    start = parser.prev().lexeme
    ident = parse_token(parser, [lx.TokenType.IDENTIFIER])
    if ident is None:
        return er.CompileError(
            message="missing value name", regions=[parser.curr_region()]
        )

    val_type = None
    if not parser.match(lx.TokenType.EQUALS):
        val_type_ = parse_type(parser)
        if isinstance(val_type_, er.CompileError):
            return val_type_
        val_type = val_type_
        if not parser.match(lx.TokenType.EQUALS):
            return er.CompileError(
                message="missing '=' for value initializer",
                regions=[parser.curr_region()],
            )

    expr = parse_expr(parser)
    if isinstance(expr, er.CompileError):
        return expr

    if not parser.match(lx.TokenType.SEMICOLON):
        return er.CompileError(
            message="missing ';' to end value initializer",
            regions=[parser.prev().lexeme, parser.curr_region()],
        )

    region = er.SourceView.range(start, parser.prev().lexeme)
    return ast.AstValueDecl(str(ident), val_type, expr, region)


def finish_func_decl(parser: Parser) -> Union[ast.AstFuncDecl, er.CompileError]:
    """
    Parse a function declaration from the parser or return an error. Assumes that the "func" token
    has already been consumed.

    AstFuncDecl : "func" IDENTIFIER "(" ( AstParam ( "," AstParam )* )? ")" AstType AstBlockStmt ;
    """
    start = parser.prev().lexeme
    ident = parse_token(parser, [lx.TokenType.IDENTIFIER])
    if ident is None:
        return er.CompileError(
            message="missing function name", regions=[parser.curr_region()]
        )

    if not parser.match(lx.TokenType.LEFT_PAREN):
        return er.CompileError(
            message="missing '(' to begin parameters", regions=[parser.curr_region()]
        )

    params = parse_tuple(parser, parse_param)
    if isinstance(params, er.CompileError):
        return params

    return_type = parse_type(parser)
    if isinstance(return_type, er.CompileError):
        return return_type

    if not parser.match(lx.TokenType.LEFT_BRACE):
        return er.CompileError(
            message="expected function body", regions=[parser.curr_region()]
        )
    block = finish_block_stmt(parser)
    if isinstance(block, er.CompileError):
        return block

    region = er.SourceView.range(start, parser.prev().lexeme)
    return ast.AstFuncDecl(str(ident), params, return_type, block, region)


def parse_param(parser: Parser) -> Union[ast.AstParam, er.CompileError]:
    """
    Parse a parameter from the parser or return an error.

    AstParam : AstType IDENTIFIER ;
    """
    param_type = parse_type(parser)
    if isinstance(param_type, er.CompileError):
        return param_type
    param_ident = parse_token(parser, [lx.TokenType.IDENTIFIER])
    if param_ident is None:
        return er.CompileError(
            message="missing parameter name", regions=[parser.curr_region()]
        )
    return ast.AstParam(param_type, param_ident)


def parse_tuple(
    parser: Parser, parse_func: Callable[[Parser], Union[T, er.CompileError]]
) -> Union[List[T], er.CompileError]:
    """
    Given that the opening '(' has already been consumed, parse the elements of a tuple (a,b,...)
    form into a list using a parameter function to parse each element.
    """
    opener = parser.prev()
    if parser.match(lx.TokenType.RIGHT_PAREN):
        return []

    first = parse_func(parser)
    if isinstance(first, er.CompileError):
        return first
    pairs = [first]

    while not parser.match(lx.TokenType.RIGHT_PAREN):
        if parser.done():
            return er.CompileError(message="unclosed '('", regions=[opener.lexeme])
        if not parser.match(lx.TokenType.COMMA):
            return er.CompileError("missing ',' delimiter", [parser.curr_region()])
        elem = parse_func(parser)
        if isinstance(elem, er.CompileError):
            return elem
        pairs.append(elem)
    return pairs


def parse_stmt(parser: Parser) -> Union[ast.AstStmt, er.CompileError]:
    """
    Parse a statement from the parser or return an error.

    AstStmt : AstPrintStmt
            | AstBlockStmt
            | AstIfStmt
            | AstWhileStmt
            | AstReturnStmt
            | AstExprStmt
            ;
    """
    if parser.match(lx.TokenType.PRINT):
        return finish_print_stmt(parser)
    if parser.match(lx.TokenType.LEFT_BRACE):
        return finish_block_stmt(parser)
    if parser.match(lx.TokenType.IF):
        return finish_if_stmt(parser)
    if parser.match(lx.TokenType.WHILE):
        return finish_while_stmt(parser)
    if parser.match(lx.TokenType.RETURN):
        return finish_return_stmt(parser)
    return parse_expr_stmt(parser)


def finish_print_stmt(parser: Parser) -> Union[ast.AstPrintStmt, er.CompileError]:
    """
    Parse a print statement from the parser or return an error. Assumes that the "print" token has
    already been consumed.

    AstPrintStmt : "print" AstExpr? ";" ;
    """
    start = parser.prev().lexeme

    if parser.match(lx.TokenType.SEMICOLON):
        return ast.AstPrintStmt(None, er.SourceView.range(start, parser.prev().lexeme))

    expr = parse_expr(parser)
    if isinstance(expr, er.CompileError):
        return expr

    if not parser.match(lx.TokenType.SEMICOLON):
        return er.CompileError(
            message="missing ';' to end print statement",
            regions=[parser.prev().lexeme, parser.curr_region()],
        )

    return ast.AstPrintStmt(expr, er.SourceView.range(start, parser.prev().lexeme))


def finish_block_stmt(parser: Parser) -> Union[ast.AstBlockStmt, er.CompileError]:
    """
    Parse a block statement from the parser or return an error. Assumes that the opening brace has
    already been consumed.

    AstBlockStmt : "{" AstDecl* "}" ;
    """
    start = parser.prev().lexeme

    decls = []
    open_brace = parser.prev()
    while not parser.match(lx.TokenType.RIGHT_BRACE):
        if parser.done():
            return er.CompileError(
                message="unclosed '{'",
                regions=[open_brace.lexeme, parser.curr_region()],
            )
        decl = parse_decl(parser)
        if isinstance(decl, er.CompileError):
            return decl
        decls.append(decl)
    return ast.AstBlockStmt(decls, er.SourceView.range(start, parser.prev().lexeme))


def finish_if_stmt(parser: Parser) -> Union[ast.AstIfStmt, er.CompileError]:
    """
    Parse an if statement from the parser or return an error. Assumes that the "if" token has
    already been consumed.

    AstIfStmt : "if" "(" AstExpr ")" AstBlockStmt
                ( "else" "if" "(" AstExpr ")" AstBlockStmt )*
                ( "else" AstBlockStmt )?
              ;
    """
    start = parser.prev().lexeme

    def parse_cond() -> Union[Tuple[ast.AstExpr, ast.AstBlockStmt], er.CompileError]:
        if not parser.match(lx.TokenType.LEFT_PAREN):
            return er.CompileError(
                message="missing '(' to start condition", regions=[parser.curr_region()]
            )
        cond = parse_expr(parser)
        if isinstance(cond, er.CompileError):
            return cond
        if not parser.match(lx.TokenType.RIGHT_PAREN):
            return er.CompileError(
                message="missing ')' to end condition", regions=[parser.curr_region()]
            )
        if not parser.match(lx.TokenType.LEFT_BRACE):
            return er.CompileError(
                message="expected block after condition", regions=[parser.curr_region()]
            )
        block = finish_block_stmt(parser)
        if isinstance(block, er.CompileError):
            return block
        return cond, block

    if_pair = parse_cond()
    if isinstance(if_pair, er.CompileError):
        return if_pair
    elif_pairs = []
    else_block = None
    while parser.match(lx.TokenType.ELSE):
        if parser.match(lx.TokenType.IF):
            elif_pair = parse_cond()
            if isinstance(elif_pair, er.CompileError):
                return elif_pair
            elif_pairs.append(elif_pair)
        else:
            if not parser.match(lx.TokenType.LEFT_BRACE):
                return er.CompileError(
                    message="expected else block", regions=[parser.curr_region()]
                )
            else_block_ = finish_block_stmt(parser)
            if isinstance(else_block_, er.CompileError):
                return else_block_
            else_block = else_block_
            break
    return ast.AstIfStmt(
        if_pair,
        elif_pairs,
        else_block,
        er.SourceView.range(start, parser.prev().lexeme),
    )


def finish_while_stmt(parser: Parser) -> Union[ast.AstWhileStmt, er.CompileError]:
    """
    Parse a while statement from the parser or return an error. Assumes the "while" token has
    already been consumed.

    AstWhileStmt : "while" ( "(" AstExpr ")" )? AstBlockStmt ;
    """
    start = parser.prev().lexeme

    cond = None
    if parser.match(lx.TokenType.LEFT_PAREN):
        cond_ = parse_expr(parser)
        if isinstance(cond_, er.CompileError):
            return cond_
        cond = cond_
        if not parser.match(lx.TokenType.RIGHT_PAREN):
            return er.CompileError(
                message="missing ')' to end condition", regions=[parser.curr_region()]
            )
    if not parser.match(lx.TokenType.LEFT_BRACE):
        return er.CompileError(message="expected block", regions=[parser.curr_region()])
    block = finish_block_stmt(parser)
    if isinstance(block, er.CompileError):
        return block
    return ast.AstWhileStmt(
        cond, block, er.SourceView.range(start, parser.prev().lexeme)
    )


def finish_return_stmt(parser: Parser) -> Union[ast.AstReturnStmt, er.CompileError]:
    """
    Parse a return statement from the parser or return an error. Assumes the "return" token has
    already been consumed.

    AstReturnStmt : "return" AstExpr? ";" ;
    """
    return_token = parser.prev()
    expr = None
    if not parser.match(lx.TokenType.SEMICOLON):
        expr_ = parse_expr(parser)
        if isinstance(expr_, er.CompileError):
            return expr_
        expr = expr_
        if not parser.match(lx.TokenType.SEMICOLON):
            return er.CompileError(
                message="missing ';' to end return statement",
                regions=[parser.prev().lexeme, parser.curr_region()],
            )
    region = er.SourceView.range(return_token.lexeme, parser.prev().lexeme)
    return ast.AstReturnStmt(expr, region)


def parse_expr_stmt(parser: Parser) -> Union[ast.AstExprStmt, er.CompileError]:
    """
    Parse an expression statement from the parser or return an error.

    AstExprStmt : AstExpr ";" ;
    """
    expr = parse_expr(parser)
    if isinstance(expr, er.CompileError):
        return expr
    if not parser.match(lx.TokenType.SEMICOLON):
        return er.CompileError(
            message="missing ';' to end expression statement",
            regions=[parser.prev().lexeme, parser.curr_region()],
        )
    return ast.AstExprStmt(expr, er.SourceView.range(expr.region, parser.prev().lexeme))


def parse_type(parser: Parser) -> Union[ast.AstType, er.CompileError]:
    """
    Parse a type from the parser or return an error.

    AstType : ( "(" AstType ")" | AstFuncType | AstAtomType ) ( "?" )? ;
    """
    if parser.match(lx.TokenType.LEFT_PAREN):
        start = parser.prev().lexeme
        result = parse_type(parser)
        if isinstance(result, er.CompileError):
            return result
        if not parser.match(lx.TokenType.RIGHT_PAREN):
            return er.CompileError(
                message="missing ')' to end type grouping",
                regions=[parser.curr_region()],
            )
        result.region = er.SourceView.range(start, parser.prev().lexeme)
        return result

    if parser.match(lx.TokenType.FUNC):
        result = finish_func_type(parser)
    else:
        result = parse_atom_type(parser)

    if isinstance(result, er.CompileError):
        return result

    if parser.match(lx.TokenType.QUESTION_MARK):
        result = ast.AstOptionalType(
            result, er.SourceView.range(result.region, parser.prev().lexeme)
        )
    return result


def finish_func_type(parser: Parser) -> Union[ast.AstFuncType, er.CompileError]:
    """
    Parse a function type from the parser or return an error. Assumes that the "func" token has
    already been consumed.

    AstFuncType : "func" "(" ( AstType ( "," AstType )* )? ")" AstType ;
    """
    start = parser.prev().lexeme
    if not parser.match(lx.TokenType.LEFT_PAREN):
        return er.CompileError(
            message="missing '(' to begin parameter types",
            regions=[parser.curr_region()],
        )
    params = parse_tuple(parser, parse_type)
    if isinstance(params, er.CompileError):
        return params
    return_type = parse_type(parser)
    if isinstance(return_type, er.CompileError):
        return return_type
    region = er.SourceView.range(start, parser.prev().lexeme)
    return ast.AstFuncType(params, return_type, region)


def parse_atom_type(parser: Parser) -> Union[ast.AstAtomType, er.CompileError]:
    """
    Parse an atom type from the parser or return an error.

    AstAtomType : IDENTIFIER | "void" ;
    """
    token = parse_token(parser, [lx.TokenType.IDENTIFIER, lx.TokenType.VOID])
    if token is None:
        return er.CompileError(message="expected type", regions=[parser.curr_region()])
    return ast.AstAtomType(token)


def finish_unary_expr(parser: Parser) -> Union[ast.AstExpr, er.CompileError]:
    """
    Parse a unary expression from the parser or return an error. Assumes that the operator token
    has already been consumed.
    """
    operator = parser.prev()
    target = parse_expr(parser, precedence=Precedence.UNARY)
    if isinstance(target, er.CompileError):
        return target
    region = er.SourceView.range(operator.lexeme, target.region)
    return ast.AstUnaryExpr(operator, target, region)


def finish_binary_expr(
    parser: Parser, lhs: ast.AstExpr
) -> Union[ast.AstExpr, er.CompileError]:
    """
    Parse a binary expression from the parser or return an error. Assumes the operator token has
    already been consumed, and takes the lhs expression as a parameter.
    """
    operator = parser.prev()
    prec = PRATT_TABLE[operator.kind].precedence
    rhs = parse_expr(parser, prec.next())
    if isinstance(rhs, er.CompileError):
        return rhs
    region = er.SourceView.range(lhs.region, rhs.region)
    return ast.AstBinaryExpr(operator, lhs, rhs, region)


def finish_call_expr(
    parser: Parser, lhs: ast.AstExpr
) -> Union[ast.AstExpr, er.CompileError]:
    """
    Parse a function call expression from the parser or return an error. Assumes that the open
    parenthesis has already been consumed, and takes the function expression as a parameter.
    """
    args = parse_tuple(parser, parse_expr)
    if isinstance(args, er.CompileError):
        return args
    region = er.SourceView.range(lhs.region, parser.prev().lexeme)
    return ast.AstCallExpr(lhs, args, region)


def finish_int_expr(parser: Parser) -> Union[ast.AstIntExpr, er.CompileError]:
    """
    Parse an int expression from the parser or return an error. Assumes that the literal token has
    already been consumed.
    """
    token = parser.prev()
    val = int(str(token)[:-1])
    if val > 2 ** 31 - 1:
        return er.CompileError(
            message="literal value is too large", regions=[token.lexeme]
        )
    return ast.AstIntExpr(token)


def finish_num_expr(parser: Parser) -> Union[ast.AstNumExpr, er.CompileError]:
    """
    Parse a num expression from the parser or return an error. Assumes that the literal token has
    already been consumed.
    """
    token = parser.prev()
    if "." in str(token):
        decimals = str(token).split(".")[1]
        if len(decimals) > 7:
            return er.CompileError(
                message="too many decimal palces, precision up to only 7 is supported",
                regions=[token.lexeme],
            )
    return ast.AstNumExpr(token)


def finish_str_expr(parser: Parser) -> Union[ast.AstStrExpr, er.CompileError]:
    """
    Parse a str expression from the parser or return an error. Assumes that the literal token has
    already been consumed.
    """
    token = parser.prev()
    if len(str(token)) > 512 + 2:
        return er.CompileError(
            message="string literal too long, max length is 512", regions=[token.lexeme]
        )
    return ast.AstStrExpr(token)


def finish_ident_expr(parser: Parser) -> Union[ast.AstIdentExpr, er.CompileError]:
    """
    Parse an identifier expression from the parser or return an error. Assumes that the identifier
    has already been consumed.
    """
    return ast.AstIdentExpr(parser.prev())


def finish_bool_expr(parser: Parser) -> Union[ast.AstBoolExpr, er.CompileError]:
    """
    Parse a bool expression from the parser or return an error. Assumes that the literal token has
    already been consumed.
    """
    return ast.AstBoolExpr(parser.prev())


def finish_nil_expr(parser: Parser) -> Union[ast.AstNilExpr, er.CompileError]:
    """
    Parse a nil expression from the parser or return an error. Assumes that the literal token has
    already been consumed.
    """
    return ast.AstNilExpr(parser.prev())


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

    def __lt__(self, other: "Precedence") -> bool:
        return int(self.value) < int(other.value)

    def __le__(self, other: "Precedence") -> bool:
        return int(self.value) <= int(other.value)

    def __gt__(self, other: "Precedence") -> bool:
        return int(self.value) > int(other.value)

    def __ge__(self, other: "Precedence") -> bool:
        return int(self.value) >= int(other.value)

    def next(self) -> "Precedence":
        """
        Returns the next highest precedence.
        """
        next_value = self.value + 1
        return Precedence(min(next_value, Precedence.MAX.value))


PrefixRule = Callable[[Parser], Union[ast.AstExpr, er.CompileError]]
InfixRule = Callable[[Parser, ast.AstExpr], Union[ast.AstExpr, er.CompileError]]


class PrattRule(NamedTuple):
    """
    Represents a rule for parsing a token within an expression.
    """

    prefix: Optional[PrefixRule] = None
    infix: Optional[InfixRule] = None
    precedence: Precedence = Precedence.NONE


PRATT_TABLE: DefaultDict[lx.TokenType, PrattRule] = collections.defaultdict(
    PrattRule,
    {
        lx.TokenType.LEFT_PAREN: PrattRule(
            infix=finish_call_expr, precedence=Precedence.CALL
        ),
        lx.TokenType.MINUS: PrattRule(
            prefix=finish_unary_expr,
            infix=finish_binary_expr,
            precedence=Precedence.TERM,
        ),
        lx.TokenType.PLUS: PrattRule(
            infix=finish_binary_expr, precedence=Precedence.TERM
        ),
        lx.TokenType.STAR: PrattRule(
            infix=finish_binary_expr, precedence=Precedence.FACTOR
        ),
        lx.TokenType.SLASH: PrattRule(
            infix=finish_binary_expr, precedence=Precedence.FACTOR
        ),
        lx.TokenType.OR: PrattRule(infix=finish_binary_expr, precedence=Precedence.OR),
        lx.TokenType.AND: PrattRule(
            infix=finish_binary_expr, precedence=Precedence.AND
        ),
        lx.TokenType.DOUBLE_EQUALS: PrattRule(
            infix=finish_binary_expr, precedence=Precedence.EQUALITY
        ),
        lx.TokenType.NOT_EQUALS: PrattRule(
            infix=finish_binary_expr, precedence=Precedence.EQUALITY
        ),
        lx.TokenType.STR_LITERAL: PrattRule(prefix=finish_str_expr),
        lx.TokenType.NUM_LITERAL: PrattRule(prefix=finish_num_expr),
        lx.TokenType.INT_LITERAL: PrattRule(prefix=finish_int_expr),
        lx.TokenType.IDENTIFIER: PrattRule(prefix=finish_ident_expr),
        lx.TokenType.TRUE: PrattRule(prefix=finish_bool_expr),
        lx.TokenType.FALSE: PrattRule(prefix=finish_bool_expr),
        lx.TokenType.NIL: PrattRule(prefix=finish_nil_expr),
    },
)


def parse_prefix(parser: Parser) -> Union[ast.AstExpr, er.CompileError]:
    """
    Parses a prefix expression from a Parser using a pratt table.
    """
    start_token = parser.advance()
    if not start_token:
        return er.CompileError(
            message="unexpected EOF; expected expression",
            regions=[parser.curr_region()],
        )
    rule = PRATT_TABLE[start_token.kind]
    if not rule.prefix:
        return er.CompileError(
            message="unexpected token; expected expression",
            regions=[start_token.lexeme],
        )
    return rule.prefix(parser)


def parse_infix(
    parser: Parser, expr: ast.AstExpr, precedence: Precedence
) -> Optional[Union[ast.AstExpr, er.CompileError]]:
    """
    Given an initial expression and precedence parses an infix expression from a Parser using a
    pratt table. If there are no infix extensions bound by the precedence returns None.
    """
    # See if there's an infix token
    # If not, there's no expression to parse
    token = parser.curr()
    if not token:
        return None
    rule = PRATT_TABLE[token.kind]
    if not rule.infix:
        return None
    # While the infix token is bound by the precedence of the expression
    while rule.precedence >= precedence:
        # Advance past the infix token and run its rule
        parser.advance()
        if rule.infix:  # Should always be true but mypy can't tell
            expr_ = rule.infix(parser, expr)
            if isinstance(expr_, er.CompileError):
                return expr_
            expr = expr_
        # See if there's another infix token
        # If not, the expression is finished
        token = parser.curr()
        if not token:
            break
        rule = PRATT_TABLE[token.kind]
        if not rule.infix:
            break
    return expr


def parse_expr(
    parser: Parser, precedence: Precedence = Precedence.ASSIGNMENT
) -> Union[ast.AstExpr, er.CompileError]:
    """
    Parses an expression bound by a given precedence from a Parser using a pratt table.
    """
    prefix_expr = parse_prefix(parser)
    if isinstance(prefix_expr, er.CompileError):
        return prefix_expr
    infix_parse = parse_infix(parser, prefix_expr, precedence)
    if infix_parse is None:
        return prefix_expr
    return infix_parse
