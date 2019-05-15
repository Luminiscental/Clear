from enum import Enum
from collections import defaultdict, namedtuple
from clr.errors import parse_error
from clr.tokens import TokenType
from clr.constants import ClrStr, ClrInt, ClrNum
from clr.ast.index_annotations import IndexAnnotation
from clr.ast.type_annotations import TypeAnnotation, NUM_TYPE, INT_TYPE, STR_TYPE
from clr.ast.type_nodes import parse_type


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
    # Consume an initial prefix expression bound by the passed precedence
    first_rule = get_rule(parser[0])
    value = first_rule.prefix(parser)
    # Consume any following infix expression still bound by the passed precedence
    while get_rule(parser[0]).precedence >= precedence:
        rule = get_rule(parser[0])
        # Update the value, pushing the old value as the left node of the infix expression
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
    value.grouped = True
    return value


class ExprNode:  # pylint: disable=too-few-public-methods
    def __init__(self):
        self.type_annotation = TypeAnnotation()
        self.assignable = False
        self.grouped = False
        self.polymorphed_fields = None


def pprint(str_func):
    def wrapped_str(self):
        if self.grouped:
            return "(" + str_func(self) + ")"
        return str_func(self)

    return wrapped_str


class CallExpr(ExprNode):
    def __init__(self, target, arguments):
        super().__init__()
        self.target = target
        self.arguments = arguments

    @staticmethod
    def parse(left, parser):
        target = left
        parser.consume(
            TokenType.LEFT_PAREN, parse_error("Expected '(' to call!", parser)
        )
        arguments = []
        # Consume arguments until we hit the closing paren
        while not parser.match(TokenType.RIGHT_PAREN):
            # Consume an expression for each argument
            arguments.append(parse_expr(parser))
            # If we haven't hit the end consume a comma before the next argument
            if not parser.check(TokenType.RIGHT_PAREN):
                parser.consume(
                    TokenType.COMMA,
                    parse_error("Expected comma to delimit arguments!", parser),
                )
        return CallExpr(target, arguments)

    @pprint
    def __str__(self):
        return str(self.target) + "(" + ", ".join(map(str, self.arguments)) + ")"

    def accept(self, expr_visitor):
        expr_visitor.visit_call_expr(self)


class ConstructExpr(ExprNode):
    def __init__(self, name, args):
        super().__init__()
        self.name = name
        self.args = args
        self.constructor_index_annotation = IndexAnnotation()

    @staticmethod
    def parse(left, parser):
        if not isinstance(left, IdentExpr):
            parse_error(f"Invalid constructor type `{left}`!", parser)()
        name = left.name
        args = {}
        parser.consume(
            TokenType.LEFT_BRACE, parse_error("Expected constructor!", parser)
        )
        while not parser.match(TokenType.RIGHT_BRACE):
            parser.consume(
                TokenType.IDENTIFIER, parse_error("Expected field argument!", parser)
            )
            field_token = parser[-1]
            if field_token.lexeme in args:
                parse_error("Repeated field argument!", parser)()
            parser.consume(
                TokenType.EQUAL, parse_error("Expected field value!", parser)
            )
            field_value = parse_expr(parser)
            args[field_token.lexeme] = field_value
            if not parser.check(TokenType.RIGHT_BRACE):
                parser.consume(
                    TokenType.COMMA,
                    parse_error("Field arguments must be comma delimited!", parser),
                )
        return ConstructExpr(name, args)

    @pprint
    def __str__(self):
        return (
            str(self.name)
            + " { "
            + ", ".join(
                [str(name) + " = " + str(value) for name, value in self.args.items()]
            )
            + " }"
        )

    def accept(self, expr_visitor):
        expr_visitor.visit_construct_expr(self)


class UnaryExpr(ExprNode):
    def __init__(self, operator, target):
        super().__init__()
        self.operator = operator
        self.target = target

    @staticmethod
    def parse(parser):
        parser.consume_one(UNARY_OPS, parse_error("Expected unary operator!", parser))
        operator = parser[-1]
        target = parse_expr(parser, precedence=Precedence.UNARY)
        return UnaryExpr(operator, target)

    @pprint
    def __str__(self):
        return str(self.operator) + str(self.target)

    def accept(self, expr_visitor):
        expr_visitor.visit_unary_expr(self)


class AssignExpr(ExprNode):
    def __init__(self, left, right, operator):
        super().__init__()
        self.left = left
        self.right = right
        self.operator = operator

    @staticmethod
    def parse(left, parser):
        parser.consume(TokenType.EQUAL, parse_error("Expected assignment!", parser))
        operator = parser[-1]
        right = parse_expr(parser, Precedence.ASSIGNMENT)
        return AssignExpr(left, right, operator)

    @pprint
    def __str__(self):
        return str(self.left) + " = " + str(self.right)

    def accept(self, expr_visitor):
        expr_visitor.visit_assign_expr(self)


