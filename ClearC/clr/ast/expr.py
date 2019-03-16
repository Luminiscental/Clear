from enum import Enum
from collections import defaultdict, namedtuple
from clr.tokens import TokenType, token_info
from clr.errors import parse_error
from clr.ast.resolve import TypeAnnotation
from clr.constants import ClrStr, ClrNum, ClrInt


class Precedence(Enum):

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
    PRIMARY = 10

    def __lt__(self, other):
        return self.__cmp__(other) < 0

    def __le__(self, other):
        return self.__cmp__(other) <= 0

    def __gt__(self, other):
        return self.__cmp__(other) > 0

    def __ge__(self, other):
        return self.__cmp__(other) >= 0

    def __cmp__(self, other):
        if self.value == other.value:
            return 0
        if self.value < other.value:
            return -1
        return 1

    def next(self):
        return Precedence(self.value + 1)


ParseRule = namedtuple(
    "ParseRule",
    ("prefix", "infix", "precedence"),
    defaults=(
        lambda parser: parse_error("Expected expression!", parser)(),
        lambda left, parser: parse_error("Expected expression!", parser)(),
        Precedence.NONE,
    ),
)


def get_rule(token):
    return PRATT_TABLE[token.token_type]


def parse_expr(parser, precedence=Precedence.ASSIGNMENT):
    first_rule = get_rule(parser.get_current())
    value = first_rule.prefix(parser)
    while get_rule(parser.get_current()).precedence >= precedence:
        rule = get_rule(parser.get_current())
        value = rule.infix(value, parser)
    return value


def parse_grouping(parser):
    parser.consume(
        TokenType.LEFT_PAREN, parse_error("Expected '(' before expression!", parser)
    )
    value = parse_expr(parser)
    parser.consume(
        TokenType.RIGHT_PAREN, parse_error("Expected ')' after expression!", parser)
    )
    return value


class AstNode:
    def __init__(self, parser):
        self.token = parser.get_current()

    def get_info(self):
        return token_info(self.token)


class ExprNode(AstNode):
    def __init__(self, parser):
        super().__init__(parser)
        self.type_annotation = TypeAnnotation()


class CallExpr(ExprNode):
    def __init__(self, left, parser):
        super().__init__(parser)
        self.target = left
        parser.consume(
            TokenType.LEFT_PAREN, parse_error("Expected '(' to call!", parser)
        )
        self.arguments = []
        while not parser.match(TokenType.RIGHT_PAREN):
            self.arguments.append(parse_expr(parser))
            if not parser.check(TokenType.RIGHT_PAREN):
                parser.consume(
                    TokenType.COMMA,
                    parse_error("Expected comma to delimit parameters!", parser),
                )

    def accept(self, expr_visitor):
        expr_visitor.visit_call_expr(self)


class UnaryExpr(ExprNode):
    def __init__(self, parser):
        super().__init__(parser)
        parser.consume_one(UNARY_OPS, parse_error("Expected unary operator!", parser))
        self.operator = parser.get_prev()
        self.target = parse_expr(parser, precedence=Precedence.UNARY)

    def accept(self, expr_visitor):
        expr_visitor.visit_unary_expr(self)


class BinaryExpr(ExprNode):
    def __init__(self, left, parser):
        super().__init__(parser)
        self.left = left
        parser.consume_one(BINARY_OPS, parse_error("Expected binary operator!", parser))
        self.operator = parser.get_prev()
        prec = get_rule(self.operator).precedence
        if self.operator.token_type not in LEFT_ASSOC_OPS:
            prec = prec.next()
        self.right = parse_expr(parser, precedence=prec)
        self.token = self.operator

    def accept(self, expr_visitor):
        expr_visitor.visit_binary_expr(self)


class AndExpr(ExprNode):
    def __init__(self, left, parser):
        super().__init__(parser)
        self.left = left
        parser.consume(TokenType.AND, parse_error("Expected and operator!", parser))
        self.operator = parser.get_prev()
        self.right = parse_expr(parser, precedence=Precedence.AND)
        self.token = self.operator

    def accept(self, expr_visitor):
        expr_visitor.visit_and_expr(self)


class OrExpr(ExprNode):
    def __init__(self, left, parser):
        super().__init__(parser)
        self.left = left
        parser.consume(TokenType.OR, parse_error("Expected or operator!", parser))
        self.operator = parser.get_prev()
        self.right = parse_expr(parser, precedence=Precedence.OR)
        self.token = self.operator

    def accept(self, expr_visitor):
        expr_visitor.visit_or_expr(self)


