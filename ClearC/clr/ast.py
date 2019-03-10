"""
This module provides classes to compose an AST for Clear programs.
"""
from enum import Enum
from collections import namedtuple, defaultdict
from clr.tokens import TokenType, token_info, tokenize
from clr.errors import parse_error, emit_error
from clr.values import DEBUG
from clr.constants import ClrInt, ClrNum, ClrStr
from clr.compile import Compiler
from clr.resolve import Resolver, ValueType, ResolvedName


class Parser:
    """
    This class wraps a list of tokens with functionality to walk along the list
    and check the token types that occur as well as their values. It is used
    by the AST nodes to build the tree from these tokens.
    """

    def __init__(self, tokens):
        self.index = 0
        self.tokens = tokens

    def get_current(self):
        """This function returns the token currently pointed to."""
        return self.tokens[self.index]

    def get_prev(self):
        """This function returns the token last pointed to."""
        return self.tokens[self.index - 1]

    def current_info(self):
        """This function returns information about the current token as a string."""
        return token_info(self.get_current())

    def prev_info(self):
        """This function returns information about the last token as a string."""
        return token_info(self.get_prev())

    def advance(self):
        """This function moves the parser onto the next token."""
        self.index += 1

    def check(self, token_type):
        """This function returns whether the current token is of the given token type."""
        return self.get_current().token_type == token_type

    def match(self, expected_type):
        """
        This function checks if the current token is of the given token type;
        if it is the parser advances to the next token, otherwise it does not.
        """
        if not self.check(expected_type):
            return False
        self.advance()
        return True

    def consume(self, expected_type, err):
        """
        This method checks if the current token is of the given token type;
        if it is the parser advances to the next token, otherwise the error
        function that was passed is called.
        """
        if not self.match(expected_type):
            err()

    def consume_one(self, possibilities, err):
        """
        This method checks if the current token matches one of the possible
        token types and if so advances the parser, otherwise calling the passed
        error function.
        """
        if not possibilities:
            err()
        elif not self.match(possibilities[0]):
            self.consume_one(possibilities[1:], err)


class Precedence(Enum):

    """
    This class enumerates the possible precedences of operators
    in Clear expressions, matched with numerical values to show the
    ordering and rich comparison protocols.
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
        """This function returns the next precedence above self."""
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
    """This function returns the parse rule associated with the given token."""
    return PRATT_TABLE[token.token_type]


class Ast:
    """
    This class is the root node for a Clear program's AST.
    It representes the following grammar rule:

    Ast : AstDecl* ;
    """

    def __init__(self, parser):
        self.children = []
        while not parser.match(TokenType.EOF):
            self.children.append(AstDecl(parser))
        resolver = Resolver()
        for child in self.children:
            child.resolve(resolver)

    def compile(self):
        """This function walks over the AST and produces bytecode for the program."""
        compiler = Compiler()
        for child in self.children:
            child.gen_code(compiler)
        return compiler.flush_code()

    @staticmethod
    def from_source(source):
        """
        This function takes a string of Clear source; tokenizes it and
        generates an AST by parsing those tokens.
        """
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
    This class is an AST node for a declaration; either a value declaration
    or a statement. It represents the following grammar rule:

    AstDecl : AstValDecl
            | AstStmt
            ;
    """

    def __init__(self, parser):
        if parser.check(TokenType.VAL):
            self.value = AstValDecl(parser)
        else:
            self.value = AstStmt(parser)

    def gen_code(self, compiler):
        """
        This method is a code generation method that accepts a compiler
        instance to visit this node.
        """
        self.value.gen_code(compiler)

    def resolve(self, resolver):
        """
        This method resolves the types and indices of any variables/values
        as children of the node given a resolver instance.
        """
        self.value.resolve(resolver)