class AccessExpr(ExprNode):
    def __init__(self, left, right):
        super().__init__()
        self.left = left
        self.right = right

    @staticmethod
    def parse(left, parser):
        parser.consume(
            TokenType.DOT, parse_error("Expected property accessor!", parser)
        )
        right = parse_expr(parser, Precedence.CALL.next())
        return AccessExpr(left, right)

    @pprint
    def __str__(self):
        return str(self.left) + "." + str(self.right)

    def accept(self, expr_visitor):
        expr_visitor.visit_access_expr(self)


class BinaryExpr(ExprNode):
    def __init__(self, left, right, operator):
        super().__init__()
        self.left = left
        self.right = right
        self.operator = operator

    @staticmethod
    def parse(left, parser):
        possibilities = set.union(
            set(ARITHMETIC_OPS), set(EQUALITY_OPS), set(COMPARISON_OPS)
        )
        parser.consume_one(
            possibilities, parse_error("Expected binary operator!", parser)
        )
        operator = parser[-1]
        precedence = get_rule(operator).precedence.next()
        right = parse_expr(parser, precedence)
        return BinaryExpr(left, right, operator)

    @pprint
    def __str__(self):
        return str(self.left) + " " + str(self.operator) + " " + str(self.right)

    def accept(self, expr_visitor):
        expr_visitor.visit_binary_expr(self)


class IfExpr(ExprNode):
    def __init__(self, checks, otherwise):
        super().__init__()
        self.checks = checks
        self.otherwise = otherwise

    @staticmethod
    def parse(parser):
        parser.consume(TokenType.IF, parse_error("Expected if expression!", parser))
        initial_cond = parse_grouping(parser)
        parser.consume(TokenType.LEFT_BRACE, parse_error("Expected if block!", parser))
        initial_value = parse_expr(parser)
        parser.consume(
            TokenType.RIGHT_BRACE, parse_error("Expected '}' to end block!", parser)
        )
        checks = [(initial_cond, initial_value)]
        while parser.match(TokenType.ELSE):
            if parser.match(TokenType.IF):
                other_cond = parse_grouping(parser)
                parser.consume(
                    TokenType.LEFT_BRACE, parse_error("Expected else-if block!", parser)
                )
                other_value = parse_expr(parser)
                parser.consume(
                    TokenType.RIGHT_BRACE,
                    parse_error("Expected '}' to end block!", parser),
                )
                checks.append((other_cond, other_value))
            else:
                parser.consume(
                    TokenType.LEFT_BRACE, parse_error("Expected else block!", parser)
                )
                otherwise = parse_expr(parser)
                parser.consume(
                    TokenType.RIGHT_BRACE,
                    parse_error("Expected '}' to end block!", parser),
                )
                break
        else:
            parse_error("Expected final else block for if expression!", parser)
        return IfExpr(checks, otherwise)

    def accept(self, expr_visitor):
        expr_visitor.visit_if_expr(self)


class UnpackExpr(ExprNode):
    def __init__(self, target, present_value, default_value):
        super().__init__()
        self.target = target
        self.present_value = present_value
        self.default_value = default_value
        # Upvalues for the present-case implicit function
        self.upvalues = []

    @staticmethod
    def parse(left, parser):
        present_value = None
        default_value = None

        if not isinstance(left, IdentExpr):
            parse_error(f"Cannot unpack non-identifier expression `{left}`!", parser)()

        parser.consume(
            TokenType.QUESTION_MARK, parse_error("Expected optional unpacking!", parser)
        )
        # Skipped present-case
        if parser.match(TokenType.COLON):
            default_value = parse_expr(parser)
        else:
            present_value = parse_expr(parser)
            # Both present
            if parser.match(TokenType.COLON):
                default_value = parse_expr(parser)
        return UnpackExpr(left, present_value, default_value)

    @pprint
    def __str__(self):
        result = str(self.target) + "?"
        if self.present_value is not None:
            result += " " + str(self.present_value)
        if self.default_value is not None:
            if self.present_value is not None:
                result += " "
            result += ": " + str(self.default_value)
        return result

    def accept(self, expr_visitor):
        expr_visitor.visit_unpack_expr(self)


