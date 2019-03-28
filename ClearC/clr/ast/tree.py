import itertools
from enum import Enum
from collections import defaultdict, namedtuple
from clr.tokens import TokenType, token_info, tokenize
from clr.values import DEBUG, OpCode
from clr.errors import parse_error, emit_error
from clr.constants import ClrStr, ClrNum, ClrInt, ClrUint, Constants
from clr.assemble import assembled_size
from clr.ast.visitor import DeclVisitor
from clr.ast.type_annotations import (
    TypeAnnotation,
    TypeAnnotationType,
    FunctionTypeAnnotation,
    INT_TYPE,
    NUM_TYPE,
    STR_TYPE,
    BOOL_TYPE,
    ANY_TYPE,
    SIMPLE_TYPES,
)
from clr.ast.return_annotations import ReturnAnnotation, ReturnAnnotationType
from clr.ast.index_annotations import IndexAnnotationType, IndexAnnotation
from clr.ast.parser import Parser


Builtin = namedtuple("Builtin", ("signatures", "opcode", "return_type"))

BUILTINS = {
    "clock": Builtin(signatures=[[]], opcode=OpCode.CLOCK, return_type=NUM_TYPE),
    "int": Builtin(
        signatures=[[INT_TYPE], [NUM_TYPE], [BOOL_TYPE]],
        opcode=OpCode.INT,
        return_type=INT_TYPE,
    ),
    "num": Builtin(
        signatures=[[INT_TYPE], [NUM_TYPE], [BOOL_TYPE]],
        opcode=OpCode.NUM,
        return_type=NUM_TYPE,
    ),
    "str": Builtin(
        signatures=[[INT_TYPE], [NUM_TYPE], [STR_TYPE], [BOOL_TYPE]],
        opcode=OpCode.STR,
        return_type=STR_TYPE,
    ),
    "bool": Builtin(
        signatures=[[INT_TYPE], [NUM_TYPE], [BOOL_TYPE]],
        opcode=OpCode.BOOL,
        return_type=BOOL_TYPE,
    ),
}


class SimpleType:
    def __init__(self, parser):
        err = parse_error("Expected simple type!", parser)
        parser.consume(TokenType.IDENTIFIER, err)
        if parser.get_prev().lexeme not in SIMPLE_TYPES:
            err()
        self.token = parser.get_prev()
        self.as_annotation = SIMPLE_TYPES[self.token.lexeme]


class FunctionType:
    def __init__(self, parser):
        parser.consume(TokenType.FUNC, parse_error("Expected function type!", parser))
        parser.consume(
            TokenType.LEFT_PAREN, parse_error("Expected parameter types!", parser)
        )
        self.params = []
        while not parser.match(TokenType.RIGHT_PAREN):
            param_type = parse_type(parser)
            self.params.append(param_type)
            if not parser.check(TokenType.RIGHT_PAREN):
                parser.consume(
                    TokenType.COMMA,
                    parse_error("Expected comma to delimit parameters!", parser),
                )
        self.return_type = parse_type(parser)
        self.as_annotation = FunctionTypeAnnotation(
            return_type=self.return_type.as_annotation,
            signature=list(map(lambda param: param.as_annotation, self.params)),
        )


def parse_type(parser):
    if parser.get_current().lexeme in SIMPLE_TYPES:
        return SimpleType(parser)
    if parser.get_current().token_type == TokenType.FUNC:
        return FunctionType(parser)
    parse_error("Expected type!", parser)()


class Ast:
    def __init__(self, parser):
        self.children = []
        while not parser.match(TokenType.EOF):
            decl = parse_decl(parser)
            self.children.append(decl)

        self.accept(TypeResolver())
        if DEBUG:
            print("Finished resolving")

        self.accept(Indexer())
        if DEBUG:
            print("Finished indexing")

    def compile(self):
        compiler = Compiler()
        self.accept(compiler)
        if DEBUG:
            print("Finished compiling")
        return compiler.flush_code()

    def accept(self, decl_visitor):
        for child in self.children:
            child.accept(decl_visitor)

    @staticmethod
    def from_source(source):
        tokens = tokenize(source)
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
        lambda parser: parse_error("Expected expression!", parser)(),
        lambda left, parser: parse_error("Expected expression!", parser)(),
        Precedence.NONE,
    ),
)


def get_rule(token):
    return PRATT_TABLE[token.token_type]


def parse_expr(parser, precedence=Precedence.ASSIGNMENT):
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
    parser.consume(
        TokenType.LEFT_PAREN, parse_error("Expected '(' before expression!", parser)
    )
    value = parse_expr(parser)
    parser.consume(
        TokenType.RIGHT_PAREN, parse_error("Expected ')' after expression!", parser)
    )
    return value


class ExprNode:
    def __init__(self):
        self.type_annotation = TypeAnnotation()
        self.assignable = False


class CallExpr(ExprNode):
    def __init__(self, left, parser):
        super().__init__()
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
        expr_visitor.visit_call_expr(self)