class AstValDecl:
    """
    This class is an AST node for a value declaration. It represents
    the following grammar rule:

    AstValDecl : 'val' id '=' AstExpr ';' ;
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
        """
        This method is a code generation method that accepts a compiler
        instance to visit this node.
        """
        compiler.init_value(self.resolved_name, self.value)

    def resolve(self, resolver):
        """
        This method resolves the types and indices of any variables/values
        as children of the node given a resolver instance.
        """
        self.value.resolve(resolver)
        self.resolved_name = resolver.add_name(self.name.lexeme, self.value.value_type)


class AstStmt:
    """
    This class is an AST node for a statement. Either a print statement,
    a simple block, an if statement or an expression statement. It represents
    the following grammar rule:

    AstStmt : AstPrintStmt
            | AstBlock
            | AstIfStmt
            | AstExprStmt
            ;
    """

    def __init__(self, parser):
        if parser.check(TokenType.PRINT):
            self.value = AstPrintStmt(parser)
        elif parser.check(TokenType.LEFT_BRACE):
            self.value = AstBlock(parser)
        elif parser.check(TokenType.IF):
            self.value = AstIfStmt(parser)
        else:
            self.value = AstExprStmt(parser)

    def gen_code(self, compiler):
        """
        This method is a code generation method that accepts a compiler
        instance to visit this node.
        """
        self.value.gen_code(compiler)

    def resolve(self, resolver):
        """
        This method resolves the types and indices of any variables/values
        as children of the node given a resolver instance.
        """
        self.value.resolve(resolver)


class AstPrintStmt:
    """
    This class is an AST node for a print statement. It represents
    the following grammar rule:

    AstPrintStmt : 'print' AstExpr ';' ;
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
        """
        This method is a code generation method that accepts a compiler
        instance to visit this node.
        """
        compiler.print_expression(self.value)

    def resolve(self, resolver):
        """
        This method resolves the types and indices of any variables/values
        as children of the node given a resolver instance.
        """
        if self.value:
            self.value.resolve(resolver)


class AstIfStmt:
    """
    This class is an AST node for an if statement with optional else-if and
    else branches. It represents the following grammar rule:

    AstIfStmt : 'if' AstExpr AstBlock ( 'else' 'if' AstExpr AstBlock )* ( 'else' AstBlock )? ;
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
        """
        This method is a code generation method that accepts a compiler
        instance to visit this node.
        """
        compiler.run_if(self.checks, self.otherwise)

    def resolve(self, resolver):
        """
        This method resolves the types and indices of any variables/values
        as children of the node given a resolver instance.
        """
        for check in self.checks:
            cond, block = check
            cond.resolve(resolver)
            block.resolve(resolver)
        if self.otherwise:
            self.otherwise.resolve(resolver)


class AstExprStmt:
    """
    This class is an AST node for an expression statement where the result of
    the expression is discarded. It represents the following grammar rule:

    AstExprStmt : AstExpr ';' ;
    """

    def __init__(self, parser):
        self.value = AstExpr(parser)
        if not parser.match(TokenType.SEMICOLON):
            parse_error("Expected semicolon to end expression statement!", parser)()

    def gen_code(self, compiler):
        """
        This method is a code generation method that accepts a compiler
        instance to visit this node.
        """
        compiler.drop_expression(self.value)

    def resolve(self, resolver):
        """
        This method resolves the types and indices of any variables/values
        as children of the node given a resolver instance.
        """
        self.value.resolve(resolver)


class AstBlock:
    """
    This class is an AST node for a simple block scoping a list of declarations.
    It represents the following grammar rule:

    AstBlock : '{' AstDecl* '}' ;
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
        """
        This method is a code generation method that accepts a compiler
        instance to visit this node.
        """
        compiler.push_scope()
        for decl in self.declarations:
            decl.gen_code(compiler)
        compiler.pop_scope()

    def resolve(self, resolver):
        """
        This method resolves the types and indices of any variables/values
        as children of the node given a resolver instance.
        """
        resolver.push_scope()
        for decl in self.declarations:
            decl.resolve(resolver)
        resolver.pop_scope()


class AstExpr:
    """
    This class is an AST node representing an expression in the Clear language.
    This involves literals, arithmetic operators with precedence, and the logic
    operators "and" and "or"
    """

    def __init__(self, parser, precedence=Precedence.ASSIGNMENT):
        first_rule = get_rule(parser.get_current())
        self.value = first_rule.prefix(parser)
        while get_rule(parser.get_current()).precedence >= precedence:
            rule = get_rule(parser.get_current())
            self.value = rule.infix(self.value, parser)
        self.value_type = ValueType.UNRESOLVED

    def gen_code(self, compiler):
        """
        This method is a code generation method that accepts a compiler
        instance to visit this node.
        """
        self.value.gen_code(compiler)

    def resolve(self, resolver):
        """
        This method resolves the types and indices of any variables/values
        as children of the node given a resolver instance.
        """
        self.value.resolve(resolver)
        self.value_type = self.value.value_type

    def __str__(self):
        return str(self.value)


