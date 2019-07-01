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
    TypeVar,
    Generic,
)

import enum
import collections

import clr.errors as er
import clr.lexer as lx
import clr.ast as ast


T = TypeVar("T")  # pylint: disable=invalid-name
Result = Union[T, er.CompileError]


def parse_tokens(tokens: Sequence[lx.Token]) -> Result[ast.Ast]:
    """
    Parses an ast from a list of tokens.
    """
    return parse_ast(Parser(tokens))


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


def parse_ast(parser: Parser) -> Result[ast.Ast]:
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
    return ast.Ast(decls, er.SourceView.range(decls[0].region, decls[-1].region))


def parse_token(parser: Parser, kinds: Iterable[lx.TokenType]) -> Optional[lx.Token]:
    """
    Parses a token from a given iterable of token types to check, and if none of the types match
    returns None.
    """
    for kind in kinds:
        if parser.match(kind):
            return parser.prev()
    return None


def parse_decl(parser: Parser) -> Result[ast.AstDecl]:
    """
    Parse a declaration from the parser or return an error.

    AstDecl : AstValueDecl | AstFuncDecl | AstStmt ;
    """
    if parser.match(lx.TokenType.VAL):
        return finish_value_decl(parser)
    if parser.match(lx.TokenType.FUNC):
        return finish_func_decl(parser)
    return parse_stmt(parser)


def parse_binding(parser: Parser) -> Result[ast.AstBinding]:
    """
    Parse a value binding from the parser or return an error.

    AstBinding : IDENTIFIER ;
    """
    token = parse_token(parser, [lx.TokenType.IDENTIFIER])
    if token is None:
        return er.CompileError(
            message="expected value name", regions=[parser.curr_region()]
        )
    return ast.AstBinding(str(token), token.lexeme)


def finish_value_decl(parser: Parser) -> Result[ast.AstValueDecl]:
    """
    Parse a value declaration from the parser or return an error. Assumes that the "val" token has
    already been consumed.

    AstValueDecl : "val" AstBinding ( ", " AstBinding )* ":" AstType? "=" AstExpr ";" ;
    """
    start = parser.prev().lexeme
    bindings = finish_tuple(parser, parse_binding, end=lx.TokenType.COLON)
    if isinstance(bindings, er.CompileError):
        return bindings
    # There has to be at least one
    if not bindings:
        return er.CompileError(
            message="expected value name", regions=[parser.prev().lexeme]
        )

    val_type = None
    if not parser.match(lx.TokenType.EQUALS):
        val_type_ = parse_type(parser)
        if isinstance(val_type_, er.CompileError):
            return val_type_
        val_type = val_type_
        if not parser.match(lx.TokenType.EQUALS):
            return er.CompileError(
                message="expected '=' for value initializer",
                regions=[parser.curr_region()],
            )

    expr = parse_expr(parser)
    if isinstance(expr, er.CompileError):
        return expr

    if not parser.match(lx.TokenType.SEMICOLON):
        return er.CompileError(
            message="expected ';' to end value initializer",
            regions=[parser.prev().lexeme, parser.curr_region()],
        )

    region = er.SourceView.range(start, parser.prev().lexeme)
    return ast.AstValueDecl(bindings, val_type, expr, region)


def finish_func_decl(parser: Parser) -> Result[ast.AstFuncDecl]:
    """
    Parse a function declaration from the parser or return an error. Assumes that the "func" token
    has already been consumed.

    AstFuncDecl : "func" IDENTIFIER "(" ( AstParam ( "," AstParam )* )? ")" AstType AstBlockStmt ;
    """
    start = parser.prev().lexeme
    binding = parse_binding(parser)
    if isinstance(binding, er.CompileError):
        return binding

    if not parser.match(lx.TokenType.LEFT_PAREN):
        return er.CompileError(
            message="expected '(' to begin parameters", regions=[parser.curr_region()]
        )

    params = finish_tuple(parser, parse_param)
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
    return ast.AstFuncDecl(binding, params, return_type, block, region)