class UnaryExpr(ExprNode):
    def __init__(self, parser):
        super().__init__()
        parser.consume_one(UNARY_OPS, parse_error("Expected unary operator!", parser))
        self.operator = parser.get_prev()
        self.target = parse_expr(parser, precedence=Precedence.UNARY)

    def accept(self, expr_visitor):
        expr_visitor.visit_unary_expr(self)


class BinaryExpr(ExprNode):
    def __init__(self, left, parser):
        super().__init__()
        self.left = left
        parser.consume_one(BINARY_OPS, parse_error("Expected binary operator!", parser))
        self.operator = parser.get_prev()
        precedence = get_rule(self.operator).precedence
        # Right-associative operations bind to the right including repeated operations,
        # left-associative operations don't
        if self.operator.token_type not in LEFT_ASSOC_OPS:
            precedence = precedence.next()
        self.right = parse_expr(parser, precedence)

    def accept(self, expr_visitor):
        expr_visitor.visit_binary_expr(self)


class AndExpr(ExprNode):
    def __init__(self, left, parser):
        super().__init__()
        self.left = left
        parser.consume(TokenType.AND, parse_error("Expected and operator!", parser))
        self.operator = parser.get_prev()
        # and acts like a normal right-associative binary operator when parsing
        self.right = parse_expr(parser, precedence=Precedence.AND)

    def accept(self, expr_visitor):
        expr_visitor.visit_and_expr(self)


class OrExpr(ExprNode):
    def __init__(self, left, parser):
        super().__init__()
        self.left = left
        parser.consume(TokenType.OR, parse_error("Expected or operator!", parser))
        self.operator = parser.get_prev()
        # or acts like a normal right-associative binary operator when parsing
        self.right = parse_expr(parser, precedence=Precedence.OR)

    def accept(self, expr_visitor):
        expr_visitor.visit_or_expr(self)


class IdentExpr(ExprNode):
    def __init__(self, parser):
        super().__init__()
        parser.consume(TokenType.IDENTIFIER, parse_error("Expected variable!", parser))
        self.name = parser.get_prev()
        # Identifiers have indices, by default it is unresolved
        self.index_annotation = IndexAnnotation()

    def accept(self, expr_visitor):
        expr_visitor.visit_ident_expr(self)


class StringExpr(ExprNode):
    def __init__(self, parser):
        super().__init__()
        parser.consume(TokenType.STRING, parse_error("Expected string!", parser))
        total = [parser.get_prev()]
        # Adjacent string literals are combined and joined with " to allow effective escaping,
        # don't judge me
        while parser.match(TokenType.STRING):
            total.append(parser.get_prev())
        joined = '"'.join(map(lambda t: t.lexeme[1:-1], total))
        self.value = ClrStr(joined)

    def accept(self, expr_visitor):
        expr_visitor.visit_string_expr(self)


class NumberExpr(ExprNode):
    def __init__(self, parser):
        super().__init__()
        parser.consume(TokenType.NUMBER, parse_error("Expected number!", parser))
        lexeme = parser.get_prev().lexeme
        if parser.match(TokenType.INTEGER_SUFFIX):
            try:
                self.value = ClrInt(lexeme)
                self.integral = True
            except ValueError:
                parse_error("Integer literal must be an integer!", parser)()
        else:
            try:
                self.value = ClrNum(lexeme)
                self.integral = False
            except ValueError:
                parse_error("Number literal must be a number!", parser)()

    def accept(self, expr_visitor):
        expr_visitor.visit_number_expr(self)


class BooleanExpr(ExprNode):
    def __init__(self, parser):
        super().__init__()
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


def parse_stmt(parser):
    if parser.check(TokenType.PRINT):
        return PrintStmt(parser)
    if parser.check(TokenType.LEFT_BRACE):
        return BlockStmt(parser)
    if parser.check(TokenType.IF):
        return IfStmt(parser)
    if parser.check(TokenType.WHILE):
        return WhileStmt(parser)
    if parser.check(TokenType.RETURN):
        return RetStmt(parser)
    return ExprStmt(parser)


class StmtNode:
    def __init__(self, parser):
        self.return_annotation = ReturnAnnotation()
        self.first_token = parser.get_current()


class BlockStmt(StmtNode):
    def __init__(self, parser):
        super().__init__(parser)
        parser.consume(TokenType.LEFT_BRACE, parse_error("Expected block!", parser))
        opener = parser.get_prev()
        self.declarations = []
        while not parser.match(TokenType.RIGHT_BRACE):
            if parser.match(TokenType.EOF):
                emit_error(f"Unclosed block! {token_info(opener)}")()
            decl = parse_decl(parser)
            self.declarations.append(decl)

    def accept(self, stmt_visitor):
        stmt_visitor.visit_block_stmt(self)


class ExprStmt(StmtNode):
    def __init__(self, parser):
        super().__init__(parser)
        self.value = parse_expr(parser)
        parser.consume(
            TokenType.SEMICOLON,
            parse_error("Expected semicolon to end expression statement!", parser),
        )

    def accept(self, stmt_visitor):
        stmt_visitor.visit_expr_stmt(self)


