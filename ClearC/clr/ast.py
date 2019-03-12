"""
This module provides classes to compose an AST for Clear programs.
"""
from enum import Enum
from collections import namedtuple, defaultdict
from clr.tokens import TokenType, token_info, tokenize
from clr.errors import parse_error, emit_error
from clr.values import DEBUG, DEBUG_PPRINT, DONT_RESOLVE
from clr.constants import ClrInt, ClrNum, ClrStr
from clr.compile import Compiler
from clr.resolve import Resolver, ValueType, ResolvedName
from clr.visitor import AstVisitable


def _indent(string):
    return "\n".join(map(lambda line: "    " + line, string.splitlines()))


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


class AstNode:
    """
    This class provides default behaviour for AST nodes to give general info about the node.
    """

    def __init__(self, parser):
        self.token = parser.get_current()
        self.returns = False
        self.value_type = ValueType.UNRESOLVED

    def get_info(self):
        """
        This method returns info about the start of this node.
        """
        return token_info(self.token)


class Ast(AstVisitable, AstNode):
    """
    This class is the root node for a Clear program's AST.
    It representes the following grammar rule:

    Ast : AstDecl* ;
    """

    def __init__(self, parser):
        super().__init__(parser)
        self.children = []
        while not parser.match(TokenType.EOF):
            self.children.append(AstDecl(parser))
        if not DONT_RESOLVE:
            if DEBUG:
                print("Resolving:")
            resolver = Resolver()
            self.accept(resolver)
        if DEBUG_PPRINT:
            print("AST pretty print:")
            print(str(self))

    def __str__(self):
        return "\n".join(map(str, self.children))

    def compile(self):
        """This function walks over the AST and produces bytecode for the program."""
        if DEBUG:
            print("Compiling:")
        compiler = Compiler()
        self.accept(compiler)
        return compiler.flush_code()

    def accept(self, visitor):
        for child in self.children:
            child.accept(visitor)

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


class AstDecl(AstVisitable, AstNode):
    """
    This class is an AST node for a declaration; either a value declaration
    or a statement. It represents the following grammar rule:

    AstDecl : AstValDecl
            | AstFuncDecl
            | AstStmt
            ;
    """

    def __init__(self, parser):
        super().__init__(parser)
        if parser.check(TokenType.VAL) or parser.check(TokenType.VAR):
            self.value = AstValDecl(parser)
        elif parser.check(TokenType.FUNC):
            self.value = AstFuncDecl(parser)
        else:
            self.value = AstStmt(parser)
        self.token = self.value.token

    def __str__(self):
        return str(self.value)

    def accept(self, visitor):
        visitor.visit_decl(self)


class AstValDecl(AstVisitable, AstNode):
    """
    This class is an AST node for a value declaration. It represents
    the following grammar rule:

    AstValDecl : ('val' | 'var') AstIdent '=' AstExpr ';' ;
    """

    def __init__(self, parser):
        super().__init__(parser)
        parser.consume_one(
            [TokenType.VAL, TokenType.VAR],
            parse_error("Expected value declaration!", parser),
        )
        mutable = parser.get_prev().token_type == TokenType.VAR
        parser.consume(
            TokenType.IDENTIFIER, parse_error("Expected value name!", parser)
        )
        self.name = parser.get_prev()
        self.token = self.name
        parser.consume(
            TokenType.EQUAL, parse_error("Expected '=' for value initializer!", parser)
        )
        self.value = AstExpr(parser)
        parser.consume(
            TokenType.SEMICOLON,
            parse_error("Expected semicolon after value declaration!", parser),
        )
        self.resolved_name = ResolvedName(is_mutable=mutable)

    def __str__(self):
        return (
            ("var " if self.resolved_name.is_mutable else "val ")
            + self.name.lexeme
            + " = "
            + str(self.value)
            + ";"
        )

    def accept(self, visitor):
        visitor.visit_val_decl(self)


class AstParams(AstNode):
    """
    This class is an AST node for the parameter list of a function. It represents
    the following grammar rule:

    AstParams : '(' ( AstType AstIdent ( ',' AstType AstIdent )* )? ')' ;
    """

    def __init__(self, parser):
        super().__init__(parser)
        parser.consume(
            TokenType.LEFT_PAREN, parse_error("Expected parameter list!", parser)
        )
        self.pairs = []
        while not parser.match(TokenType.RIGHT_PAREN):
            type_id = AstType(parser)
            parser.consume(
                TokenType.IDENTIFIER, parse_error("Expected parameter name!", parser)
            )
            name_id = parser.get_prev()
            self.pairs.append((type_id, name_id))
            if not parser.check(TokenType.RIGHT_PAREN):
                parser.consume(
                    TokenType.COMMA,
                    parse_error("Expected comma to delimit parameters!", parser),
                )

    def __str__(self):
        return (
            "("
            + ", ".join(map(lambda pair: " ".join(map(str, pair)), self.pairs))
            + ")"
        )