class IdentExpr(ExprNode):
    def __init__(self, parser):
        super().__init__(parser)
        parser.consume(TokenType.IDENTIFIER, parse_error("Expected variable!", parser))
        self.name = parser.get_prev()

    def accept(self, expr_visitor):
        expr_visitor.visit_ident_expr(self)


class StringExpr(ExprNode):
    def __init__(self, parser):
        super().__init__(parser)
        parser.consume(TokenType.STRING, parse_error("Expected string!", parser))
        total = [self.token]
        while parser.match(TokenType.STRING):
            total.append(parser.get_prev())
        joined = '"'.join(map(lambda t: t.lexeme[1:-1], total))
        self.value = ClrStr(joined)

    def accept(self, expr_visitor):
        expr_visitor.visit_string_expr(self)


class NumberExpr(ExprNode):
    def __init__(self, parser):
        super().__init__(parser)
        parser.consume(TokenType.NUMBER, parse_error("Expected number!", parser))
        if parser.match(TokenType.INTEGER_SUFFIX):
            try:
                self.value = ClrInt(self.token.lexeme)
                self.integral = True
            except ValueError:
                parse_error("Integer literal must be an integer!", parser)()
        else:
            try:
                self.value = ClrNum(self.token.lexeme)
                self.integral = False
            except ValueError:
                parse_error("Number literal must be a number!", parser)()

    def accept(self, expr_visitor):
        expr_visitor.visit_number_expr(self)


class BooleanExpr(ExprNode):
    def __init__(self, parser):
        super().__init__(parser)
        parser.consume_one(BOOLEANS, parse_error("Expected boolean literal!", parser))
        self.value = parser.get_prev().token_type == TokenType.TRUE

    def accept(self, expr_visitor):
        expr_visitor.visit_boolean_expr(self)


BOOLEANS = {TokenType.TRUE, TokenType.FALSE}

UNARY_OPS = {TokenType.MINUS, TokenType.BANG}

BINARY_OPS = {
    TokenType.PLUS,
    TokenType.MINUS,
    TokenType.STAR,
    TokenType.SLASH,
    TokenType.EQUAL_EQUAL,
    TokenType.BANG_EQUAL,
    TokenType.LESS,
    TokenType.GREATER_EQUAL,
    TokenType.GREATER,
    TokenType.LESS_EQUAL,
    TokenType.EQUAL,
}

LEFT_ASSOC_OPS = {TokenType.EQUAL}


PRATT_TABLE = defaultdict(
    ParseRule,
    {
        TokenType.LEFT_PAREN: ParseRule(
            prefix=parse_grouping, infix=CallExpr, precedence=Precedence.CALL
        ),
        TokenType.MINUS: ParseRule(
            prefix=UnaryExpr, infix=BinaryExpr, precedence=Precedence.TERM
        ),
        TokenType.PLUS: ParseRule(infix=BinaryExpr, precedence=Precedence.TERM),
        TokenType.SLASH: ParseRule(infix=BinaryExpr, precedence=Precedence.FACTOR),
        TokenType.STAR: ParseRule(infix=BinaryExpr, precedence=Precedence.FACTOR),
        TokenType.NUMBER: ParseRule(prefix=NumberExpr),
        TokenType.STRING: ParseRule(prefix=StringExpr),
        TokenType.TRUE: ParseRule(prefix=BooleanExpr),
        TokenType.FALSE: ParseRule(prefix=BooleanExpr),
        TokenType.BANG: ParseRule(prefix=UnaryExpr),
        TokenType.EQUAL_EQUAL: ParseRule(
            infix=BinaryExpr, precedence=Precedence.EQUALITY
        ),
        TokenType.BANG_EQUAL: ParseRule(
            infix=BinaryExpr, precedence=Precedence.EQUALITY
        ),
        TokenType.LESS: ParseRule(infix=BinaryExpr, precedence=Precedence.COMPARISON),
        TokenType.GREATER_EQUAL: ParseRule(
            infix=BinaryExpr, precedence=Precedence.COMPARISON
        ),
        TokenType.GREATER: ParseRule(
            infix=BinaryExpr, precedence=Precedence.COMPARISON
        ),
        TokenType.LESS_EQUAL: ParseRule(
            infix=BinaryExpr, precedence=Precedence.COMPARISON
        ),
        TokenType.IDENTIFIER: ParseRule(prefix=IdentExpr),
        TokenType.AND: ParseRule(infix=AndExpr, precedence=Precedence.AND),
        TokenType.OR: ParseRule(infix=OrExpr, precedence=Precedence.OR),
        TokenType.EQUAL: ParseRule(infix=BinaryExpr, precedence=Precedence.ASSIGNMENT),
    },
)