class RetStmt(StmtNode):
    def __init__(self, parser):
        super().__init__(parser)
        parser.consume(
            TokenType.RETURN, parse_error("Expected return statement!", parser)
        )
        self.return_token = parser.get_prev()
        self.value = parse_expr(parser)
        parser.consume(
            TokenType.SEMICOLON,
            parse_error("Expected semicolon after return statement!", parser),
        )

    def accept(self, stmt_visitor):
        stmt_visitor.visit_ret_stmt(self)


class WhileStmt(StmtNode):
    def __init__(self, parser):
        # TODO: Break statements
        super().__init__()
        parser.consume(
            TokenType.WHILE, parse_error("Expected while statement!", parser)
        )
        if not parser.check(TokenType.LEFT_BRACE):
            self.condition = parse_expr(parser)
        else:
            self.condition = None
        self.block = BlockStmt(parser)

    def accept(self, stmt_visitor):
        stmt_visitor.visit_while_stmt(self)


class IfStmt(StmtNode):
    def __init__(self, parser):
        super().__init__(parser)
        parser.consume(TokenType.IF, parse_error("Expected if statement!", parser))
        self.checks = [(parse_expr(parser), BlockStmt(parser))]
        self.otherwise = None
        while parser.match(TokenType.ELSE):
            if parser.match(TokenType.IF):
                other_cond = parse_expr(parser)
                other_block = BlockStmt(parser)
                self.checks.append((other_cond, other_block))
            else:
                self.otherwise = BlockStmt(parser)
                break

    def accept(self, stmt_visitor):
        stmt_visitor.visit_if_stmt(self)


class PrintStmt(StmtNode):
    def __init__(self, parser):
        super().__init__(parser)
        parser.consume(
            TokenType.PRINT, parse_error("Expected print statement!", parser)
        )
        if not parser.match(TokenType.SEMICOLON):
            self.value = parse_expr(parser)
            parser.consume(
                TokenType.SEMICOLON,
                parse_error("Expected semicolon for print statement!", parser),
            )
        else:
            self.value = None

    def accept(self, stmt_visitor):
        stmt_visitor.visit_print_stmt(self)


def parse_decl(parser):
    if parser.check_one(VAL_TOKENS):
        return ValDecl(parser)
    if parser.check(TokenType.FUNC):
        return FuncDecl(parser)
    return parse_stmt(parser)


class DeclNode(StmtNode):
    def __init__(self, parser):
        super().__init__(parser)
        self.index_annotation = IndexAnnotation()


class FuncDecl(DeclNode):
    def __init__(self, parser):
        super().__init__(parser)
        parser.consume(
            TokenType.FUNC, parse_error("Expected function declaration!", parser)
        )
        # Consume the name token
        parser.consume(
            TokenType.IDENTIFIER, parse_error("Expected function name!", parser)
        )
        self.name = parser.get_prev()
        if self.name.lexeme in BUILTINS:
            emit_error(
                f"Invalid identifier name {self.name.lexeme}! This is reserved for the built-in function {self.name.lexeme}(). {token_info(self.name)}"
            )()
        parser.consume(
            TokenType.LEFT_PAREN,
            parse_error("Expected '(' to start function parameters!", parser),
        )
        self.params = []
        # Consume parameters until we hit the closing paren
        while not parser.match(TokenType.RIGHT_PAREN):
            # Consume a type for the parameter
            param_type = parse_type(parser)
            # And then a name for the parameter
            parser.consume(
                TokenType.IDENTIFIER, parse_error("Expected parameter name!", parser)
            )
            param_name = parser.get_prev()
            # Append the parameters as (type, name) tuples
            pair = (param_type, param_name)
            self.params.append(pair)
            # If we haven't hit the end there must be a comma before the next parameter
            if not parser.check(TokenType.RIGHT_PAREN):
                parser.consume(
                    TokenType.COMMA,
                    parse_error("Expected comma to delimit parameters!", parser),
                )
        # Consume the return type
        self.return_type = parse_type(parser)
        # Consume the definition block
        self.block = BlockStmt(parser)
        self.upvalues = []

    def accept(self, decl_visitor):
        decl_visitor.visit_func_decl(self)


class ValDecl(DeclNode):
    def __init__(self, parser):
        super().__init__()
        parser.consume_one(
            VAL_TOKENS, parse_error("Expected value declaration!", parser)
        )
        self.mutable = parser.get_prev().token_type == TokenType.VAR
        # Consume the variable name
        parser.consume(
            TokenType.IDENTIFIER, parse_error("Expected value name!", parser)
        )
        self.name = parser.get_prev()
        if self.name.lexeme in BUILTINS:
            emit_error(
                f"Invalid identifier name {self.name.lexeme}! This is reserved for the built-in function {self.name.lexeme}(). {token_info(self.name)}"
            )()
        parser.consume(
            TokenType.EQUAL, parse_error("Expected '=' for value initializer!", parser)
        )
        # Consume the expression to initialize with
        self.initializer = parse_expr(parser)
        parser.consume(
            TokenType.SEMICOLON,
            parse_error("Expected semicolon after value declaration!", parser),
        )

    def accept(self, decl_visitor):
        decl_visitor.visit_val_decl(self)


