from enum import Enum
from collections import namedtuple, defaultdict
from clr.tokens import TokenType, token_info, tokenize
from clr.errors import parse_error, emit_error
from clr.values import DEBUG
from clr.constants import ClrInt, ClrNum, ClrStr
from clr.compile import Compiler


class Parser:
    def __init__(self, tokens):
        self.index = 0
        self.tokens = tokens

    def get_current(self):
        return self.tokens[self.index]

    def get_prev(self):
        return self.tokens[self.index - 1]

    def current_info(self):
        return token_info(self.get_current())

    def prev_info(self):
        return token_info(self.get_prev())

    def advance(self):
        self.index += 1

    def check(self, token_type):
        return self.get_current().token_type == token_type

    def match(self, expected_type):
        if not self.check(expected_type):
            return False
        self.advance()
        return True

    def consume(self, expected_type, err):
        if not self.match(expected_type):
            err()

    def consume_one(self, possibilities, err):
        if not possibilities:
            err()
        elif not self.match(possibilities[0]):
            self.consume_one(possibilities[1:], err)


def parse_source(source):

    tokens = tokenize(source)
    if DEBUG:
        print("Tokens:")
        print(" ".join([token.lexeme for token in tokens]))
    parser = Parser(tokens)
    ast = Ast(parser)
    return ast


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
        lambda parser: parse_error("Expected expression!", parser),
        lambda left, parser: parse_error("Expected expression!", parser),
        Precedence.NONE,
    ),
)


def get_rule(token):
    return PRATT_TABLE[token.token_type]


class Ast:
    """
    Ast : AstDecl* ;

    self.children: a list of the declarations
    """

    def __init__(self, parser):
        self.children = []
        while not parser.match(TokenType.EOF):
            self.add_child(AstDecl(parser))

    def add_child(self, child):
        self.children.append(child)

    def gen_code(self):
        compiler = Compiler()
        for child in self.children:
            child.gen_code(compiler)
        return compiler.flush_code()


class AstDecl:
    """
    AstDecl : AstValDecl
            | AstStat
            ;

    self.value: the declaration
    """

    def __init__(self, parser):
        if parser.check(TokenType.VAL):
            self.value = AstValDecl(parser)
        else:
            self.value = AstStat(parser)

    def gen_code(self, compiler):
        self.value.gen_code(compiler)


class AstValDecl:
    """
    AstValDecl : 'val' id '=' AstExpr ';' ;

    self.name: the identifier token
    self.value: expression evaluating to the intializer of the value
    """

    def __init__(self, parser):
        if not parser.match(TokenType.VAL):
            parse_error("Expected value declaration!", parser)()
        if not parser.match(TokenType.IDENTIFIER):
            parse_error("Expected value name!", parser)()
        self.name = parser.get_prev()
        if not parser.match(TokenType.EQUAL):
            parse_error("Expected value initializer!", parser)()
        self.value = AstExpr(parser)
        parser.consume(
            TokenType.SEMICOLON,
            parse_error("Expected semicolon after value declaration!", parser),
        )

    def gen_code(self, compiler):
        compiler.init_value(self.name, self.value)


class AstStat:
    """
    AstStat : AstPrintStat
            | AstBlock
            | AstIfStat
            | AstExprStat
            ;

    self.value: the statement
    """

    def __init__(self, parser):
        if parser.check(TokenType.PRINT):
            self.value = AstPrintStat(parser)
        elif parser.check(TokenType.LEFT_BRACE):
            self.value = AstBlock(parser)
        elif parser.check(TokenType.IF):
            self.value = AstIfStat(parser)
        else:
            self.value = AstExprStat(parser)

    def gen_code(self, compiler):
        self.value.gen_code(compiler)


class AstPrintStat:
    """
    AstPrintStat : 'print' AstExpr ';' ;

    self.value: expression evaluating to the value to print
    """

    def __init__(self, parser):
        if not parser.match(TokenType.PRINT):
            parse_error("Expected print statement!", parser)()
        self.value = AstExpr(parser)
        if not parser.match(TokenType.SEMICOLON):
            parse_error("Expected semicolon for print statement!", parser)()

    def gen_code(self, compiler):
        compiler.print_expression(self.value)


