from enum import Enum
from collections import namedtuple, defaultdict
from clr.tokens import TokenType, token_info, tokenize
from clr.errors import parse_error, emit_error
from clr.values import DEBUG
from clr.constants import ClrInt, ClrNum, ClrStr
from clr.compile import Compiler
from clr.resolve import Resolver, ValueType, ResolvedName


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


class Ast:
    """
    Ast : AstDecl* ;

    self.children: a list of the declarations
    """

    def __init__(self, parser):
        self.children = []
        while not parser.match(TokenType.EOF):
            self.children.append(AstDecl(parser))
        resolver = Resolver()
        for child in self.children:
            child.resolve(resolver)

    def compile(self):
        compiler = Compiler()
        for child in self.children:
            child.gen_code(compiler)
        return compiler.flush_code()

    @staticmethod
    def from_source(source):

        tokens = tokenize(source)
        if DEBUG:
            print("Tokens:")
            print(" ".join([token.lexeme for token in tokens]))
        parser = Parser(tokens)
        ast = Ast(parser)
        return ast


# TODO: VarDecl and assignment


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

    def resolve(self, resolver):
        self.value.resolve(resolver)


class AstValDecl:
    """
    AstValDecl : 'val' id '=' AstExpr ';' ;

    self.name: the identifier token
    self.value: expression evaluating to the intializer of the value
    self.resolved_name: resolution info about this value; unresolved by default
    """

    def __init__(self, parser):
        if not parser.match(TokenType.VAL):
            parse_error("Expected value declaration!", parser)()
        if not parser.match(TokenType.IDENTIFIER):
            parse_error("Expected value name!", parser)()
        self.name = parser.get_prev()
        if not parser.match(TokenType.EQUAL):
            parse_error("Expected '=' for value initializer!", parser)()
        self.value = AstExpr(parser)
        parser.consume(
            TokenType.SEMICOLON,
            parse_error("Expected semicolon after value declaration!", parser),
        )
        self.resolved_name = ResolvedName()

    def gen_code(self, compiler):
        compiler.init_value(self.resolved_name, self.value)

    def resolve(self, resolver):
        self.value.resolve(resolver)
        self.resolved_name = resolver.add_name(self.name.lexeme, self.value.value_type)


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

    def resolve(self, resolver):
        self.value.resolve(resolver)


class AstPrintStat:
    """
    AstPrintStat : 'print' AstExpr ';' ;

    self.value: expression evaluating to the value to print or None
    """

    def __init__(self, parser):
        if not parser.match(TokenType.PRINT):
            parse_error("Expected print statement!", parser)()
        if not parser.match(TokenType.SEMICOLON):
            self.value = AstExpr(parser)
            if not parser.match(TokenType.SEMICOLON):
                parse_error("Expected semicolon for print statement!", parser)()
        else:
            self.value = None

    def gen_code(self, compiler):
        compiler.print_expression(self.value)

    def resolve(self, resolver):
        if self.value:
            self.value.resolve(resolver)


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

    def resolve(self, resolver):
        for check in self.checks:
            cond, block = check
            cond.resolve(resolver)
            block.resolve(resolver)
        if self.otherwise:
            self.otherwise.resolve(resolver)


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

    def resolve(self, resolver):
        self.value.resolve(resolver)


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

    def gen_code(self, compiler):
        compiler.push_scope()
        for decl in self.declarations:
            decl.gen_code(compiler)
        compiler.pop_scope()

    def resolve(self, resolver):
        resolver.push_scope()
        for decl in self.declarations:
            decl.resolve(resolver)
        resolver.pop_scope()


class AstExpr:
    """
    self.value: tree of the expression
    self.value_type: the type the expression evaluates to
    """

    def __init__(self, parser, precedence=Precedence.ASSIGNMENT):
        first_rule = get_rule(parser.get_current())
        self.value = first_rule.prefix(parser)
        while get_rule(parser.get_current()).precedence >= precedence:
            rule = get_rule(parser.get_current())
            self.value = rule.infix(self.value, parser)
        self.value_type = ValueType.UNRESOLVED

    def gen_code(self, compiler):
        self.value.gen_code(compiler)

    def resolve(self, resolver):
        self.value.resolve(resolver)
        self.value_type = self.value.value_type

    def __str__(self):
        return str(self.value)


class AstGrouping:
    """
    self.value: the enclosed expression
    self.value_type: the type the expression evaluates to
    """

    def __init__(self, parser):
        if not parser.match(TokenType.LEFT_PAREN):
            parse_error("Expected '(' before expression!", parser)()
        self.value = AstExpr(parser)
        if not parser.match(TokenType.RIGHT_PAREN):
            parse_error("Expected ')' after expression!", parser)()
        self.value_type = ValueType.UNRESOLVED

    def gen_code(self, compiler):
        self.value.gen_code(compiler)

    def resolve(self, resolver):
        self.value.resolve(resolver)
        self.value_type = self.value.value_type

    def __str__(self):
        return "(" + str(self.value) + ")"


