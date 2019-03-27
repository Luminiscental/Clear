import itertools
from collections import defaultdict, namedtuple
from clr.tokens import TokenType
from clr.errors import emit_error
from clr.ast.visitor import DeclVisitor
from clr.ast.type import (
    TypeAnnotation,
    FuncInfo,
    ReturnAnnotation,
    Type,
    Return,
    BUILTINS,
    INT_TYPE,
    NUM_TYPE,
    STR_TYPE,
    BOOL_TYPE,
)

TypePair = namedtuple(
    "TypedPair", ("annotation", "assignable"), defaults=(TypeAnnotation(), False)
)


class TypeResolver(DeclVisitor):
    def __init__(self):
        self.scopes = [defaultdict(TypePair)]
        self.expected_returns = []
        self.level = 0

    def _declare_name(self, name, type_annotation, assignable=False):
        self.scopes[self.level][name] = TypePair(type_annotation, assignable)

    def _lookup_name(self, name):
        result = TypePair()
        lookback = 0
        while lookback <= self.level:
            result = self.scopes[self.level - lookback][name]
            lookback += 1
            if result.annotation.kind != Type.UNRESOLVED:
                break
        return result

    def start_scope(self):
        super().start_scope()
        self.scopes.append(defaultdict(TypePair))
        self.level += 1

    def end_scope(self):
        super().end_scope()
        del self.scopes[self.level]
        self.level -= 1

    def visit_call_expr(self, node):
        if node.target.is_ident and node.target.name.lexeme in BUILTINS:
            # If it's a built-in don't call super() as we don't evaluate the target
            if len(node.arguments) != 1:
                emit_error(
                    f"Built-in function {node.target} only takes one argument! {node.get_info()}"
                )()
            arg = node.arguments[0]
            arg.accept(self)
            builtin = BUILTINS[node.target.name.lexeme]
            if arg.type_annotation not in builtin.param_types:
                emit_error(
                    f"Built-in function {node.target} cannot take an argument of type {arg.type_annotation}! {node.get_info()}"
                )()
            node.type_annotation = builtin.return_type
        else:
            super().visit_call_expr(node)
            function_type = node.target.type_annotation
            if function_type.kind != Type.FUNCTION:
                emit_error(
                    f"Attempt to call a non-callable object {node.target}! {node.get_info()}"
                )()
            passed_signature = list(
                map(lambda arg: arg.type_annotation, node.arguments)
            )
            args = "(" + ", ".join(map(str, passed_signature)) + ")"
            if passed_signature != function_type.func_info.signature:
                emit_error(
                    f"Could not find signature for function matching provided argument list {args}! {node.get_info()}"
                )()
            node.type_annotation = function_type.func_info.return_type

    def visit_unary_expr(self, node):
        super().visit_unary_expr(node)
        target_type = node.target.type_annotation
        if (
            target_type.kind
            not in {TokenType.MINUS: [Type.NUM, Type.INT], TokenType.BANG: [Type.BOOL]}[
                node.operator.token_type
            ]
        ):
            emit_error(
                f"Incompatible operand type {target_type} for unary operator! {node.get_info()}"
            )()
        node.type_annotation = target_type

    def visit_binary_expr(self, node):
        super().visit_binary_expr(node)
        left_type = node.left.type_annotation
        right_type = node.right.type_annotation
        if left_type.kind != right_type.kind:
            emit_error(
                f"Incompatible operand types {left_type} and {right_type} for binary operator! {node.get_info()}"
            )()
        arg_kind = left_type.kind
        if (
            arg_kind
            not in {
                TokenType.PLUS: [Type.NUM, Type.INT, Type.STR],
                TokenType.MINUS: [Type.NUM, Type.INT],
                TokenType.STAR: [Type.NUM, Type.INT],
                TokenType.SLASH: [Type.NUM],
                TokenType.EQUAL_EQUAL: Type,
                TokenType.BANG_EQUAL: Type,
                TokenType.LESS: [Type.NUM, Type.INT],
                TokenType.GREATER_EQUAL: [Type.NUM, Type.INT],
                TokenType.GREATER: [Type.NUM, Type.INT],
                TokenType.LESS_EQUAL: [Type.NUM, Type.INT],
                TokenType.EQUAL: Type,
            }[node.operator.token_type]
        ):
            emit_error(
                f"Incompatible operand type {arg_kind} for binary operator! {node.get_info()}"
            )()
        if node.operator.token_type == TokenType.EQUAL and not node.left.assignable:
            emit_error(f"Unassignable expression {node.left}! {node.get_info()}")()
        node.type_annotation = left_type

    def visit_and_expr(self, node):
        super().visit_and_expr(node)
        left_type = node.left.type_annotation
        right_type = node.right.type_annotation
        if left_type.kind != Type.BOOL:
            emit_error(
                f"Incompatible type {left_type} for left operand to logic operator! {node.get_info()}"
            )()
        if right_type.kind != Type.BOOL:
            emit_error(
                f"Incompatible type {right_type} for right operand to logic operator! {node.get_info()}"
            )()

    def visit_or_expr(self, node):
        super().visit_or_expr(node)
        left_type = node.left.type_annotation
        right_type = node.right.type_annotation
        if left_type.kind != Type.BOOL:
            emit_error(
                f"Incompatible type {left_type} for left operand to logic operator! {node.get_info()}"
            )()
        if right_type.kind != Type.BOOL:
            emit_error(
                f"Incompatible type {right_type} for right operand to logic operator! {node.get_info()}"
            )()

    def visit_ident_expr(self, node):
        super().visit_ident_expr(node)
        if node.name.lexeme in BUILTINS:
            emit_error(
                f"Invalid identifier name {node.name.lexeme}! This is reserved for the built-in function {node.name.lexeme}(). {node.get_info()}"
            )()
        (node.type_annotation, node.assignable) = self._lookup_name(node.name.lexeme)
        if node.type_annotation.kind == Type.UNRESOLVED:
            emit_error(f"Reference to undefined identifier! {node.get_info()}")()

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
        kind = Return.NEVER
        return_type = None
        for decl in node.declarations:
            if kind == Return.ALWAYS:
                emit_error(f"Unreachable code! {decl.get_info()}")()
            if not decl.is_stmt:
                continue
            annotation = decl.return_annotation
            if annotation.kind in [Return.SOMETIMES, Return.ALWAYS]:
                kind = annotation.kind
                return_type = annotation.return_type
        node.return_annotation = ReturnAnnotation(kind, return_type)

    def visit_ret_stmt(self, node):
        super().visit_ret_stmt(node)
        if not self.expected_returns:
            emit_error(
                f"Return statement found outside of function! {node.get_info()}"
            )()
        expected = self.expected_returns[-1]
        if expected != node.value.type_annotation:
            emit_error(
                f"Incompatible return type! Expected {expected} but was given {node.value.type_annotation}! {node.get_info()}"
            )()
        node.return_annotation = ReturnAnnotation(Return.ALWAYS, expected)

    def visit_while_stmt(self, node):
        super().visit_while_stmt(node)
        node.return_annotation = node.block.return_annotation
        if node.return_annotation.kind == Return.ALWAYS:
            node.return_annotation.kind = Return.SOMETIMES

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
        kind = Return.NEVER
        if all(map(lambda annotation: annotation.kind == Return.ALWAYS, annotations)):
            kind = Return.ALWAYS
        elif any(map(lambda annotation: annotation.kind != Return.NEVER, annotations)):
            kind = Return.SOMETIMES
        returns = [
            annotation.return_type
            for annotation in annotations
            if annotation.kind != Return.NEVER
        ]
        return_type = returns[0] if returns else None
        node.return_annotation = ReturnAnnotation(kind, return_type)

    def visit_func_decl(self, node):
        # No super because we handle the params
        # Iterate over the parameters and resolve to types
        arg_types = []
        for param_type, param_name in node.params:
            resolved_type = param_type.as_annotation()
            if resolved_type.kind == Type.UNRESOLVED:
                emit_error(
                    f"Invalid parameter type {param_type} for function! {node.get_info()}"
                )()
            arg_types.append(resolved_type)
        # Resolve the return type
        return_type = node.return_type.as_annotation()
        # Create an annotation for the function signature
        func_info = FuncInfo(return_type=return_type, signature=arg_types)
        type_annotation = TypeAnnotation(kind=Type.FUNCTION, func_info=func_info)
        # Declare the function
        self._declare_name(node.name.lexeme, type_annotation)
        # Start the function scope
        self.start_scope()
        # Iterate over the parameters and declare them
        for param_type, param_name in node.params:
            self._declare_name(param_name.lexeme, param_type.as_annotation())
        # Expect return statements for the return type
        self.expected_returns.append(return_type)
        # Define the function by its block
        node.block.accept(self)
        # End the function scope
        self.end_scope()
        # Stop expecting return statements
        del self.expected_returns[-1]
        if node.block.return_annotation.kind != Return.ALWAYS:
            emit_error(f"Function does not always return! {node.get_info()}")()

    def visit_val_decl(self, node):
        super().visit_val_decl(node)
        type_annotation = node.value.type_annotation
        self._declare_name(node.name.lexeme, type_annotation, assignable=node.mutable)
