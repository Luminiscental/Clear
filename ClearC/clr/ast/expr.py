"""
This module provides classes / functions to form expression nodes within the AST from parsing tokens.

Functions:
    - get_rule
    - parse_expr
    - parse_grouping

Classes:
    - Precedence
    - AstNode
    - ExprNode
    - CallExpr
    - UnaryExpr
    - BinaryExpr
    - AndExpr
    - OrExpr
    - IdentExpr
    - StringExpr
    - NumberExpr
    - BooleanExpr
"""
from enum import Enum
from collections import defaultdict, namedtuple
from clr.tokens import TokenType
from clr.ast.tree import AstNode
from clr.errors import parse_error
from clr.ast.index import IndexAnnotation
from clr.constants import ClrStr, ClrNum, ClrInt


class Precedence(Enum):
    """
    This class enumerates the precedences of operators to parse with values to represent their
    ordering and rich comparison methods.

    Superclasses:
        - Enum

    Methods:
        - next
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
        """
        This methods returns the next highest precedence after self.

        Returns:
            The next highest precedence after self.
        """
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
    """
    This function returns the ParseRule for a given operator token by looking up the pratt table.

    Parameters:
        - token : the operator token to lookup the precedence for.

    Returns:
        the parse rule for the given operator, which emits an error for invalid operators / usage.
    """
    return PRATT_TABLE[token.token_type]


def parse_expr(parser, precedence=Precedence.ASSIGNMENT):
    """
    This function parses an expression node for the AST from the parser, emitting an error if the
    tokens don't form a valid expression.

    Parameters:
        - parser : the parser to read tokens from.
        - precedence=Precedence.ASSIGNMENT : the precedence of expression to parse by, parsing stops
            once an operator with precedence lower than this is reached.

    Returns:
        the expression node parsed from the parser.
    """
    # Consume an initial prefix expression bound by the passed precedence
    first_rule = get_rule(parser.get_current())
    value = first_rule.prefix(parser)
    # Consume any following infix expression still bound by the passed precedence
    while get_rule(parser.get_current()).precedence >= precedence:
        rule = get_rule(parser.get_current())
        # Update the value, pushing the old value as the left node of the infix expression
        value = rule.infix(value, parser)
    return value


def parse_grouping(parser):
    """
    This function parses an expression grouped by parentheses, emitting an error if the tokens
    don't form such an expression.

    Parameters:
        - parser : the parser to read tokens form.

    Returns:
        the expression node parsed from the parser.
    """
    parser.consume(
        TokenType.LEFT_PAREN, parse_error("Expected '(' before expression!", parser)
    )
    value = parse_expr(parser)
    parser.consume(
        TokenType.RIGHT_PAREN, parse_error("Expected ')' after expression!", parser)
    )
    return value


class ExprNode(AstNode):
    """
    This class stores the type annotation for an expression node in the AST, by default annotated
    as unresolved.

    Superclasses:
        - AstNode

    Fields:
        - type_annotation : the type annotation for this expression.
    """

    def __init__(self, parser):
        super().__init__(parser)
        from clr.ast.type import TypeAnnotation

        self.type_annotation = TypeAnnotation()


class CallExpr(ExprNode):
    """
    This class represents an AST node for an expression calling a value, initialized from a parser.

    Superclasses:
        - ExprNode

    Fields:
        - target : the expression node that is being called.
        - arguments : a list of expressions for the arguments passed to the target when calling.

    Methods:
        - accept
    """

    def __init__(self, left, parser):
        super().__init__(parser)
        self.target = left
        parser.consume(
            TokenType.LEFT_PAREN, parse_error("Expected '(' to call!", parser)
        )
        self.arguments = []
        # Consume arguments until we hit the closing paren
        while not parser.match(TokenType.RIGHT_PAREN):
            # Consume an expression for each argument
            self.arguments.append(parse_expr(parser))
            # If we haven't hit the end consume a comma before the next argument
            if not parser.check(TokenType.RIGHT_PAREN):
                parser.consume(
                    TokenType.COMMA,
                    parse_error("Expected comma to delimit arguments!", parser),
                )

    def accept(self, expr_visitor):
        """
        This method accepts an expression visitor to the node.

        Parameters:
            - expr_visitor : the visitor to accept.
        """
        expr_visitor.visit_call_expr(self)


class UnaryExpr(ExprNode):
    """
    This class represents an AST node for a unary operator applied to a value, initialized from
    a parser.

    Superclasses:
        - ExprNode

    Fields:
        - operator : the operator token being applied.
        - target : the expression being applied onto.

    Methods:
        - accept
    """

    def __init__(self, parser):
        super().__init__(parser)
        parser.consume_one(UNARY_OPS, parse_error("Expected unary operator!", parser))
        self.operator = parser.get_prev()
        self.target = parse_expr(parser, precedence=Precedence.UNARY)

    def accept(self, expr_visitor):
        """
        This method accepts an expression visitor to the node.

        Parameters:
            - expr_visitor : the visitor to accept.
        """
        expr_visitor.visit_unary_expr(self)


class BinaryExpr(ExprNode):
    """
    This class represents an AST node for a binary operator applied to two expressions, initialized
    from a parser.

    Superclasses:
        - ExprNode

    Fields:
        - left : the left expression.
        - operator : the operator token.
        - right : the right expression.

    Methods:
        - accept
    """

    def __init__(self, left, parser):
        super().__init__(parser)
        self.left = left
        parser.consume_one(BINARY_OPS, parse_error("Expected binary operator!", parser))
        self.operator = parser.get_prev()
        prec = get_rule(self.operator).precedence
        # Right-associative operations bind to the right including repeated operations,
        # left-associative operations don't
        if self.operator.token_type not in LEFT_ASSOC_OPS:
            prec = prec.next()
        self.right = parse_expr(parser, precedence=prec)
        self.token = self.operator

    def accept(self, expr_visitor):
        """
        This method accepts an expression visitor to the node.

        Parameters:
            - expr_visitor : the visitor to accept.
        """
        expr_visitor.visit_binary_expr(self)


class AndExpr(ExprNode):
    """
    This class represents an AST node for the and operator being applied to two expressions,
    initialized from a parser.

    Superclasses:
        - ExprNode

    Fields:
        - left : the left expression.
        - operator : the and token.
        - right : the right expression.

    Methods:
        - accept
    """

    def __init__(self, left, parser):
        super().__init__(parser)
        self.left = left
        parser.consume(TokenType.AND, parse_error("Expected and operator!", parser))
        self.operator = parser.get_prev()
        # and acts like a normal right-associative binary operator when parsing
        self.right = parse_expr(parser, precedence=Precedence.AND)
        self.token = self.operator

    def accept(self, expr_visitor):
        """
        This method accepts an expression visitor to the node.

        Parameters:
            - expr_visitor : the visitor to accept.
        """
        expr_visitor.visit_and_expr(self)


class OrExpr(ExprNode):
    """
    This class represents an AST node for the or operator being applied to two expressions,
    initialized from a parser.

    Superclasses:
        - ExprNode

    Fields:
        - left : the left expression.
        - operator : the or token.
        - right : the right expression.

    Methods:
        - accept
    """

    def __init__(self, left, parser):
        super().__init__(parser)
        self.left = left
        parser.consume(TokenType.OR, parse_error("Expected or operator!", parser))
        self.operator = parser.get_prev()
        # or acts like a normal right-associative binary operator when parsing
        self.right = parse_expr(parser, precedence=Precedence.OR)
        self.token = self.operator

    def accept(self, expr_visitor):
        """
        This method accepts an expression visitor to the node.

        Parameters:
            - expr_visitor : the visitor to accept.
        """
        expr_visitor.visit_or_expr(self)


class IdentExpr(ExprNode):
    """
    This class represents an AST node for an identifier as part of an expression, initialized
    from a parser.

    Superclasses:
        - ExprNode

    Fields:
        - name : the token for the identifier.

    Methods:
        - accept
    """

    def __init__(self, parser):
        super().__init__(parser)
        parser.consume(TokenType.IDENTIFIER, parse_error("Expected variable!", parser))
        self.name = parser.get_prev()
        # Identifiers have indices, by default it is unresolved
        self.index_annotation = IndexAnnotation()
        self.is_ident = True

    def accept(self, expr_visitor):
        """
        This method accepts an expression visitor to the node.

        Parameters:
            - expr_visitor : the visitor to accept.
        """
        expr_visitor.visit_ident_expr(self)


class StringExpr(ExprNode):
    """
    This class represents an AST node for a string literal, initialized from a parser.

    Superclasses:
        - ExprNode

    Fields:
        - value : a ClrStr storing the represented string.

    Methods:
        - accept
    """

    def __init__(self, parser):
        super().__init__(parser)
        parser.consume(TokenType.STRING, parse_error("Expected string!", parser))
        total = [self.token]
        # Adjacent string literals are combined and joined with " to allow effective escaping,
        # don't judge me
        while parser.match(TokenType.STRING):
            total.append(parser.get_prev())
        joined = '"'.join(map(lambda t: t.lexeme[1:-1], total))
        self.value = ClrStr(joined)

    def accept(self, expr_visitor):
        """
        This method accepts an expression visitor to the node.

        Parameters:
            - expr_visitor : the visitor to accept.
        """
        expr_visitor.visit_string_expr(self)


class NumberExpr(ExprNode):
    """
    This class represents an AST node for a number/integer literal, initialized from a parser.

    Superclasses:
        - ExprNode

    Fields:
        - value : a ClrNum or ClrInt storing the represented value.

    Methods:
        - accept
    """

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
        """
        This method accepts an expression visitor to the node.

        Parameters:
            - expr_visitor : the visitor to accept.
        """
        expr_visitor.visit_number_expr(self)


class BooleanExpr(ExprNode):
    """
    This class represents an AST node for a boolean literal, initialized from a parser.

    Superclasses:
        - ExprNode

    Fields:
        - value : a boolean storing the represented value.

    Methods:
        - accept
    """

    def __init__(self, parser):
        super().__init__(parser)
        parser.consume_one(BOOLEANS, parse_error("Expected boolean literal!", parser))
        self.value = parser.get_prev().token_type == TokenType.TRUE

    def accept(self, expr_visitor):
        """
        This method accepts an expression visitor to the node.

        Parameters:
            - expr_visitor : the visitor to accept.
        """
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