class AstIfStat:
    """
    AstIfStat : 'if' AstExpr AstBlock ( 'else' 'if' AstExpr AstBlock )* ( 'else' AstBlock )? ;

    self.checks: list of (condition, block) tuples for the if / else-if branches
    self.otherwise: block for the else branch or None
    """

    def __init__(self, parser):
        if not parser.match(TokenType.IF):
            parse_error("Expected if statement!", parser)()
        self.checks = [(AstExpr(parser), AstBlock(parser))]
        self.otherwise = None
        while parser.match(TokenType.ELSE):
            if parser.match(TokenType.IF):
                other_cond = AstExpr(parser)
                other_block = AstBlock(parser)
                self.checks.append((other_cond, other_block))
            else:
                self.otherwise = AstBlock(parser)
                break

    def gen_code(self, compiler):
        compiler.run_if(self.checks, self.otherwise)


class AstExprStat:
    """
    AstExprStat : AstExpr ';' ;

    self.value: the expression
    """

    def __init__(self, parser):
        self.value = AstExpr(parser)
        if not parser.match(TokenType.SEMICOLON):
            parse_error("Expected semicolon to end expression statement!", parser)()

    def gen_code(self, compiler):
        compiler.drop_expression(self.value)


class AstBlock:
    """
    AstBlock : '{' AstDecl* '}' ;

    self.declarations: a list of the declarations
    """

    def __init__(self, parser):
        if not parser.match(TokenType.LEFT_BRACE):
            parse_error("Expected block!", parser)()
        opener = parser.get_prev()
        self.declarations = []
        while not parser.match(TokenType.RIGHT_BRACE):
            if parser.match(TokenType.EOF):
                emit_error(f"Unclosed block! {token_info(opener)}")()
            decl = AstDecl(parser)
            self.declarations.append(decl)
            pass

    def gen_code(self, compiler):
        compiler.push_scope()
        for decl in self.declarations:
            decl.gen_code(compiler)
        compiler.pop_scope()


class AstExpr:
    """
    self.value: tree of the expression
    """

    def __init__(self, parser, precedence=Precedence.ASSIGNMENT):
        first_rule = get_rule(parser.get_current())
        self.value = first_rule.prefix(parser)
        while get_rule(parser.get_current()).precedence >= precedence:
            rule = get_rule(parser.get_current())
            self.value = rule.infix(self.value, parser)

    def gen_code(self, compiler):
        self.value.gen_code(compiler)


class AstGrouping:
    """
    self.value: the enclosed expression
    """

    def __init__(self, parser):
        if not parser.match(TokenType.LEFT_PAREN):
            parse_error("Expected '(' before expression!", parser)()
        self.value = AstExpr(parser)
        if not parser.match(TokenType.RIGHT_PAREN):
            parse_error("Expected ')' after expression!", parser)()

    def gen_code(self, compiler):
        self.value.gen_code(compiler)


class AstUnary:
    """
    self.operator: the operator token
    self.target: expression evaluating to the operand
    """

    def __init__(self, parser):
        parser.consume_one(
            [TokenType.MINUS, TokenType.BANG],
            parse_error("Expected unary operator!", parser),
        )
        self.operator = parser.get_prev()
        self.target = AstExpr(parser, precedence=Precedence.UNARY)

    def gen_code(self, compiler):
        compiler.apply_unary(self.operator, self.target)


class AstBinary:
    """
    self.operator: the operator token
    self.left: expression evaluating to the left operand
    self.right: expression evaluating to the right operand
    """

    def __init__(self, left, parser):
        self.left = left
        parser.consume_one(
            [
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
            ],
            parse_error("Expected binary operator!", parser),
        )
        self.operator = parser.get_prev()
        prec = get_rule(self.operator).precedence
        self.right = AstExpr(parser, precedence=prec.next())

    def gen_code(self, compiler):
        compiler.apply_binary(self.operator, self.left, self.right)


class AstNumber:
    """
    self.value: the literal value, either ClrInt or ClrNum
    """

    def __init__(self, parser):
        if not parser.match(TokenType.NUMBER):
            parse_error("Expected number!", parser)()
        token = parser.get_prev()
        if parser.match(TokenType.INTEGER_SUFFIX):
            try:
                self.value = ClrInt(token.lexeme)
            except ValueError:
                parse_error("Integer literal must be an integer!", parser)()
        else:
            try:
                self.value = ClrNum(token.lexeme)
            except ValueError:
                parse_error("Number literal must be a number!", parser)()

    def gen_code(self, compiler):
        compiler.load_constant(self.value)


class AstString:
    """
    self.value: the literal value, a ClrStr
    """

    def __init__(self, parser):
        if not parser.match(TokenType.STRING):
            parse_error("Expected string!", parser)()
        token = parser.get_prev()
        total = [token]
        while parser.match(TokenType.STRING):
            total.append(parser.get_prev())
        joined = '"'.join(map(lambda t: t.lexeme[1:-1], total))
        self.value = ClrStr(joined)

    def gen_code(self, compiler):
        compiler.load_constant(self.value)