VAL_TOKENS = {TokenType.VAL, TokenType.VAR}


class Indexer(DeclVisitor):
    def __init__(self):
        self.scopes = [defaultdict(IndexAnnotation)]
        self.level = 0
        self.local_index = 0
        self.global_index = 0
        self.is_function = False

    def lookup_name(self, name):
        lookback = 0
        # Keep looking back up to the global scope
        while lookback <= self.level:
            result = self.scopes[self.level - lookback][name]
            lookback += 1
            # If the scope containes a resolved index for thei name we're done
            if result.kind != IndexAnnotationType.UNRESOLVED:
                if DEBUG:
                    print(f"Found {name} with index {result}")
                break
        # If no resolved name was found the returned index is unresolved
        return result

    def _declare_name(self, name):
        prev = self.lookup_name(name)
        # If the name already was not found as already declared make it a new index
        if prev.kind == IndexAnnotationType.UNRESOLVED:
            if self.level > 0:
                idx = self.local_index
                self.local_index += 1
                kind = IndexAnnotationType.LOCAL
            else:
                idx = self.global_index
                self.global_index += 1
                kind = IndexAnnotationType.GLOBAL
        else:
            # If it was already declared use the old value directly
            idx = prev.value
            kind = prev.kind
        result = IndexAnnotation(kind, idx)
        if DEBUG:
            print(f"Declared {name} as {result}")
        self.scopes[self.level][name] = result
        return result

    def start_scope(self):
        super().start_scope()
        self.scopes.append(defaultdict(IndexAnnotation))
        self.level += 1

    def end_scope(self):
        super().end_scope()
        if self.level == 0:
            emit_error("Cannot end the global scope!")()
        else:
            popped = self.scopes[self.level]
            popped_indices = [
                index
                for index in popped.values()
                if index.kind != IndexAnnotationType.UNRESOLVED
            ]
            # If there are resolved indices that went out of scope, reset back so that they can be
            # re-used
            if popped_indices:
                self.local_index = min(map(lambda index: index.value, popped_indices))
                if DEBUG:
                    print(f"After popping local index is {self.local_index}")
        # Remove the popped scope
        del self.scopes[self.level]
        self.level -= 1

    def visit_call_expr(self, node):
        if isinstance(node.target, IdentExpr) and node.target.name.lexeme in BUILTINS:
            # If it's a built-in don't call super as we don't want to lookup the name
            for arg in node.arguments:
                arg.accept(self)
        else:
            super().visit_call_expr(node)

    def visit_ident_expr(self, node):
        super().visit_ident_expr(node)
        node.index_annotation = self.lookup_name(node.name.lexeme)
        if node.index_annotation.kind == IndexAnnotationType.UNRESOLVED:
            emit_error(f"Reference to undefined identifier! {token_info(node.name)}")()
        elif DEBUG:
            print(f"Set index for {token_info(node.name)} as {node.index_annotation}")

    def visit_val_decl(self, node):
        super().visit_val_decl(node)
        node.index_annotation = self._declare_name(node.name.lexeme)

    def visit_func_decl(self, node):
        # No super as we handle the params / scoping
        node.index_annotation = self._declare_name(node.name.lexeme)
        function = FunctionIndexer(self)
        for _, name in node.params:
            function.add_param(name.lexeme)
        for decl in node.block.declarations:
            decl.accept(function)
        node.upvalues.extend(function.upvalues)


class FunctionIndexer(Indexer):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.scopes.append(defaultdict(IndexAnnotation))
        # Default scope is not the global scope in a function
        self.level += 1
        self.params = []
        self.upvalues = []
        self.is_function = True

    def add_param(self, name):
        index = len(self.params)
        pair = (name, IndexAnnotation(kind=IndexAnnotationType.PARAM, value=index))
        self.params.append(pair)

    def lookup_name(self, name):
        result = super().lookup_name(name)
        if result.kind == IndexAnnotationType.UNRESOLVED:
            # If it wasn't found look for it as a param
            for param_name, param_index in self.params:
                if param_name == name:
                    result = param_index
        if result.kind == IndexAnnotationType.UNRESOLVED:
            # If it still isn't found look for it as an upvalue
            lookup = self.parent.lookup_name(name)
            if lookup.kind != IndexAnnotationType.UNRESOLVED:
                if DEBUG:
                    print(f"upvalue candidate: {lookup}")
                if lookup.kind == IndexAnnotationType.GLOBAL:
                    # Globals can be referenced normally
                    result = lookup
                else:
                    upvalue_index = len(self.upvalues)
                    self.upvalues.append(lookup)
                    result = IndexAnnotation(IndexAnnotationType.UPVALUE, upvalue_index)
        return result


TypeInfo = namedtuple(
    "TypeInfo", ("annotation", "assignable"), defaults=(TypeAnnotation(), False)
)