def parse_param(parser: Parser) -> Result[ast.AstParam]:
    """
    Parse a parameter from the parser or return an error.

    AstParam : AstType IDENTIFIER ;
    """
    param_type = parse_type(parser, Precedence.TUPLE.next())  # Don't consume commas
    if isinstance(param_type, er.CompileError):
        return param_type
    param_ident = parse_token(parser, [lx.TokenType.IDENTIFIER])
    if param_ident is None:
        return er.CompileError(
            message="expected parameter name", regions=[parser.curr_region()]
        )
    return ast.AstParam(param_type, param_ident)


def finish_tuple(
    parser: Parser,
    parse_func: Callable[[Parser], Result[T]],
    end: lx.TokenType = lx.TokenType.RIGHT_PAREN,
) -> Result[List[T]]:
    """
    Given that the opening token has already been consumed, parse the elements of a tuple form
    `<opener> a,b,... <end>` into a list using a parameter function to parse each element. By
    default the end token is ')'.
    """
    opener = parser.prev()
    if parser.match(end):
        return []

    first = parse_func(parser)
    if isinstance(first, er.CompileError):
        return first
    pairs = [first]

    while not parser.match(end):
        if parser.done():
            return er.CompileError(
                message=f"expected '{end}' before EOF", regions=[opener.lexeme]
            )
        if not parser.match(lx.TokenType.COMMA):
            return er.CompileError(
                f"expected ',' delimiter or '{end}'", [parser.curr_region()]
            )
        elem = parse_func(parser)
        if isinstance(elem, er.CompileError):
            return elem
        pairs.append(elem)
    return pairs


def parse_stmt(parser: Parser) -> Result[ast.AstStmt]:
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


def finish_print_stmt(parser: Parser) -> Result[ast.AstPrintStmt]:
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
            message="expected ';' to end print statement",
            regions=[parser.prev().lexeme, parser.curr_region()],
        )

    return ast.AstPrintStmt(expr, er.SourceView.range(start, parser.prev().lexeme))


def finish_block_stmt(parser: Parser) -> Result[ast.AstBlockStmt]:
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


def finish_if_stmt(parser: Parser) -> Result[ast.AstIfStmt]:
    """
    Parse an if statement from the parser or return an error. Assumes that the "if" token has
    already been consumed.

    AstIfStmt : "if" "(" AstExpr ")" AstBlockStmt
                ( "else" "if" "(" AstExpr ")" AstBlockStmt )*
                ( "else" AstBlockStmt )?
              ;
    """
    start = parser.prev().lexeme

    def parse_cond() -> Result[Tuple[ast.AstExpr, ast.AstBlockStmt]]:
        if not parser.match(lx.TokenType.LEFT_PAREN):
            return er.CompileError(
                message="expected '(' to start condition",
                regions=[parser.curr_region()],
            )
        cond = parse_expr(parser)
        if isinstance(cond, er.CompileError):
            return cond
        if not parser.match(lx.TokenType.RIGHT_PAREN):
            return er.CompileError(
                message="expected ')' to end condition", regions=[parser.curr_region()]
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


def finish_while_stmt(parser: Parser) -> Result[ast.AstWhileStmt]:
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
                message="expected ')' to end condition", regions=[parser.curr_region()]
            )
    if not parser.match(lx.TokenType.LEFT_BRACE):
        return er.CompileError(message="expected block", regions=[parser.curr_region()])
    block = finish_block_stmt(parser)
    if isinstance(block, er.CompileError):
        return block
    return ast.AstWhileStmt(
        cond, block, er.SourceView.range(start, parser.prev().lexeme)
    )