class AstGrouping:
    """
    This class is an AST node for a grouped expression, surrounded with parentheses
    to prioritize the expression's precedence.
    """

    def __init__(self, parser):
        if not parser.match(TokenType.LEFT_PAREN):
            parse_error("Expected '(' before expression!", parser)()
        self.value = AstExpr(parser)
        if not parser.match(TokenType.RIGHT_PAREN):
            parse_error("Expected ')' after expression!", parser)()
        self.value_type = ValueType.UNRESOLVED

    def gen_code(self, compiler):
        """
        This method is a code generation method that accepts a compiler
        instance to visit this node.
        """
        self.value.gen_code(compiler)

    def resolve(self, resolver):
        """
        This method resolves the types and indices of any variables/values
        as children of the node given a resolver instance.
        """
        self.value.resolve(resolver)
        self.value_type = self.value.value_type

    def __str__(self):
        return "(" + str(self.value) + ")"


class AstUnary:
    """
    This class is an AST node for a unary operator applied to an expression.
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
        """
        This method is a code generation method that accepts a compiler
        instance to visit this node.
        """
        compiler.apply_unary(self.operator, self.target)

    def resolve(self, resolver):
        """
        This method resolves the types and indices of any variables/values
        as children of the node given a resolver instance.
        """
        self.target.resolve(resolver)
        if (
            self.target.value_type
            not in {
                TokenType.MINUS: [ValueType.NUM, ValueType.INT],
                TokenType.BANG: [ValueType.BOOL],
            }[self.operator.token_type]
        ):
            emit_error(
                f"Incompatible type {str(self.value_type)} for unary operator"
                "{token_info(self.operator)}!"
            )()
        self.value_type = self.target.value_type

    def __str__(self):
        return str(self.operator.token_type) + str(self.target)


class AstBinary:
    """
    This class is an AST node for a binary operator being applied to two expressions.
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
        """
        This method is a code generation method that accepts a compiler
        instance to visit this node.
        """
        if self.operator.token_type == TokenType.EQUAL:
            # TODO: Handle assignment
            print(f"Assigning {str(self.right)} to {str(self.left)}")
        else:
            compiler.apply_binary(self.operator, self.left, self.right)

    def resolve(self, resolver):
        """
        This method resolves the types and indices of any variables/values
        as children of the node given a resolver instance.
        """
        self.left.resolve(resolver)
        self.right.resolve(resolver)
        if self.left.value_type != self.right.value_type:
            emit_error(
                f"Incompatible operand types"
                "{str(self.left.value_type)} and {str(self.right.value_type)}"
                "for binary operator {token_info(self.operator)}!"
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
                f"Incompatible type {str(self.value_type)} for binary operator"
                "{token_info(self.operator)}!"
            )()
        self.value_type = self.left.value_type

    def __str__(self):
        return str(self.left) + str(self.operator.token_type) + str(self.right)


class AstNumber:
    """
    This class is an AST node for a number or integer literal in Clear.
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
        """
        This method is a code generation method that accepts a compiler
        instance to visit this node.
        """
        compiler.load_constant(self.value)

    def resolve(self, resolver):
        """
        This method resolves the types and indices of any variables/values
        as children of the node given a resolver instance.

        Since this is a leaf node that isn't a variable/value it does nothing.
        """

    def __str__(self):
        return str(self.value)


class AstString:
    """
    This class is an AST node for a string literal in Clear.
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
        """
        This method is a code generation method that accepts a compiler
        instance to visit this node.
        """
        compiler.load_constant(self.value)

    def resolve(self, resolver):
        """
        This method resolves the types and indices of any variables/values
        as children of the node given a resolver instance.

        Since this is a leaf node that isn't a variable/value it does nothing.
        """

    def __str__(self):
        return '"' + str(self.value) + '"'