class TypeResolver(DeclVisitor):
    def __init__(self):
        self.scopes = [defaultdict(TypeInfo)]
        self.expected_returns = []
        self.level = 0

    def _declare_name(self, name, type_annotation, assignable=False):
        self.scopes[self.level][name] = TypeInfo(type_annotation, assignable)

    def _lookup_name(self, name):
        result = TypeInfo()
        lookback = 0
        while lookback <= self.level:
            result = self.scopes[self.level - lookback][name]
            lookback += 1
            if result.annotation.kind != TypeAnnotationType.UNRESOLVED:
                break
        return result

    def start_scope(self):
        super().start_scope()
        self.scopes.append(defaultdict(TypeInfo))
        self.level += 1

    def end_scope(self):
        super().end_scope()
        del self.scopes[self.level]
        self.level -= 1

    def visit_call_expr(self, node):
        if isinstance(node.target, IdentExpr) and node.target.name.lexeme in BUILTINS:
            # If it's a built-in don't call super() as we don't evaluate the target
            for arg in node.arguments:
                arg.accept(self)
            builtin = BUILTINS[node.target.name.lexeme]
            type_list = list(map(lambda pair: pair.type_annotation, node.arguments))
            if type_list not in builtin.signatures:
                emit_error(
                    f"Built-in function {token_info(node.target.name)} cannot take arguments of type {str(type_list)}!"
                )()
            node.type_annotation = builtin.return_type
        else:
            super().visit_call_expr(node)
            function_type = node.target.type_annotation
            if function_type.kind != TypeAnnotationType.FUNCTION:
                emit_error(
                    f"Attempt to call a non-callable object {token_info(node.target.name)}!"
                )()
            passed_signature = list(
                map(lambda arg: arg.type_annotation, node.arguments)
            )
            args = "(" + ", ".join(map(str, passed_signature)) + ")"
            if passed_signature != function_type.signature:
                emit_error(
                    f"Could not find signature for function {token_info(node.target.name)} matching provided argument list {args}!"
                )()
            node.type_annotation = function_type.return_type

    def visit_unary_expr(self, node):
        super().visit_unary_expr(node)
        target_type = node.target.type_annotation
        if (
            target_type
            not in {TokenType.MINUS: [NUM_TYPE, INT_TYPE], TokenType.BANG: [BOOL_TYPE]}[
                node.operator.token_type
            ]
        ):
            emit_error(
                f"Incompatible operand type {target_type} for unary operator {token_info(node.operator)}!"
            )()
        node.type_annotation = target_type

    def visit_binary_expr(self, node):
        super().visit_binary_expr(node)
        left_type = node.left.type_annotation
        right_type = node.right.type_annotation
        if left_type.kind != right_type.kind:
            emit_error(
                f"Incompatible operand types {left_type} and {right_type} for binary operator {token_info(node.operator)}!"
            )()
        if (
            left_type
            not in {
                TokenType.PLUS: [NUM_TYPE, INT_TYPE, STR_TYPE],
                TokenType.MINUS: [NUM_TYPE, INT_TYPE],
                TokenType.STAR: [NUM_TYPE, INT_TYPE],
                TokenType.SLASH: [NUM_TYPE],
                TokenType.EQUAL_EQUAL: ANY_TYPE,
                TokenType.BANG_EQUAL: ANY_TYPE,
                TokenType.LESS: [NUM_TYPE, INT_TYPE],
                TokenType.GREATER_EQUAL: [NUM_TYPE, INT_TYPE],
                TokenType.GREATER: [NUM_TYPE, INT_TYPE],
                TokenType.LESS_EQUAL: [NUM_TYPE, INT_TYPE],
                TokenType.EQUAL: ANY_TYPE,
            }[node.operator.token_type]
        ):
            emit_error(
                f"Incompatible operand type {left_type} for binary operator {token_info(node.operator)}!"
            )()
        if node.operator.token_type == TokenType.EQUAL and not node.left.assignable:
            emit_error(f"Unassignable expression {node.left}!")()
        node.type_annotation = left_type

    def visit_and_expr(self, node):
        super().visit_and_expr(node)
        left_type = node.left.type_annotation
        right_type = node.right.type_annotation
        if left_type != BOOL_TYPE:
            emit_error(
                f"Incompatible type {left_type} for left operand to logic operator {token_info(node.operator)}!"
            )()
        if right_type != BOOL_TYPE:
            emit_error(
                f"Incompatible type {right_type} for right operand to logic operator {token_info(node.operator)}!"
            )()

    def visit_or_expr(self, node):
        super().visit_or_expr(node)
        left_type = node.left.type_annotation
        right_type = node.right.type_annotation
        if left_type != BOOL_TYPE:
            emit_error(
                f"Incompatible type {left_type} for left operand to logic operator {token_info(node.operator)}!"
            )()
        if right_type != BOOL_TYPE:
            emit_error(
                f"Incompatible type {right_type} for right operand to logic operator {token_info(node.operator)}!"
            )()

    def visit_ident_expr(self, node):
        super().visit_ident_expr(node)
        if node.name.lexeme in BUILTINS:
            emit_error(
                f"Invalid identifier name {token_info(node.name)}! This is reserved for the built-in function {node.name.lexeme}."
            )()
        (node.type_annotation, node.assignable) = self._lookup_name(node.name.lexeme)
        if node.type_annotation.kind == TypeAnnotationType.UNRESOLVED:
            emit_error(f"Reference to undefined identifier {token_info(node.name)}!")()

    def visit_string_expr(self, node):
        super().visit_string_expr(node)
        node.type_annotation = STR_TYPE

    def visit_number_expr(self, node):
        super().visit_number_expr(node)
        node.type_annotation = INT_TYPE if node.integral else NUM_TYPE

    def visit_boolean_expr(self, node):
        super().visit_boolean_expr(node)
        node.type_annotation = BOOL_TYPE

    def visit_block_stmt(self, node):
        super().visit_block_stmt(node)
        kind = ReturnAnnotationType.NEVER
        return_type = None
        for decl in node.declarations:
            if kind == ReturnAnnotationType.ALWAYS:
                emit_error(f"Unreachable code {token_info(decl.first_token)}!")()
            if not isinstance(decl, StmtNode):
                continue
            annotation = decl.return_annotation
            if annotation.kind in [
                ReturnAnnotationType.SOMETIMES,
                ReturnAnnotationType.ALWAYS,
            ]:
                kind = annotation.kind
                return_type = annotation.return_type
        node.return_annotation = ReturnAnnotation(kind, return_type)

    def visit_ret_stmt(self, node):
        super().visit_ret_stmt(node)
        if not self.expected_returns:
            emit_error(
                f"Return statement found outside of function {token_info(node.return_token)}!"
            )()
        expected = self.expected_returns[-1]
        if expected != node.value.type_annotation:
            emit_error(
                f"Incompatible return type! Expected {expected} but was given {node.value.type_annotation} at {token_info(node.return_token)}!"
            )()
        node.return_annotation = ReturnAnnotation(ReturnAnnotationType.ALWAYS, expected)

    def visit_while_stmt(self, node):
        super().visit_while_stmt(node)
        node.return_annotation = node.block.return_annotation
        if node.return_annotation.kind == ReturnAnnotationType.ALWAYS:
            node.return_annotation.kind = ReturnAnnotationType.SOMETIMES

    def visit_if_stmt(self, node):
        super().visit_if_stmt(node)
        annotations = map(lambda pair: pair[1].return_annotation, node.checks)
        annotations = itertools.chain(
            annotations,
            [
                node.otherwise.return_annotation
                if node.otherwise is not None
                else ReturnAnnotation()
            ],
        )
        kind = ReturnAnnotationType.NEVER
        if all(
            map(
                lambda annotation: annotation.kind == ReturnAnnotationType.ALWAYS,
                annotations,
            )
        ):
            kind = ReturnAnnotationType.ALWAYS
        elif any(
            map(
                lambda annotation: annotation.kind != ReturnAnnotationType.NEVER,
                annotations,
            )
        ):
            kind = ReturnAnnotationType.SOMETIMES
        returns = [
            annotation.return_type
            for annotation in annotations
            if annotation.kind != ReturnAnnotationType.NEVER
        ]
        return_type = returns[0] if returns else None
        node.return_annotation = ReturnAnnotation(kind, return_type)

    def visit_func_decl(self, node):
        # No super because we handle the params
        # Iterate over the parameters and resolve to types
        arg_types = []
        for param_type, param_name in node.params:
            resolved_type = param_type.as_annotation
            if resolved_type.kind == TypeAnnotationType.UNRESOLVED:
                emit_error(
                    f"Invalid parameter type {param_type} for function {token_info(node.name)}!"
                )()
            arg_types.append(resolved_type)
        # Resolve the return type
        return_type = node.return_type.as_annotation
        # Create an annotation for the function signature
        type_annotation = FunctionTypeAnnotation(
            return_type=return_type, signature=arg_types
        )
        # Declare the function
        self._declare_name(node.name.lexeme, type_annotation)
        # Start the function scope
        self.start_scope()
        # Iterate over the parameters and declare them
        for param_type, param_name in node.params:
            self._declare_name(param_name.lexeme, param_type.as_annotation)
        # Expect return statements for the return type
        self.expected_returns.append(return_type)
        # Define the function by its block
        node.block.accept(self)
        # End the function scope
        self.end_scope()
        # Stop expecting return statements
        del self.expected_returns[-1]
        if node.block.return_annotation.kind != ReturnAnnotationType.ALWAYS:
            emit_error(f"Function does not always return {token_info(node.name)}!")()

    def visit_val_decl(self, node):
        super().visit_val_decl(node)
        type_annotation = node.initializer.type_annotation
        self._declare_name(node.name.lexeme, type_annotation, assignable=node.mutable)