def finish_return_stmt(parser: Parser) -> Result[ast.AstReturnStmt]:
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
                message="expected ';' to end return statement",
                regions=[parser.prev().lexeme, parser.curr_region()],
            )
    region = er.SourceView.range(return_token.lexeme, parser.prev().lexeme)
    return ast.AstReturnStmt(expr, region)


def parse_expr_stmt(parser: Parser) -> Result[ast.AstExprStmt]:
    """
    Parse an expression statement from the parser or return an error.

    AstExprStmt : AstExpr ";" ;
    """
    expr = parse_expr(parser)
    if isinstance(expr, er.CompileError):
        return expr
    if not parser.match(lx.TokenType.SEMICOLON):
        return er.CompileError(
            message="expected ';' to end expression statement",
            regions=[parser.prev().lexeme, parser.curr_region()],
        )
    return ast.AstExprStmt(expr, er.SourceView.range(expr.region, parser.prev().lexeme))


def finish_group_type(parser: Parser) -> Result[ast.AstType]:
    """
    Parse a grouped type from the parser or return an error. Assumes that the opening parenthesis
    has already been consumed.
    """
    start = parser.prev().lexeme
    result = parse_type(parser)
    if isinstance(result, er.CompileError):
        return result
    if not parser.match(lx.TokenType.RIGHT_PAREN):
        return er.CompileError(
            message="expected ')' to end type grouping",
            regions=[start, parser.curr_region()],
        )
    result.region = er.SourceView.range(start, parser.prev().lexeme)
    return result


def finish_optional_type(parser: Parser, target: ast.AstType) -> Result[ast.AstType]:
    """
    Parse an optional type from the parser, given the target type. Assumes that the '?' token has
    already been consumed.
    """
    return ast.AstOptionalType(
        target, er.SourceView.range(target.region, parser.prev().lexeme)
    )


def finish_union_type(parser: Parser, lhs: ast.AstType) -> Result[ast.AstType]:
    """
    Parse a union type from the parser, given the left side. Assumes that the '|' token has already
    been consumed.
    """
    rhs = parse_many_infix(parser, lx.TokenType.VERT, TYPE_TABLE, expected="type")
    if isinstance(rhs, er.CompileError):
        return rhs
    types = [lhs] + rhs
    region = er.SourceView.range(types[0].region, types[-1].region)
    return ast.AstUnionType(types, region)


def finish_tuple_type(parser: Parser, lhs: ast.AstType) -> Result[ast.AstType]:
    """
    Parse a tuple type from the parser, given the left side. Assumes that the ',' token has already
    been consumed.
    """
    rhs = parse_many_infix(parser, lx.TokenType.COMMA, TYPE_TABLE, expected="type")
    if isinstance(rhs, er.CompileError):
        return rhs
    types = [lhs] + rhs
    region = er.SourceView.range(types[0].region, types[-1].region)
    return ast.AstTupleType(tuple(types), region)


def finish_func_type(parser: Parser) -> Result[ast.AstFuncType]:
    """
    Parse a function type from the parser or return an error. Assumes that the "func" token has
    already been consumed.
    """
    start = parser.prev().lexeme
    if not parser.match(lx.TokenType.LEFT_PAREN):
        return er.CompileError(
            message="expected '(' to begin parameter types",
            regions=[parser.curr_region()],
        )

    params = finish_tuple(parser, lambda p: parse_type(p, Precedence.TUPLE.next()))
    if isinstance(params, er.CompileError):
        return params
    return_type = parse_type(parser)
    if isinstance(return_type, er.CompileError):
        return return_type
    region = er.SourceView.range(start, parser.prev().lexeme)
    return ast.AstFuncType(params, return_type, region)


def finish_ident_type(parser: Parser) -> Result[ast.AstIdentType]:
    """
    Parse an identifier type from the parser or return an error. Assumes that the identifier token
    has already been consumed.
    """
    return ast.AstIdentType(parser.prev())