class AstBoolean:
    """
    self.value: the boolean token
    """

    def __init__(self, parser):
        parser.consume_one(
            [TokenType.TRUE, TokenType.FALSE],
            parse_error("Expected boolean literal!", parser),
        )
        self.value = parser.get_prev()

    def gen_code(self, compiler):
        compiler.load_boolean(self.value)


class AstIdent:
    """
    self.name: the variable name token
    """

    def __init__(self, parser):
        if not parser.match(TokenType.IDENTIFIER):
            parse_error("Expected variable!", parser)()
        token = parser.get_prev()
        self.name = token

    def gen_code(self, compiler):
        compiler.load_variable(self.name)


class AstBuiltin:
    """
    self.function: the builtin function name token
    self.target: the parameter grouping
    """

    def __init__(self, parser):
        parser.consume_one(
            [
                TokenType.TYPE,
                TokenType.INT,
                TokenType.BOOL,
                TokenType.NUM,
                TokenType.STR,
            ],
            parse_error("Expected builtin function!", parser),
        )
        self.function = parser.get_prev()
        self.target = AstGrouping(parser)

    def gen_code(self, compiler):
        compiler.apply_builtin(self.function, self.target)


class AstAnd:
    """
    self.left: expression evaluating to the left operand
    self.right: expression evaluating to the right operand
    """

    def __init__(self, left, parser):
        self.left = left
        parser.consume(TokenType.AND, parse_error("Expected and operator!", parser))
        self.right = AstExpr(parser, precedence=Precedence.AND)

    def gen_code(self, compiler):
        compiler.apply_and(self.left, self.right)


class AstOr:
    """
    self.left: expression evaluating to the left operand
    self.right: expression evaluating to the right operand
    """

    def __init__(self, left, parser):
        self.left = left
        parser.consume(TokenType.OR, parse_error("Expected and operator!", parser))
        self.right = AstExpr(parser, precedence=Precedence.OR)

    def gen_code(self, compiler):
        compiler.apply_or(self.left, self.right)


PRATT_TABLE = defaultdict(
    ParseRule,
    {
        TokenType.LEFT_PAREN: ParseRule(prefix=AstGrouping, precedence=Precedence.CALL),
        TokenType.MINUS: ParseRule(
            prefix=AstUnary, infix=AstBinary, precedence=Precedence.TERM
        ),
        TokenType.PLUS: ParseRule(infix=AstBinary, precedence=Precedence.TERM),
        TokenType.SLASH: ParseRule(infix=AstBinary, precedence=Precedence.FACTOR),
        TokenType.STAR: ParseRule(infix=AstBinary, precedence=Precedence.FACTOR),
        TokenType.NUMBER: ParseRule(prefix=AstNumber),
        TokenType.STRING: ParseRule(prefix=AstString),
        TokenType.TRUE: ParseRule(prefix=AstBoolean),
        TokenType.FALSE: ParseRule(prefix=AstBoolean),
        TokenType.BANG: ParseRule(prefix=AstUnary),
        TokenType.EQUAL_EQUAL: ParseRule(
            infix=AstBinary, precedence=Precedence.EQUALITY
        ),
        TokenType.BANG_EQUAL: ParseRule(
            infix=AstBinary, precedence=Precedence.EQUALITY
        ),
        TokenType.LESS: ParseRule(infix=AstBinary, precedence=Precedence.COMPARISON),
        TokenType.GREATER_EQUAL: ParseRule(
            infix=AstBinary, precedence=Precedence.COMPARISON
        ),
        TokenType.GREATER: ParseRule(infix=AstBinary, precedence=Precedence.COMPARISON),
        TokenType.LESS_EQUAL: ParseRule(
            infix=AstBinary, precedence=Precedence.COMPARISON
        ),
        TokenType.IDENTIFIER: ParseRule(prefix=AstIdent),
        TokenType.TYPE: ParseRule(prefix=AstBuiltin, precedence=Precedence.CALL),
        TokenType.INT: ParseRule(prefix=AstBuiltin, precedence=Precedence.CALL),
        TokenType.BOOL: ParseRule(prefix=AstBuiltin, precedence=Precedence.CALL),
        TokenType.NUM: ParseRule(prefix=AstBuiltin, precedence=Precedence.CALL),
        TokenType.STR: ParseRule(prefix=AstBuiltin, precedence=Precedence.CALL),
        TokenType.AND: ParseRule(infix=AstAnd, precedence=Precedence.AND),
        TokenType.OR: ParseRule(infix=AstOr, precedence=Precedence.OR),
    },
)