class Program:
    def __init__(self):
        self.code_list = []

    def load_constant(self, index):
        self.code_list.append(OpCode.LOAD_CONST)
        self.code_list.append(index)

    def simple_op(self, opcode):
        self.code_list.append(opcode)

    def define_name(self, index):
        opcode = {
            IndexAnnotationType.GLOBAL: lambda: OpCode.DEFINE_GLOBAL,
            IndexAnnotationType.LOCAL: lambda: OpCode.DEFINE_LOCAL,
            IndexAnnotationType.UPVALUE: lambda: OpCode.SET_UPVALUE,
        }.get(
            index.kind, emit_error(f"Cannot define name with index kind {index.kind}!")
        )()
        self.code_list.append(opcode)
        self.code_list.append(index.value)

    def load_name(self, index):
        opcode = {
            IndexAnnotationType.GLOBAL: lambda: OpCode.LOAD_GLOBAL,
            IndexAnnotationType.LOCAL: lambda: OpCode.LOAD_LOCAL,
            IndexAnnotationType.PARAM: lambda: OpCode.LOAD_PARAM,
            IndexAnnotationType.UPVALUE: lambda: OpCode.LOAD_UPVALUE,
        }.get(index.kind, emit_error(f"Cannot load unresolved name of {index}!"))()
        self.code_list.append(opcode)
        self.code_list.append(index.value)

    def begin_function(self):
        self.code_list.append(OpCode.START_FUNCTION)
        index = len(self.code_list)
        # Insert temporary offset to later be patched
        self.code_list.append(ClrUint(0))
        return index

    def end_function(self, index):
        contained = self.code_list[index + 1 :]
        offset = assembled_size(contained)
        # Patch the previously inserted offset
        self.code_list[index] = ClrUint(offset)

    def make_closure(self, upvalues):
        self.code_list.append(OpCode.CLOSURE)
        self.code_list.append(len(upvalues))
        for upvalue in upvalues:
            if DEBUG:
                print(f"Loading upvalue {upvalue}")
            self.load_name(upvalue)

    def begin_jump(self, conditional=False, leave_value=False):
        self.code_list.append(OpCode.JUMP_IF_NOT if conditional else OpCode.JUMP)
        index = len(self.code_list)
        if DEBUG:
            print(f"Defining a jump from {index}")
        # Insert temporary offset to later be patched
        temp_offset = ClrUint(0)
        self.code_list.append(temp_offset)
        # If there was a condition and we aren't told to leave it pop it from the stack
        if conditional and not leave_value:
            self.code_list.append(OpCode.POP)
        return index, conditional

    def end_jump(self, jump_ref, leave_value=False):
        index, conditional = jump_ref
        contained = self.code_list[index + 1 :]
        offset = assembled_size(contained)
        if DEBUG:
            print(f"Jump from {index} set with offset {offset}")
        # Patch the previously inserted offset
        self.code_list[index] = ClrUint(offset)
        if conditional and not leave_value:
            self.code_list.append(OpCode.POP)

    def begin_loop(self):
        index = len(self.code_list)
        if DEBUG:
            print(f"Loop checkpoint for {index} picked")
        return index

    def loop_back(self, index):
        self.code_list.append(OpCode.LOOP)
        offset_index = len(self.code_list)
        # Insert an offset temporarily to include it when calculating the actual offset.
        self.code_list.append(ClrUint(0))
        contained = self.code_list[index:]
        offset = ClrUint(assembled_size(contained))
        if DEBUG:
            print(f"Loop back to {index} set with offset {offset}")
        self.code_list[offset_index] = offset

    def flush(self):
        return self.code_list