def finish_void_type(parser: Parser) -> Result[ast.AstVoidType]:
    """
    Parse a void type from the parser or return an error. Assumes that the "void" token has already
    been consumed.
    """
    return ast.AstVoidType(parser.prev())


def finish_group_expr(parser: Parser) -> Result[ast.AstExpr]:
    """
    Parse a grouped expression from the parser or return an error. Assumes that the opening
    parenthesis has already been consumed.
    """
    opener = parser.prev()
    expr = parse_expr(parser)
    if isinstance(expr, er.CompileError):
        return expr
    if not parser.match(lx.TokenType.RIGHT_PAREN):
        return er.CompileError(
            message="expected ')' to finish expression",
            regions=[opener.lexeme, expr.region],
        )
    expr.region = er.SourceView.range(opener.lexeme, parser.prev().lexeme)
    return expr


def finish_unary_expr(parser: Parser) -> Result[ast.AstExpr]:
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


def finish_binary_expr(parser: Parser, lhs: ast.AstExpr) -> Result[ast.AstExpr]:
    """
    Parse a binary expression from the parser or return an error. Assumes the operator token has
    already been consumed, and takes the lhs expression as a parameter.
    """
    operator = parser.prev()
    prec = EXPR_TABLE[operator.kind].precedence
    # The .next() makes it left associative
    rhs = parse_expr(parser, prec.next())
    if isinstance(rhs, er.CompileError):
        return rhs
    region = er.SourceView.range(lhs.region, rhs.region)
    return ast.AstBinaryExpr(operator, lhs, rhs, region)


def parse_alias(parser: Parser) -> Result[Tuple[ast.AstExpr, ast.AstBinding]]:
    """
    Parse an alias from the parser or return an error.

    ALIAS : AstExpr "as" AstBinding | AstIdentExpr ;
    """
    target = parse_expr(parser)
    if isinstance(target, er.CompileError):
        return target
    if parser.match(lx.TokenType.AS):
        binding = parse_binding(parser)
        if isinstance(binding, er.CompileError):
            return binding
    else:
        if isinstance(target, ast.AstIdentExpr):
            # "<ident>" is syntax sugar for "<ident> as <ident>"
            binding = ast.AstBinding(target.name, target.region)
        else:
            return er.CompileError(
                message=f"missing binding for non-identifier target expression",
                regions=[target.region, parser.curr_region()],
            )
    return target, binding


def parse_case(
    parser: Parser
) -> Result[Union[Tuple[ast.AstType, ast.AstExpr], ast.AstExpr]]:
    """
    Parse a type case from the parser or return an error.
    """
    if parser.match(lx.TokenType.ELSE):
        # Parse fallback
        if not parser.match(lx.TokenType.COLON):
            return er.CompileError(
                message="expected ':' before fallback value",
                regions=[parser.curr_region()],
            )
        fallback = parse_expr(parser, precedence=Precedence.TUPLE.next())
        if isinstance(fallback, er.CompileError):
            return fallback
        if not parser.match(lx.TokenType.RIGHT_BRACE):
            return er.CompileError(
                message="expected '}' after fallback case",
                regions=[parser.curr_region()],
            )
        return fallback
    # Parse case
    case_type = parse_type(parser)
    if isinstance(case_type, er.CompileError):
        return case_type
    if not parser.match(lx.TokenType.COLON):
        return er.CompileError(
            message="expected ':' before case value", regions=[parser.curr_region()]
        )
    case_value = parse_expr(parser, precedence=Precedence.TUPLE.next())
    if isinstance(case_value, er.CompileError):
        return case_value
    return case_type, case_value