class AstFuncDecl(AstVisitable, AstNode):
    """
    This class is an AST node for a function delcaration. It represents
    the following grammar rule:

    AstFuncDecl : 'func' AstIdent '(' params? ')' AstBlock ;
    """

    def __init__(self, parser):
        super().__init__(parser)
        parser.consume(
            TokenType.FUNC, parse_error("Expected function declaration!", parser)
        )
        parser.consume(
            TokenType.IDENTIFIER, parse_error("Expected function name!", parser)
        )
        self.name = parser.get_prev()
        self.token = self.name
        self.params = AstParams(parser)
        self.block = AstBlock(parser)
        self.resolved_name = ResolvedName()
        self.return_type = ValueType.UNRESOLVED

    def __str__(self):
        return "func " + str(self.name) + str(self.params) + " " + str(self.block)

    def accept(self, visitor):
        visitor.visit_func_decl(self)


class AstStmt(AstVisitable, AstNode):
    """
    This class is an AST node for a statement. Either a print statement,
    a simple block, an if statement or an expression statement. It represents
    the following grammar rule:

    AstStmt : AstPrintStmt
            | AstBlock
            | AstIfStmt
            | AstExprStmt
            | AstRetStmt
            ;
    """

    def __init__(self, parser):
        super().__init__(parser)
        if parser.check(TokenType.PRINT):
            self.value = AstPrintStmt(parser)
        elif parser.check(TokenType.LEFT_BRACE):
            self.value = AstBlock(parser)
        elif parser.check(TokenType.IF):
            self.value = AstIfStmt(parser)
        elif parser.check(TokenType.RETURN):
            self.value = AstRetStmt(parser)
        else:
            self.value = AstExprStmt(parser)
        self.token = self.value.token

    def __str__(self):
        return str(self.value)

    def accept(self, visitor):
        visitor.visit_stmt(self)


class AstPrintStmt(AstVisitable, AstNode):
    """
    This class is an AST node for a print statement. It represents
    the following grammar rule:

    AstPrintStmt : 'print' AstExpr ';' ;
    """

    def __init__(self, parser):
        super().__init__(parser)
        parser.consume(
            TokenType.PRINT, parse_error("Expected print statement!", parser)
        )
        if not parser.match(TokenType.SEMICOLON):
            self.value = AstExpr(parser)
            parser.consume(
                TokenType.SEMICOLON,
                parse_error("Expected semicolon for print statement!", parser),
            )
        else:
            self.value = None

    def __str__(self):
        return "print " + str(self.value) + ";"

    def accept(self, visitor):
        visitor.visit_print_stmt(self)


class AstIfStmt(AstVisitable, AstNode):
    """
    This class is an AST node for an if statement with optional else-if and
    else branches. It represents the following grammar rule:

    AstIfStmt : 'if' AstExpr AstBlock ( 'else' 'if' AstExpr AstBlock )* ( 'else' AstBlock )? ;
    """

    def __init__(self, parser):
        super().__init__(parser)
        parser.consume(TokenType.IF, parse_error("Expected if statement!", parser))
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

    def __str__(self):
        result = ""
        first = True
        for cond, block in self.checks:
            if first:
                result += "if "
                first = False
            else:
                result += "else if "
            result += str(cond) + " " + str(block) + " "
        if self.otherwise:
            result += "else " + str(self.otherwise)
        return result + "\n"

    def accept(self, visitor):
        visitor.visit_if_stmt(self)


class AstRetStmt(AstVisitable, AstNode):
    """
    This class is an AST node for a return statement within a function. It represents
    the following grammar rule:

    AstRetStmt : 'return' AstExpr ';' ;
    """

    def __init__(self, parser):
        super().__init__(parser)
        parser.consume(
            TokenType.RETURN, parse_error("Expected return statement!", parser)
        )
        self.value = AstExpr(parser)
        parser.consume(
            TokenType.SEMICOLON,
            parse_error("Expected semicolon after return statement!", parser),
        )

    def __str__(self):
        return "return " + str(self.value) + ";"

    def accept(self, visitor):
        visitor.visit_ret_stmt(self)