class AstUnary:
    """
    self.operator: the operator token
    self.target: expression evaluating to the operand
    self.value_type: the type the expression evaluates to
    """

    def __init__(self, parser):
        parser.consume_one(
            [TokenType.MINUS, TokenType.BANG],
            parse_error("Expected unary operator!", parser),
        )
        self.operator = parser.get_prev()
        self.target = AstExpr(parser, precedence=Precedence.UNARY)
        self.value_type = ValueType.UNRESOLVED

    def gen_code(self, compiler):
        compiler.apply_unary(self.operator, self.target)

    def resolve(self, resolver):
        self.target.resolve(resolver)
        if (
            self.target.value_type
            not in {
                TokenType.MINUS: [ValueType.NUM, ValueType.INT],
                TokenType.BANG: [ValueType.BOOL],
            }[self.operator.token_type]
        ):
            emit_error(
                f"Incompatible type {str(self.value_type)} for unary operator {token_info(self.operator)}!"
            )()
        self.value_type = self.target.value_type

    def __str__(self):
        return str(self.operator.token_type) + str(self.target)


class AstBinary:
    """
    self.operator: the operator token
    self.left: expression evaluating to the left operand
    self.right: expression evaluating to the right operand
    self.value_type: the type the expression evaluates to
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
                TokenType.EQUAL,
            ],
            parse_error("Expected binary operator!", parser),
        )
        self.operator = parser.get_prev()
        prec = get_rule(self.operator).precedence
        if self.operator.token_type not in LEFT_ASSOC_OPS:
            prec = prec.next()
        self.right = AstExpr(parser, precedence=prec)
        self.value_type = ValueType.UNRESOLVED

    def gen_code(self, compiler):
        if self.operator.token_type == TokenType.EQUAL:
            # TODO: Handle assignment
            print(f"Assigning {str(self.right)} to {str(self.left)}")
        else:
            compiler.apply_binary(self.operator, self.left, self.right)

    def resolve(self, resolver):
        self.left.resolve(resolver)
        self.right.resolve(resolver)
        if self.left.value_type != self.right.value_type:
            emit_error(
                f"Incompatible operand types {str(self.left.value_type)} and {str(self.right.value_type)} for binary operator {token_info(self.operator)}!"
            )()
        if (
            self.left.value_type
            not in {
                TokenType.PLUS: [ValueType.NUM, ValueType.INT, ValueType.STR],
                TokenType.MINUS: [ValueType.NUM, ValueType.INT],
                TokenType.STAR: [ValueType.NUM, ValueType.INT],
                TokenType.SLASH: [ValueType.NUM],
                TokenType.EQUAL_EQUAL: ValueType,
                TokenType.BANG_EQUAL: ValueType,
                TokenType.LESS: [ValueType.NUM, ValueType.INT],
                TokenType.GREATER_EQUAL: [ValueType.NUM, ValueType.INT],
                TokenType.GREATER: [ValueType.NUM, ValueType.INT],
                TokenType.LESS_EQUAL: [ValueType.NUM, ValueType.INT],
                TokenType.EQUAL: ValueType,
            }[self.operator.token_type]
        ):
            emit_error(
                f"Incompatible type {str(self.value_type)} for binary operator {token_info(self.operator)}!"
            )()
        self.value_type = self.left.value_type

    def __str__(self):
        return str(self.left) + str(self.operator.token_type) + str(self.right)


class AstNumber:
    """
    self.value: the literal value, either ClrInt or ClrNum
    self.value_type: the type of the value
    """

    def __init__(self, parser):
        if not parser.match(TokenType.NUMBER):
            parse_error("Expected number!", parser)()
        token = parser.get_prev()
        if parser.match(TokenType.INTEGER_SUFFIX):
            try:
                self.value = ClrInt(token.lexeme)
                self.value_type = ValueType.INT
            except ValueError:
                parse_error("Integer literal must be an integer!", parser)()
        else:
            try:
                self.value = ClrNum(token.lexeme)
                self.value_type = ValueType.NUM
            except ValueError:
                parse_error("Number literal must be a number!", parser)()

    def gen_code(self, compiler):
        compiler.load_constant(self.value)

    def resolve(self, resolver):
        pass

    def __str__(self):
        return str(self.value)


class AstString:
    """
    self.value: the literal value, a ClrStr
    self.value_type: the type of the value
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
        self.value_type = ValueType.STR

    def gen_code(self, compiler):
        compiler.load_constant(self.value)

    def resolve(self, resolver):
        pass

    def __str__(self):
        return '"' + str(self.value) + '"'