def finish_case_expr(parser: Parser) -> Result[ast.AstExpr]:
    """
    Parse a case expression from the parser or return an error. Assumes that the "case" token has
    already been consumed.
    """
    start = parser.prev().lexeme
    alias = parse_alias(parser)
    if isinstance(alias, er.CompileError):
        return alias

    if not parser.match(lx.TokenType.LEFT_BRACE):
        return er.CompileError(
            message="expected '{' to open case block", regions=[parser.curr_region()]
        )
    opener = parser.prev()
    cases: List[Tuple[ast.AstType, ast.AstExpr]] = []
    fallback: Result[Optional[ast.AstExpr]] = None
    while not parser.match(lx.TokenType.RIGHT_BRACE):
        if parser.done():
            return er.CompileError(
                message="unclosed '{'", regions=[opener.lexeme, parser.curr_region()]
            )
        if cases and not parser.match(lx.TokenType.COMMA):
            return er.CompileError(
                message=f"expected ',' to delimit cases", regions=[parser.curr_region()]
            )
        case = parse_case(parser)
        if isinstance(case, er.CompileError):
            return case
        if isinstance(case, ast.AstExpr):
            fallback = case
            break
        cases.append(case)

    if isinstance(fallback, er.CompileError):
        return fallback

    region = er.SourceView.range(start, parser.prev().lexeme)
    return ast.AstCaseExpr(*alias, cases, fallback, region)


def finish_call_expr(parser: Parser, lhs: ast.AstExpr) -> Result[ast.AstExpr]:
    """
    Parse a function call expression from the parser or return an error. Assumes that the open
    parenthesis has already been consumed, and takes the function expression as a parameter.
    """
    args = finish_tuple(
        parser, lambda parser: parse_expr(parser, Precedence.TUPLE.next())
    )
    if isinstance(args, er.CompileError):
        return args
    region = er.SourceView.range(lhs.region, parser.prev().lexeme)
    return ast.AstCallExpr(lhs, args, region)


def finish_tuple_expr(parser: Parser, lhs: ast.AstExpr) -> Result[ast.AstExpr]:
    """
    Parse a tuple expression from the parser or return an error. Assumes that the comma has already
    been consumed, and takes the lhs expression as a parameter.
    """
    rhs = parse_many_infix(
        parser, lx.TokenType.COMMA, EXPR_TABLE, expected="expression"
    )
    if isinstance(rhs, er.CompileError):
        return rhs
    exprs = [lhs] + rhs
    region = er.SourceView.range(exprs[0].region, exprs[-1].region)
    return ast.AstTupleExpr(tuple(exprs), region)


def finish_lambda_expr(parser: Parser) -> Result[ast.AstExpr]:
    """
    Parse a lambda expression from the parser or return an error. Assumes that the "func" token has
    already been consumed.
    """
    start = parser.prev().lexeme
    if not parser.match(lx.TokenType.LEFT_PAREN):
        return er.CompileError(
            message=f"expected '(' to start parameters", regions=[parser.curr_region()]
        )
    params = finish_tuple(parser, parse_param)
    if isinstance(params, er.CompileError):
        return params
    value = parse_expr(parser, precedence=Precedence.TUPLE.next())
    if isinstance(value, er.CompileError):
        return value
    region = er.SourceView.range(start, parser.prev().lexeme)
    return ast.AstLambdaExpr(params, value, region)


def finish_int_expr(parser: Parser) -> Result[ast.AstIntExpr]:
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


def finish_num_expr(parser: Parser) -> Result[ast.AstNumExpr]:
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


def finish_str_expr(parser: Parser) -> Result[ast.AstStrExpr]:
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


def finish_ident_expr(parser: Parser) -> Result[ast.AstIdentExpr]:
    """
    Parse an identifier expression from the parser or return an error. Assumes that the identifier
    has already been consumed.
    """
    return ast.AstIdentExpr(parser.prev())


def finish_bool_expr(parser: Parser) -> Result[ast.AstBoolExpr]:
    """
    Parse a bool expression from the parser or return an error. Assumes that the literal token has
    already been consumed.
    """
    return ast.AstBoolExpr(parser.prev())