class LambdaExpr(ExprNode):
    def __init__(self, params, result):
        super().__init__()
        self.params = params
        self.result = result
        self.upvalues = []

    @staticmethod
    def parse(parser):
        parser.consume(TokenType.FUNC, parse_error("Expected lambda!", parser))
        parser.consume(
            TokenType.LEFT_PAREN, parse_error("Expected '(' for parameters!", parser)
        )
        params = []
        while not parser.match(TokenType.RIGHT_PAREN):
            param_type = parse_type(parser)
            param_name = IdentExpr.parse(parser)
            pair = (param_type, param_name.name)
            params.append(pair)
            if not parser.check(TokenType.RIGHT_PAREN):
                parser.consume(
                    TokenType.COMMA,
                    parse_error("Expected comma delimited parameters!", parser),
                )
        result = parse_expr(parser)
        return LambdaExpr(params, result)

    @pprint
    def __str__(self):
        result = "func("
        result += ", ".join(
            map(
                lambda param_pair: str(param_pair[0]) + " " + str(param_pair[1]),
                self.params,
            )
        )
        result += ") " + str(self.result)
        return result

    def accept(self, expr_visitor):
        expr_visitor.visit_lambda_expr(self)


class AndExpr(ExprNode):
    def __init__(self, left, right, operator):
        super().__init__()
        self.left = left
        self.right = right
        self.operator = operator

    @staticmethod
    def parse(left, parser):
        parser.consume(TokenType.AND, parse_error("Expected and operator!", parser))
        operator = parser[-1]
        # and acts like a normal right-associative binary operator when parsing
        right = parse_expr(parser, precedence=Precedence.AND)
        return AndExpr(left, right, operator)

    @pprint
    def __str__(self):
        return str(self.left) + " and " + str(self.right)

    def accept(self, expr_visitor):
        expr_visitor.visit_and_expr(self)


class OrExpr(ExprNode):
    def __init__(self, left, right, operator):
        super().__init__()
        self.left = left
        self.right = right
        self.operator = operator

    @staticmethod
    def parse(left, parser):
        parser.consume(TokenType.OR, parse_error("Expected or operator!", parser))
        operator = parser[-1]
        # or acts like a normal right-associative binary operator when parsing
        right = parse_expr(parser, precedence=Precedence.OR)
        return OrExpr(left, right, operator)

    @pprint
    def __str__(self):
        return str(self.left) + " or " + str(self.right)

    def accept(self, expr_visitor):
        expr_visitor.visit_or_expr(self)


class KeywordExpr(ExprNode):
    def __init__(self, token):
        super().__init__()
        self.token = token

    @staticmethod
    def parse(parser):
        parser.consume_one(
            KEYWORD_EXPRESSIONS, parse_error("Expected keyword expression!", parser)
        )
        token = parser[-1]
        return KeywordExpr(token)

    @pprint
    def __str__(self):
        return self.token.lexeme

    def accept(self, expr_visitor):
        expr_visitor.visit_keyword_expr(self)


class IdentExpr(ExprNode):
    def __init__(self, name):
        super().__init__()
        self.name = name
        # Identifiers have indices, by default it is unresolved
        self.index_annotation = IndexAnnotation()

    @staticmethod
    def parse(parser):
        parser.consume(TokenType.IDENTIFIER, parse_error("Expected variable!", parser))
        name = parser[-1]
        return IdentExpr(name)

    @pprint
    def __str__(self):
        return self.name.lexeme

    def accept(self, expr_visitor):
        expr_visitor.visit_ident_expr(self)


class StringExpr(ExprNode):
    def __init__(self, value):
        super().__init__()
        self.value = value

    @staticmethod
    def parse(parser):
        parser.consume(TokenType.STRING, parse_error("Expected string!", parser))
        total = [parser[-1]]
        # Adjacent string literals are combined and joined by " to allow effective escaping,
        # don't judge me
        while parser.match(TokenType.STRING):
            total.append(parser[-1])
        joined = '"'.join(map(lambda t: t.lexeme[1:-1], total))
        value = ClrStr(joined)
        return StringExpr(value)

    @pprint
    def __str__(self):
        return '"' + self.value.value.replace('"', '""') + '"'

    def accept(self, expr_visitor):
        expr_visitor.visit_string_expr(self)


class NumberExpr(ExprNode):
    def __init__(self, lexeme, value, integral):
        super().__init__()
        self.lexeme = lexeme
        self.value = value
        self.integral = integral

    @staticmethod
    def parse(parser):
        parser.consume(TokenType.NUMBER, parse_error("Expected number!", parser))
        lexeme = parser[-1].lexeme
        if parser.match(TokenType.INTEGER_SUFFIX):
            try:
                value = ClrInt(lexeme)
                integral = True
            except ValueError:
                parse_error("Integer literal must be an integer!", parser)()
            lexeme += "i"
        else:
            try:
                value = ClrNum(lexeme)
                integral = False
            except ValueError:
                parse_error("Number literal must be a number!", parser)()
        return NumberExpr(lexeme, value, integral)

    @pprint
    def __str__(self):
        return self.lexeme

    def accept(self, expr_visitor):
        expr_visitor.visit_number_expr(self)


