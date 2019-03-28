import itertools
from collections import namedtuple, defaultdict
from clr.tokens import TokenType, token_info
from clr.errors import emit_error
from clr.ast.visitor import DeclVisitor
from clr.ast.type_annotations import (
    TypeAnnotation,
    TypeAnnotationType,
    BUILTINS,
    NUM_TYPE,
    INT_TYPE,
    STR_TYPE,
    BOOL_TYPE,
    ANY_TYPE,
    FunctionTypeAnnotation,
)
from clr.ast.return_annotations import ReturnAnnotation, ReturnAnnotationType
from clr.ast.expression_nodes import IdentExpr
from clr.ast.statement_nodes import StmtNode

TypeInfo = namedtuple(
    "TypeInfo", ("annotation", "assignable"), defaults=(TypeAnnotation(), False)
)


class TypeResolver(DeclVisitor):
    def __init__(self):
        super().__init__()
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
                    f"Attempt to call a non-callable object {node.target}! (type is {function_type})"
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