def finish_nil_expr(parser: Parser) -> Result[ast.AstNilExpr]:
    """
    Parse a nil expression from the parser or return an error. Assumes that the literal token has
    already been consumed.
    """
    return ast.AstNilExpr(parser.prev())


@enum.unique
class Precedence(enum.Enum):
    """
    Enumerates the different precedences of postfix expressions. The values respect the ordering.
    """

    NONE = 0
    ASSIGNMENT = 1
    TUPLE = 2
    OR = 3
    AND = 4
    EQUALITY = 5
    COMPARISON = 6
    TERM = 7
    FACTOR = 8
    UNARY = 9
    CALL = 10
    MAX = 11

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


PrefixRule = Callable[[Parser], Result[T]]
PostfixRule = Callable[[Parser, T], Result[T]]


# https://github.com/python/mypy/issues/685
class PrattRule(Generic[T]):  # pylint: disable=too-few-public-methods
    """
    Represents a pratt rule for a token type.
    """

    def __init__(
        self,
        prefix: Optional[PrefixRule[T]] = None,
        postfix: Optional[PostfixRule[T]] = None,
        precedence: Precedence = Precedence.NONE,
    ) -> None:
        self.prefix = prefix
        self.postfix = postfix
        self.precedence = precedence


PrattTable = DefaultDict[lx.TokenType, PrattRule[T]]

TYPE_TABLE: PrattTable[ast.AstType] = collections.defaultdict(
    PrattRule,
    {
        lx.TokenType.IDENTIFIER: PrattRule(prefix=finish_ident_type),
        lx.TokenType.VOID: PrattRule(prefix=finish_void_type),
        lx.TokenType.FUNC: PrattRule(prefix=finish_func_type),
        lx.TokenType.LEFT_PAREN: PrattRule(prefix=finish_group_type),
        lx.TokenType.QUESTION_MARK: PrattRule(
            postfix=finish_optional_type, precedence=Precedence.CALL
        ),
        lx.TokenType.VERT: PrattRule(
            postfix=finish_union_type, precedence=Precedence.TERM
        ),
        lx.TokenType.COMMA: PrattRule(
            postfix=finish_tuple_type, precedence=Precedence.TUPLE
        ),
    },
)