class BooleanExpr(ExprNode):
    def __init__(self, value):
        super().__init__()
        self.value = value

    @staticmethod
    def parse(parser):
        parser.consume_one(BOOLEANS, parse_error("Expected boolean literal!", parser))
        value = parser[-1].token_type == TokenType.TRUE
        return BooleanExpr(value)

    @pprint
    def __str__(self):
        return str(self.value).lower()

    def accept(self, expr_visitor):
        expr_visitor.visit_boolean_expr(self)


KEYWORD_EXPRESSIONS = {TokenType.THIS, TokenType.NIL}

BOOLEANS = {TokenType.TRUE, TokenType.FALSE}

UNARY_OPS = {TokenType.MINUS, TokenType.BANG}

ARITHMETIC_OPS = {
    TokenType.PLUS: [NUM_TYPE, INT_TYPE, STR_TYPE],
    TokenType.MINUS: [NUM_TYPE, INT_TYPE],
    TokenType.STAR: [NUM_TYPE, INT_TYPE],
    TokenType.SLASH: [NUM_TYPE],
}

EQUALITY_OPS = {TokenType.EQUAL_EQUAL, TokenType.BANG_EQUAL}

COMPARISON_OPS = {
    TokenType.LESS,
    TokenType.GREATER_EQUAL,
    TokenType.GREATER,
    TokenType.LESS_EQUAL,
}

PRATT_TABLE = defaultdict(
    ParseRule,
    {
        TokenType.LEFT_BRACE: ParseRule(
            infix=ConstructExpr.parse, precedence=Precedence.CALL
        ),
        TokenType.LEFT_PAREN: ParseRule(
            prefix=parse_grouping, infix=CallExpr.parse, precedence=Precedence.CALL
        ),
        TokenType.MINUS: ParseRule(
            prefix=UnaryExpr.parse, infix=BinaryExpr.parse, precedence=Precedence.TERM
        ),
        TokenType.PLUS: ParseRule(infix=BinaryExpr.parse, precedence=Precedence.TERM),
        TokenType.SLASH: ParseRule(
            infix=BinaryExpr.parse, precedence=Precedence.FACTOR
        ),
        TokenType.STAR: ParseRule(infix=BinaryExpr.parse, precedence=Precedence.FACTOR),
        TokenType.NUMBER: ParseRule(prefix=NumberExpr.parse),
        TokenType.STRING: ParseRule(prefix=StringExpr.parse),
        TokenType.TRUE: ParseRule(prefix=BooleanExpr.parse),
        TokenType.FALSE: ParseRule(prefix=BooleanExpr.parse),
        TokenType.BANG: ParseRule(prefix=UnaryExpr.parse),
        TokenType.DOT: ParseRule(infix=AccessExpr.parse, precedence=Precedence.CALL),
        TokenType.EQUAL_EQUAL: ParseRule(
            infix=BinaryExpr.parse, precedence=Precedence.EQUALITY
        ),
        TokenType.BANG_EQUAL: ParseRule(
            infix=BinaryExpr.parse, precedence=Precedence.EQUALITY
        ),
        TokenType.LESS: ParseRule(
            infix=BinaryExpr.parse, precedence=Precedence.COMPARISON
        ),
        TokenType.GREATER_EQUAL: ParseRule(
            infix=BinaryExpr.parse, precedence=Precedence.COMPARISON
        ),
        TokenType.GREATER: ParseRule(
            infix=BinaryExpr.parse, precedence=Precedence.COMPARISON
        ),
        TokenType.LESS_EQUAL: ParseRule(
            infix=BinaryExpr.parse, precedence=Precedence.COMPARISON
        ),
        TokenType.QUESTION_MARK: ParseRule(
            infix=UnpackExpr.parse, precedence=Precedence.CALL
        ),
        TokenType.IDENTIFIER: ParseRule(prefix=IdentExpr.parse),
        TokenType.AND: ParseRule(infix=AndExpr.parse, precedence=Precedence.AND),
        TokenType.OR: ParseRule(infix=OrExpr.parse, precedence=Precedence.OR),
        TokenType.EQUAL: ParseRule(
            infix=AssignExpr.parse, precedence=Precedence.ASSIGNMENT
        ),
        TokenType.THIS: ParseRule(prefix=KeywordExpr.parse),
        TokenType.NIL: ParseRule(prefix=KeywordExpr.parse),
        TokenType.IF: ParseRule(prefix=IfExpr.parse),
        TokenType.FUNC: ParseRule(prefix=LambdaExpr.parse),
    },
)