class AstBoolean:
    """
    This class is an AST node for a boolean literal in Clear.
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
        """
        This method is a code generation method that accepts a compiler
        instance to visit this node.
        """
        compiler.load_boolean(self.value)

    def resolve(self, resolver):
        """
        This method resolves the types and indices of any variables/values
        as children of the node given a resolver instance.

        Since this is a leaf node that isn't a variable/value it does nothing.
        """

    def __str__(self):
        return str(self.value.token_type)


class AstIdent:
    """
    This class is an AST node for an identifier reference within an expression.
    """

    def __init__(self, parser):
        if not parser.match(TokenType.IDENTIFIER):
            parse_error("Expected variable!", parser)()
        token = parser.get_prev()
        self.name = token
        self.resolved_name = ResolvedName()
        self.value_type = self.resolved_name.value_type

    def gen_code(self, compiler):
        """
        This method is a code generation method that accepts a compiler
        instance to visit this node.
        """
        compiler.load_variable(self.resolved_name)

    def resolve(self, resolver):
        """
        This method resolves the types and indices of any variables/values
        as children of the node given a resolver instance.

        Since this is a leaf node it just resolves the identifier of this node.
        """
        self.resolved_name = resolver.lookup_name(self.name.lexeme)
        if self.resolved_name.value_type == ValueType.UNRESOLVED:
            emit_error(f"Reference to undefined identifier! {token_info(self.name)}")()
        self.value_type = self.resolved_name.value_type

    def __str__(self):
        return self.name.lexeme


class AstBuiltin:
    """
    This class is an AST node for applying a built-in Clear function to an expression.
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
        """
        This method is a code generation method that accepts a compiler
        instance to visit this node.
        """
        compiler.apply_builtin(self.function, self.target)

    def resolve(self, resolver):
        """
        This method resolves the types and indices of any variables/values
        as children of the node given a resolver instance.
        """
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
                f"Incompatible parameter type {str(self.target.value_type)} for"
                "built-in function {token_info(self.function)}!"
            )()

    def __str__(self):
        return str(self.function.token_type) + str(self.target)


class AstAnd:
    """
    This class is an AST node for applying the logic "and" operator to two expressions.
    """

    def __init__(self, left, parser):
        self.left = left
        parser.consume(TokenType.AND, parse_error("Expected and operator!", parser))
        self.operator = parser.get_prev()
        self.right = AstExpr(parser, precedence=Precedence.AND)
        self.value_type = ValueType.BOOL

    def gen_code(self, compiler):
        """
        This method is a code generation method that accepts a compiler
        instance to visit this node.
        """
        compiler.apply_and(self.left, self.right)

    def resolve(self, resolver):
        """
        This method resolves the types and indices of any variables/values
        as children of the node given a resolver instance.
        """
        self.left.resolve(resolver)
        self.right.resolve(resolver)
        if self.left.value_type != ValueType.BOOL:
            emit_error(
                f"Incompatible type {str(self.left.value_type)} for left operand to"
                "logic operator {token_info(self.operator)}!"
            )()
        if self.right.value_type != ValueType.BOOL:
            emit_error(
                f"Incompatible type {str(self.right.value_type)} for right operand to"
                "logic operator {token_info(self.operator)}!"
            )()

    def __str__(self):
        return str(self.left) + " and " + str(self.right)


class AstOr:
    """
    This class is an AST node for applying the logic operator "or" to two expressions.
    """

    def __init__(self, left, parser):
        self.left = left
        parser.consume(TokenType.OR, parse_error("Expected and operator!", parser))
        self.operator = parser.get_prev()
        self.right = AstExpr(parser, precedence=Precedence.OR)
        self.value_type = ValueType.BOOL

    def gen_code(self, compiler):
        """
        This method is a code generation method that accepts a compiler
        instance to visit this node.
        """
        compiler.apply_or(self.left, self.right)

    def resolve(self, resolver):
        """
        This method resolves the types and indices of any variables/values
        as children of the node given a resolver instance.
        """
        self.left.resolve(resolver)
        self.right.resolve(resolver)
        if self.left.value_type != ValueType.BOOL:
            emit_error(
                f"Incompatible type {str(self.left.value_type)} for left operand to"
                "logic operator {token_info(self.operator)}!"
            )()
        if self.right.value_type != ValueType.BOOL:
            emit_error(
                f"Incompatible type {str(self.right.value_type)} for right operand to"
                "logic operator {token_info(self.operator)}!"
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