class Compiler(DeclVisitor):
    def __init__(self):
        self.program = Program()
        self.constants = Constants()

    def flush_code(self):
        return self.constants.flush() + self.program.flush()

    def visit_val_decl(self, node):
        super().visit_val_decl(node)
        self.program.define_name(node.index_annotation)

    def visit_func_decl(self, node):
        # No super as we handle scoping
        function = self.program.begin_function()
        for decl in node.block.declarations:
            decl.accept(self)
        self.program.end_function(function)
        self.program.make_closure(node.upvalues)
        # Define the function as the closure value
        self.program.define_name(node.index_annotation)

    def visit_print_stmt(self, node):
        super().visit_print_stmt(node)
        if node.value is None:
            self.program.simple_op(OpCode.PRINT_BLANK)
        else:
            self.program.simple_op(OpCode.PRINT)

    def visit_if_stmt(self, node):
        # No super because we need the jumps in the right place
        # Create a list of jumps that skip to the end once a block completes
        final_jumps = []
        for cond, block in node.checks:
            cond.accept(self)
            # If the condition is false jump to the next block
            jump = self.program.begin_jump(conditional=True)
            block.accept(self)
            # Otherwise jump to the end after the block completes
            final_jumps.append(self.program.begin_jump())
            # The jump to the next block goes after the jump to the end to avoid it
            self.program.end_jump(jump)
        if node.otherwise is not None:
            # If we haven't jumped to the end then all the previous blocks didn't execute so run the
            # else block
            node.otherwise.accept(self)
        for final_jump in final_jumps:
            # All the final jumps end here after everything
            self.program.end_jump(final_jump)

    def visit_while_stmt(self, node):
        # No super because the loop starts before checking the condition
        loop = self.program.begin_loop()
        if node.condition is not None:
            node.condition.accept(self)
            # If there is a condition jump to the end if it's false
            skip_jump = self.program.begin_jump(conditional=True)
        node.block.accept(self)
        # Go back to before the condition to check it again
        self.program.loop_back(loop)
        if node.condition is not None:
            self.program.end_jump(skip_jump)

    def visit_ret_stmt(self, node):
        super().visit_ret_stmt(node)
        self.program.simple_op(OpCode.RETURN)

    def visit_expr_stmt(self, node):
        super().visit_expr_stmt(node)
        self.program.simple_op(OpCode.POP)

    def start_scope(self):
        super().start_scope()
        self.program.simple_op(OpCode.PUSH_SCOPE)

    def end_scope(self):
        super().end_scope()
        self.program.simple_op(OpCode.POP_SCOPE)

    def visit_unary_expr(self, node):
        super().visit_unary_expr(node)
        {
            TokenType.MINUS: lambda: self.program.simple_op(OpCode.NEGATE),
            TokenType.BANG: lambda: self.program.simple_op(OpCode.NOT),
        }.get(
            node.operator.token_type,
            emit_error(f"Unknown unary operator! {token_info(node.operator)}"),
        )()

    def visit_binary_expr(self, node):
        if node.operator.token_type == TokenType.EQUAL:
            # If it's an assignment don't call super as we don't want to evaluate the left hand side
            node.right.accept(self)
            self.program.define_name(node.left.index_annotation)
            if DEBUG:
                print(f"Loading name for {node.left}")
            # Assignment is an expression so we load the assigned value as well
            self.program.load_name(node.left.index_annotation)
        else:
            super().visit_binary_expr(node)
            {
                TokenType.PLUS: lambda: self.program.simple_op(OpCode.ADD),
                TokenType.MINUS: lambda: self.program.simple_op(OpCode.SUBTRACT),
                TokenType.STAR: lambda: self.program.simple_op(OpCode.MULTIPLY),
                TokenType.SLASH: lambda: self.program.simple_op(OpCode.DIVIDE),
                TokenType.EQUAL_EQUAL: lambda: self.program.simple_op(OpCode.EQUAL),
                TokenType.BANG_EQUAL: lambda: self.program.simple_op(OpCode.NEQUAL),
                TokenType.LESS: lambda: self.program.simple_op(OpCode.LESS),
                TokenType.GREATER_EQUAL: lambda: self.program.simple_op(OpCode.NLESS),
                TokenType.GREATER: lambda: self.program.simple_op(OpCode.GREATER),
                TokenType.LESS_EQUAL: lambda: self.program.simple_op(OpCode.NGREATER),
            }.get(
                node.operator.token_type,
                emit_error(f"Unknown binary operator! {token_info(node.operator)}"),
            )()

    def visit_call_expr(self, node):
        if isinstance(node.target, IdentExpr) and node.target.name.lexeme in BUILTINS:
            # Don't call super if it's a built-in because we don't want to evaluate the name
            opcode = BUILTINS[node.target.name.lexeme].opcode
            for arg in node.arguments:
                arg.accept(self)
            self.program.simple_op(opcode)
        else:
            super().visit_call_expr(node)
            self.program.simple_op(OpCode.CALL)
            self.program.simple_op(len(node.arguments))

    def _visit_constant_expr(self, node):
        const_index = self.constants.add(node.value)
        self.program.load_constant(const_index)

    def visit_number_expr(self, node):
        super().visit_number_expr(node)
        self._visit_constant_expr(node)

    def visit_string_expr(self, node):
        super().visit_string_expr(node)
        self._visit_constant_expr(node)

    def visit_boolean_expr(self, node):
        super().visit_boolean_expr(node)
        self.program.simple_op(OpCode.TRUE if node.value else OpCode.FALSE)

    def visit_ident_expr(self, node):
        super().visit_ident_expr(node)
        if DEBUG:
            print(f"Loading name for {node}")
        self.program.load_name(node.index_annotation)

    def visit_and_expr(self, node):
        # No super because we need to put the jumps in the right place
        node.left.accept(self)
        short_circuit = self.program.begin_jump(conditional=True)
        # If the first is false jump past the second, if we don't jump pop the value to replace
        # with the second one
        node.right.accept(self)
        # If we jumped here because the first was false leave that false value on the stack
        self.program.end_jump(short_circuit, leave_value=True)

    def visit_or_expr(self, node):
        # No super because we need to put the jumps in the right place
        node.left.accept(self)
        # If the first value is false jump past the shortcircuit
        long_circuit = self.program.begin_jump(conditional=True, leave_value=True)
        # If we haven't skipped the shortcircuit jump to the end
        short_circuit = self.program.begin_jump()
        # If we skipped the shortcircuit pop the first value to replace with the second one
        self.program.end_jump(long_circuit)
        node.right.accept(self)
        # If we short circuited leave the true value on the stack
        self.program.end_jump(short_circuit, leave_value=True)