EXPR_TABLE: PrattTable[ast.AstExpr] = collections.defaultdict(
    PrattRule,
    {
        lx.TokenType.FUNC: PrattRule(prefix=finish_lambda_expr),
        lx.TokenType.LEFT_PAREN: PrattRule(
            prefix=finish_group_expr,
            postfix=finish_call_expr,
            precedence=Precedence.CALL,
        ),
        lx.TokenType.COMMA: PrattRule(
            postfix=finish_tuple_expr, precedence=Precedence.TUPLE
        ),
        lx.TokenType.MINUS: PrattRule(
            prefix=finish_unary_expr,
            postfix=finish_binary_expr,
            precedence=Precedence.TERM,
        ),
        lx.TokenType.PLUS: PrattRule(
            postfix=finish_binary_expr, precedence=Precedence.TERM
        ),
        lx.TokenType.STAR: PrattRule(
            postfix=finish_binary_expr, precedence=Precedence.FACTOR
        ),
        lx.TokenType.SLASH: PrattRule(
            postfix=finish_binary_expr, precedence=Precedence.FACTOR
        ),
        lx.TokenType.OR: PrattRule(
            postfix=finish_binary_expr, precedence=Precedence.OR
        ),
        lx.TokenType.AND: PrattRule(
            postfix=finish_binary_expr, precedence=Precedence.AND
        ),
        lx.TokenType.CASE: PrattRule(
            prefix=finish_case_expr, precedence=Precedence.CALL
        ),
        lx.TokenType.DOUBLE_EQUALS: PrattRule(
            postfix=finish_binary_expr, precedence=Precedence.EQUALITY
        ),
        lx.TokenType.NOT_EQUALS: PrattRule(
            postfix=finish_binary_expr, precedence=Precedence.EQUALITY
        ),
        lx.TokenType.LESS: PrattRule(
            postfix=finish_binary_expr, precedence=Precedence.COMPARISON
        ),
        lx.TokenType.GREATER: PrattRule(
            postfix=finish_binary_expr, precedence=Precedence.COMPARISON
        ),
        lx.TokenType.LESS_EQUALS: PrattRule(
            postfix=finish_binary_expr, precedence=Precedence.COMPARISON
        ),
        lx.TokenType.GREATER_EQUALS: PrattRule(
            postfix=finish_binary_expr, precedence=Precedence.COMPARISON
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


def parse_prefix(parser: Parser, table: PrattTable[T], expected: str) -> Result[T]:
    """
    Parses a prefix element from a Parser using a pratt table.
    """
    start_token = parser.advance()
    if not start_token:
        return er.CompileError(
            message=f"unexpected EOF; expected {expected}",
            regions=[parser.curr_region()],
        )
    rule = table[start_token.kind]
    if not rule.prefix:
        return er.CompileError(
            message=f"unexpected token; expected {expected}",
            regions=[start_token.lexeme],
        )
    return rule.prefix(parser)


def parse_postfix(
    parser: Parser, parse: T, precedence: Precedence, table: PrattTable[T]
) -> Optional[Result[T]]:
    """
    Given an initial parse and precedence parses postfix elements from a Parser using a
    pratt table. If there are no postfix extensions bound by the precedence returns None.
    """
    # See if there's a postfix token
    # If not, there's no expression to parse
    token = parser.curr()
    if not token:
        return None
    rule = table[token.kind]
    if not rule.postfix:
        return None
    # While the postfix token is bound by the precedence of the expression
    while rule.precedence >= precedence:
        # Advance past the postfix token and run its rule
        parser.advance()
        if rule.postfix:  # Should always be true but mypy can't tell
            parse_ = rule.postfix(parser, parse)
            if isinstance(parse_, er.CompileError):
                return parse_
            parse = parse_
        # See if there's another postfix token
        # If not, the expression is finished
        token = parser.curr()
        if not token:
            break
        rule = table[token.kind]
        if not rule.postfix:
            break
    return parse


def pratt_parse(
    parser: Parser, precedence: Precedence, table: PrattTable[T], expected: str
) -> Result[T]:
    """
    Runs the pratt parsing algorithm once given a pratt table.
    """
    prefix_expr = parse_prefix(parser, table, expected)
    if isinstance(prefix_expr, er.CompileError):
        return prefix_expr
    postfix_parse = parse_postfix(parser, prefix_expr, precedence, table)
    if postfix_parse is None:
        return prefix_expr
    return postfix_parse


def parse_many_infix(
    parser: Parser, operator: lx.TokenType, table: PrattTable[T], expected: str
) -> Result[List[T]]:
    """
    Runs a postfix rule repeatedly while the same operator is used.
    """
    precedence = table[parser.prev().kind].precedence.next()
    first = pratt_parse(parser, precedence, table, expected)
    if isinstance(first, er.CompileError):
        return first

    result = [first]
    while parser.match(operator):
        next_elem = pratt_parse(parser, precedence, table, expected)
        if isinstance(next_elem, er.CompileError):
            return next_elem
        result.append(next_elem)

    return result


def parse_type(
    parser: Parser, precedence: Precedence = Precedence.NONE.next()
) -> Result[ast.AstType]:
    """
    Parse a type from the parser bound by a given precedence.
    """
    result = pratt_parse(parser, precedence, TYPE_TABLE, expected="type")
    return result


def parse_expr(
    parser: Parser, precedence: Precedence = Precedence.NONE.next()
) -> Result[ast.AstExpr]:
    """
    Parse an expression from the parser bound by a given precedence.
    """
    result = pratt_parse(parser, precedence, EXPR_TABLE, expected="expression")
    return result