class AstExprStmt(AstVisitable, AstNode):
    """
    This class is an AST node for an expression statement where the result of
    the expression is discarded. It represents the following grammar rule:

    AstExprStmt : AstExpr ';' ;
    """

    def __init__(self, parser):
        super().__init__(parser)
        self.value = AstExpr(parser)
        self.token = self.value.token
        parser.consume(
            TokenType.SEMICOLON,
            parse_error("Expected semicolon to end expression statement!", parser),
        )

    def __str__(self):
        return str(self.value) + ";"

    def accept(self, visitor):
        visitor.visit_expr_stmt(self)


class AstBlock(AstVisitable, AstNode):
    """
    This class is an AST node for a simple block scoping a list of declarations.
    It represents the following grammar rule:

    AstBlock : '{' AstDecl* '}' ;
    """

    def __init__(self, parser):
        super().__init__(parser)
        parser.consume(TokenType.LEFT_BRACE, parse_error("Expected block!", parser))
        opener = parser.get_prev()
        self.declarations = []
        while not parser.match(TokenType.RIGHT_BRACE):
            if parser.match(TokenType.EOF):
                emit_error(f"Unclosed block! {token_info(opener)}")()
            decl = AstDecl(parser)
            self.declarations.append(decl)

    def __str__(self):
        return "{\n" + _indent("\n".join(map(str, self.declarations))) + "\n}"

    def accept(self, visitor):
        visitor.start_block_stmt(self)
        for decl in self.declarations:
            decl.accept(visitor)
        visitor.end_block_stmt(self)


class AstExpr(AstVisitable, AstNode):
    """
    This class is an AST node representing an expression in the Clear language.
    This involves literals, arithmetic operators with precedence, and the logic
    operators "and" and "or"
    """

    def __init__(self, parser, precedence=Precedence.ASSIGNMENT):
        super().__init__(parser)
        first_rule = get_rule(parser.get_current())
        self.value = first_rule.prefix(parser)
        while get_rule(parser.get_current()).precedence >= precedence:
            rule = get_rule(parser.get_current())
            self.value = rule.infix(self.value, parser)
        self.is_assignable = self.value.is_assignable
        self.token = self.value.token

    def __str__(self):
        return str(self.value)

    def accept(self, visitor):
        visitor.visit_expr(self)


class AstGrouping(AstVisitable, AstNode):
    """
    This class is an AST node for a grouped expression, surrounded with parentheses
    to prioritize the expression's precedence.
    """

    def __init__(self, parser):
        super().__init__(parser)
        parser.consume(
            TokenType.LEFT_PAREN, parse_error("Expected '(' before expression!", parser)
        )
        self.value = AstExpr(parser)
        parser.consume(
            TokenType.RIGHT_PAREN, parse_error("Expected ')' after expression!", parser)
        )
        self.is_assignable = self.value.is_assignable

    def __str__(self):
        return "(" + str(self.value) + ")"

    def accept(self, visitor):
        visitor.visit_expr(self)


class AstUnary(AstVisitable, AstNode):
    """
    This class is an AST node for a unary operator applied to an expression.
    """

    def __init__(self, parser):
        super().__init__(parser)
        parser.consume_one(
            [TokenType.MINUS, TokenType.BANG],
            parse_error("Expected unary operator!", parser),
        )
        self.operator = parser.get_prev()
        self.target = AstExpr(parser, precedence=Precedence.UNARY)
        self.is_assignable = False

    def __str__(self):
        return str(self.operator.token_type) + str(self.target)

    def accept(self, visitor):
        visitor.visit_unary_expr(self)


class AstBinary(AstVisitable, AstNode):
    """
    This class is an AST node for a binary operator being applied to two expressions.
    """

    def __init__(self, left, parser):
        super().__init__(parser)
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
        self.token = self.operator
        prec = get_rule(self.operator).precedence
        if self.operator.token_type not in LEFT_ASSOC_OPS:
            prec = prec.next()
        self.right = AstExpr(parser, precedence=prec)
        self.is_assignable = False

    def __str__(self):
        return (
            str(self.left) + " " + str(self.operator.token_type) + " " + str(self.right)
        )

    def accept(self, visitor):
        visitor.visit_binary_expr(self)


class AstNumber(AstVisitable, AstNode):
    """
    This class is an AST node for a number or integer literal in Clear.
    """

    def __init__(self, parser):
        super().__init__(parser)
        parser.consume(TokenType.NUMBER, parse_error("Expected number!", parser))
        if parser.match(TokenType.INTEGER_SUFFIX):
            try:
                self.value = ClrInt(self.token.lexeme)
                self.value_type = ValueType.INT
            except ValueError:
                parse_error("Integer literal must be an integer!", parser)()
        else:
            try:
                self.value = ClrNum(self.token.lexeme)
                self.value_type = ValueType.NUM
            except ValueError:
                parse_error("Number literal must be a number!", parser)()
        self.is_assignable = False

    def __str__(self):
        return str(self.value)

    def accept(self, visitor):
        visitor.visit_constant_expr(self)