class AstBoolean:
    """
    self.value: the boolean token
    self.value_type: the type of the value
    """

    def __init__(self, parser):
        parser.consume_one(
            [TokenType.TRUE, TokenType.FALSE],
            parse_error("Expected boolean literal!", parser),
        )
        self.value = parser.get_prev()
        self.value_type = ValueType.UNRESOLVED
        self.value_type = ValueType.BOOL

    def gen_code(self, compiler):
        compiler.load_boolean(self.value)

    def resolve(self, resolver):
        pass

    def __str__(self):
        return str(self.value.token_type)


class AstIdent:
    """
    self.name: the variable name token
    self.value_type: the type of the variable
    self.resolved_name: resolution info about the variable referred to; unresolved by default
    """

    def __init__(self, parser):
        if not parser.match(TokenType.IDENTIFIER):
            parse_error("Expected variable!", parser)()
        token = parser.get_prev()
        self.name = token
        self.resolved_name = ResolvedName()
        self.value_type = self.resolved_name.value_type

    def gen_code(self, compiler):
        compiler.load_variable(self.resolved_name)

    def resolve(self, resolver):
        self.resolved_name = resolver.lookup_name(self.name.lexeme)
        if self.resolved_name.value_type == ValueType.UNRESOLVED:
            emit_error(f"Reference to undefined identifier! {token_info(self.name)}")()
        self.value_type = self.resolved_name.value_type

    def __str__(self):
        return self.name.lexeme


class AstBuiltin:
    """
    self.function: the builtin function name token
    self.target: the parameter grouping
    self.value_type: the type the function evaluates to
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
        self.value_type = {
            TokenType.TYPE: ValueType.STR,
            TokenType.INT: ValueType.INT,
            TokenType.BOOL: ValueType.BOOL,
            TokenType.NUM: ValueType.NUM,
            TokenType.STR: ValueType.STR,
        }[self.function.token_type]

    def gen_code(self, compiler):
        compiler.apply_builtin(self.function, self.target)

    def resolve(self, resolver):
        self.target.resolve(resolver)
        if (
            self.target.value_type
            not in {
                TokenType.TYPE: ValueType,
                TokenType.INT: [ValueType.NUM, ValueType.INT, ValueType.BOOL],
                TokenType.BOOL: ValueType,
                TokenType.NUM: [ValueType.NUM, ValueType.INT, ValueType.BOOL],
                TokenType.STR: ValueType,
            }[self.function.token_type]
        ):
            emit_error(
                f"Incompatible parameter type {str(self.target.value_type)} for built-in function {token_info(self.function)}!"
            )()

    def __str__(self):
        return str(self.function.token_type) + str(self.target)


class AstAnd:
    """
    self.left: expression evaluating to the left operand
    self.operator: the operator token
    self.right: expression evaluating to the right operand
    self.value_type: the type the expression evaluates to
    """

    def __init__(self, left, parser):
        self.left = left
        parser.consume(TokenType.AND, parse_error("Expected and operator!", parser))
        self.operator = parser.get_prev()
        self.right = AstExpr(parser, precedence=Precedence.AND)
        self.value_type = ValueType.BOOL

    def gen_code(self, compiler):
        compiler.apply_and(self.left, self.right)

    def resolve(self, resolver):
        self.left.resolve(resolver)
        self.right.resolve(resolver)
        if self.left.value_type != ValueType.BOOL:
            emit_error(
                f"Incompatible type {str(self.left.value_type)} for left operand to logic operator {token_info(self.operator)}!"
            )()
        if self.right.value_type != ValueType.BOOL:
            emit_error(
                f"Incompatible type {str(self.right.value_type)} for right operand to logic operator {token_info(self.operator)}!"
            )()

    def __str__(self):
        return str(self.left) + " and " + str(self.right)


class AstOr:
    """
    self.left: expression evaluating to the left operand
    self.operator: the operator token
    self.right: expression evaluating to the right operand
    self.value_type: the type the expression evaluates to
    """

    def __init__(self, left, parser):
        self.left = left
        parser.consume(TokenType.OR, parse_error("Expected and operator!", parser))
        self.operator = parser.get_prev()
        self.right = AstExpr(parser, precedence=Precedence.OR)
        self.value_type = ValueType.BOOL

    def gen_code(self, compiler):
        compiler.apply_or(self.left, self.right)

    def resolve(self, resolver):
        self.left.resolve(resolver)
        self.right.resolve(resolver)
        if self.left.value_type != ValueType.BOOL:
            emit_error(
                f"Incompatible type {str(self.left.value_type)} for left operand to logic operator {token_info(self.operator)}!"
            )()
        if self.right.value_type != ValueType.BOOL:
            emit_error(
                f"Incompatible type {str(self.right.value_type)} for right operand to logic operator {token_info(self.operator)}!"
            )()

    def __str__(self):
        return str(self.left) + " or " + str(self.right)


LEFT_ASSOC_OPS = {TokenType.EQUAL}


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
        TokenType.EQUAL: ParseRule(infix=AstBinary, precedence=Precedence.ASSIGNMENT),
    },
)