class AstString(AstVisitable, AstNode):
    """
    This class is an AST node for a string literal in Clear.
    """

    def __init__(self, parser):
        super().__init__(parser)
        parser.consume(TokenType.STRING, parse_error("Expected string!", parser))
        total = [self.token]
        while parser.match(TokenType.STRING):
            total.append(parser.get_prev())
        joined = '"'.join(map(lambda t: t.lexeme[1:-1], total))
        self.value = ClrStr(joined)
        self.value_type = ValueType.STR
        self.is_assignable = False

    def __str__(self):
        return '"' + str(self.value) + '"'

    def accept(self, visitor):
        visitor.visit_constant_expr(self)


class AstBoolean(AstVisitable, AstNode):
    """
    This class is an AST node for a boolean literal in Clear.
    """

    def __init__(self, parser):
        super().__init__(parser)
        parser.consume_one(
            [TokenType.TRUE, TokenType.FALSE],
            parse_error("Expected boolean literal!", parser),
        )
        self.value = parser.get_prev().token_type == TokenType.TRUE
        self.value_type = ValueType.BOOL
        self.is_assignable = False

    def __str__(self):
        return str("true" if self.value else "false")

    def accept(self, visitor):
        visitor.visit_boolean_expr(self)


class AstIdent(AstVisitable, AstNode):
    """
    This class is an AST node for an identifier reference within an expression.
    """

    def __init__(self, parser):
        super().__init__(parser)
        parser.consume(TokenType.IDENTIFIER, parse_error("Expected variable!", parser))
        self.name = self.token
        self.resolved_name = ResolvedName()
        self.value_type = self.resolved_name.value_type
        self.is_assignable = self.resolved_name.is_mutable

    def __str__(self):
        return self.name.lexeme

    def accept(self, visitor):
        visitor.visit_ident_expr(self)


class AstType(AstVisitable, AstNode):
    """
    This class is an AST node for a built-in type.
    """

    def __init__(self, parser):
        super().__init__(parser)
        parser.consume_one(
            [TokenType.INT, TokenType.BOOL, TokenType.NUM, TokenType.STR],
            parse_error("Expected builtin function!", parser),
        )
        self.value = parser.get_prev()
        self.value_type = {
            TokenType.INT: ValueType.INT,
            TokenType.BOOL: ValueType.BOOL,
            TokenType.NUM: ValueType.NUM,
            TokenType.STR: ValueType.STR,
        }[self.value.token_type]
        self.is_assignable = False

    def __str__(self):
        return str(self.value.token_type)

    def accept(self, visitor):
        visitor.visit_type(self)


class AstBuiltin(AstVisitable, AstNode):
    """
    This class is an AST node for applying a built-in Clear function to an expression.
    """

    def __init__(self, parser):
        super().__init__(parser)
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
        self.is_assignable = False

    def __str__(self):
        return str(self.function.token_type) + str(self.target)

    def accept(self, visitor):
        visitor.visit_builtin_expr(self)


class AstAnd(AstVisitable, AstNode):
    """
    This class is an AST node for applying the logic "and" operator to two expressions.
    """

    def __init__(self, left, parser):
        super().__init__(parser)
        self.left = left
        parser.consume(TokenType.AND, parse_error("Expected and operator!", parser))
        self.operator = parser.get_prev()
        self.token = self.operator
        self.right = AstExpr(parser, precedence=Precedence.AND)
        self.value_type = ValueType.BOOL
        self.is_assignable = False

    def __str__(self):
        return str(self.left) + " and " + str(self.right)

    def accept(self, visitor):
        visitor.visit_and_expr(self)


class AstOr(AstVisitable, AstNode):
    """
    This class is an AST node for applying the logic operator "or" to two expressions.
    """

    def __init__(self, left, parser):
        super().__init__(parser)
        self.left = left
        parser.consume(TokenType.OR, parse_error("Expected and operator!", parser))
        self.operator = parser.get_prev()
        self.token = self.operator
        self.right = AstExpr(parser, precedence=Precedence.OR)
        self.value_type = ValueType.BOOL
        self.is_assignable = False

    def __str__(self):
        return str(self.left) + " or " + str(self.right)

    def accept(self, visitor):
        visitor.visit_or_expr(self)


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
