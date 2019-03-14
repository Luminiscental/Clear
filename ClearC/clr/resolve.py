"""
This module provides a Resolver class to visit AST nodes resolving
identifiers to find their types and variable indices.
"""
from enum import Enum
from collections import namedtuple, defaultdict
from clr.tokens import TokenType
from clr.errors import emit_error, ClrCompileError
from clr.visitor import AstVisitor
from clr.values import DEBUG


class ValueType(Enum):
    """
    This class enumerates the possible types of Clear variables,
    including an unresolved option.
    """

    INT = "int"
    NUM = "num"
    STR = "str"
    BOOL = "bool"
    FUNCTION = "<function>"
    UNRESOLVED = "<unresolved>"

    def __str__(self):
        return self.value


ResolvedName = namedtuple(
    "ResolvedName",
    ("value_type", "index", "is_global", "is_mutable", "is_param", "func_decl"),
    defaults=(ValueType.UNRESOLVED, -1, False, False, False, None),
)


class Resolver(AstVisitor):
    """
    This class provides functionality for visiting AST nodes in the global scope
    to resolve the type and variable index of identifiers / declarations thereof.
    """

    def __init__(self):
        self.scopes = [defaultdict(ResolvedName)]
        self.level = 0
        self.local_index = 0
        self.global_index = 0
        self.is_function = False

    def _current_scope(self):
        return self.scopes[self.level]

    def _global_scope(self):
        return self.scopes[0]

    def _get_scope(self, lookback):
        return self.scopes[self.level - lookback]

    def _lookup_name(self, name):
        result = ResolvedName()
        lookback = 0
        while lookback < self.level:
            result = self._get_scope(lookback)[name]
            lookback += 1
            if result.value_type != ValueType.UNRESOLVED:
                break
        else:
            result = self._global_scope()[name]
        return result

    def start_block_stmt(self, node):
        super().start_block_stmt(node)
        self.scopes.append(defaultdict(ResolvedName))
        self.level += 1

    def end_block_stmt(self, node):
        super().end_block_stmt(node)
        if self.level > 0:
            popped = self._current_scope()
            if popped:
                self.local_index = min(
                    [r.index for r in popped.values() if r.index != -1]
                )
        del self.scopes[self.level]
        self.level -= 1
        for decl in node.declarations:
            if node.returns:
                emit_error(f"Unreachable code! {decl.get_info()}")()
            elif decl.returns:
                node.returns = True

    def _declare_name(self, name, value_type, is_mutable=False, func_decl=None):
        prev = self._lookup_name(name)
        if prev.value_type == ValueType.UNRESOLVED:
            if self.level > 0:
                idx = self.local_index
                self.local_index += 1
            else:
                idx = self.global_index
                self.global_index += 1
        else:
            idx = prev.index
        result = ResolvedName(
            value_type=value_type,
            index=idx,
            is_global=self.level == 0,
            is_mutable=is_mutable,
            func_decl=func_decl,
        )
        self._current_scope()[name] = result
        return result

    def visit_val_decl(self, node):
        super().visit_val_decl(node)
        node.resolved_name = self._declare_name(
            node.name.lexeme, node.value.value_type, node.resolved_name.is_mutable
        )

    def visit_func_decl(self, node):
        node.resolved_name = self._declare_name(
            name=node.name.lexeme, value_type=ValueType.FUNCTION, func_decl=node
        )
        function = FunctionResolver()
        for typename, name in node.params.pairs:
            function.add_param(name.lexeme, typename.value_type)
        for decl in node.block.declarations:
            decl.accept(function)
            if node.block.returns:
                emit_error(f"Unreachable code! {decl.get_info()}")()
            elif decl.returns:
                node.block.returns = True
        if not node.block.returns:
            emit_error(f"Function may not return! {node.get_info()}")()
        node.return_type = function.return_type
        if DEBUG:
            print(f"Function {node.get_info()} returns with {node.return_type}")

    def visit_if_stmt(self, node):
        super().visit_if_stmt(node)
        node.returns = (
            node.otherwise is not None
            and node.otherwise.returns
            and all(list(map(lambda check: check[1].returns, node.checks)))
        )

    def visit_ret_stmt(self, node):
        super().visit_ret_stmt(node)
        if not self.is_function:
            emit_error(
                f"Invalid return statement; must be inside a function! {node.get_info()}"
            )()

    def visit_decl(self, node):
        super().visit_decl(node)
        node.returns = node.value.returns

    def visit_stmt(self, node):
        super().visit_decl(node)
        node.returns = node.value.returns

    def visit_expr(self, node):
        super().visit_expr(node)
        node.value_type = node.value.value_type

    def visit_unary_expr(self, node):
        super().visit_unary_expr(node)
        if (
            node.target.value_type
            not in {
                TokenType.MINUS: [ValueType.NUM, ValueType.INT],
                TokenType.BANG: [ValueType.BOOL],
            }[node.operator.token_type]
        ):
            emit_error(
                f"Incompatible type {str(node.target.value_type)} for unary operator {node.get_info()}!"
            )()
        node.value_type = node.target.value_type

    def visit_binary_expr(self, node):
        super().visit_binary_expr(node)
        if node.left.value_type != node.right.value_type:
            emit_error(
                f"Incompatible operand types {str(node.left.value_type)} and {str(node.right.value_type)} for binary operator {node.get_info()}!"
            )()
        if (
            node.left.value_type
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
            }[node.operator.token_type]
        ):
            emit_error(
                f"Incompatible type {str(node.left.value_type)} for binary operator {node.get_info()}!"
            )()
        if node.operator.token_type == TokenType.EQUAL and not node.left.is_assignable:
            emit_error(
                f"Unassignable expression {str(node.left)}! Attempt to assign at {node.get_info()}"
            )()
        node.value_type = node.left.value_type

    def visit_call_expr(self, node):
        super().visit_call_expr(node)
        if node.target.value_type != ValueType.FUNCTION:
            emit_error(
                f"Attempt to call a non-callable object {str(node.target)}! Must be a function {node.get_info()}"
            )()
        function = node.target.resolved_name.func_decl
        if len(function.params.pairs) != len(node.arguments):
            emit_error(
                f"Incorrect number of parameters! Expected {len(function.params.pairs)} found {len(node.arguments)}! {node.get_info()}"
            )()
        for i, pair in enumerate(function.params.pairs):
            arg = node.arguments[i]
            if pair[0].value_type != arg.value_type:
                emit_error(
                    f"Incorrect argument type at position {i}! Expected {pair[0].value_type} but found {arg.value_type}! {node.get_info()}"
                )()
        node.value_type = function.return_type

    def visit_ident_expr(self, node):
        super().visit_ident_expr(node)
        node.resolved_name = self._lookup_name(node.name.lexeme)
        if node.resolved_name.value_type == ValueType.UNRESOLVED:
            emit_error(f"Reference to undefined identifier! {node.get_info()}")()
        node.value_type = node.resolved_name.value_type
        node.is_assignable = node.resolved_name.is_mutable
        if DEBUG:
            print(f"Value {node.get_info()} is found with type {node.value_type}")

    def visit_builtin_expr(self, node):
        super().visit_builtin_expr(node)
        if (
            node.target.value_type
            not in {
                TokenType.TYPE: ValueType,
                TokenType.INT: [ValueType.NUM, ValueType.INT, ValueType.BOOL],
                TokenType.BOOL: ValueType,
                TokenType.NUM: [ValueType.NUM, ValueType.INT, ValueType.BOOL],
                TokenType.STR: ValueType,
            }[node.function.token_type]
        ):
            emit_error(
                f"Incompatible parameter type {str(node.target.value_type)} for built-in function {node.get_info()}!"
            )()

    def visit_and_expr(self, node):
        super().visit_and_expr(node)
        if node.left.value_type != ValueType.BOOL:
            emit_error(
                f"Incompatible type {str(node.left.value_type)} for left operand to logic operator {node.get_info()}!"
            )()
        if node.right.value_type != ValueType.BOOL:
            emit_error(
                f"Incompatible type {str(node.right.value_type)} for right operand to logic operator {node.get_info()}!"
            )()

    def visit_or_expr(self, node):
        super().visit_or_expr(node)
        if node.left.value_type != ValueType.BOOL:
            emit_error(
                f"Incompatible type {str(node.left.value_type)} for left operand to logic operator {node.get_info()}!"
            )()
        if node.right.value_type != ValueType.BOOL:
            emit_error(
                f"Incompatible type {str(node.right.value_type)} for right operand to logic operator {node.get_info()}!"
            )()


class FunctionResolver(Resolver):
    """
    This class provides functionality for visiting AST nodes within a function
    to resolve the type and variable index of identifiers / declarations thereof.
    """

    def __init__(self):
        super().__init__()
        self.scopes.append(defaultdict(ResolvedName))
        self.level += 1
        self.params = []
        self.return_type = None
        self.is_function = True

    def add_param(self, name, value_type):
        """
        This function adds a given parameter to the context of this resolver.
        """
        index = len(self.params)
        self.params.append((name, value_type, index))

    def visit_ret_stmt(self, node):
        super().visit_ret_stmt(node)
        return_type = self.return_type
        if return_type is None:
            self.return_type = node.value.value_type
        else:
            if return_type != node.value.value_type:
                emit_error(
                    f"Invalid return type! previously had {str(return_type)} but was given {str(node.value)} which is {str(node.value.value_type)}! {node.get_info()}"
                )()
        node.returns = True

    def visit_ident_expr(self, node):
        try:
            super().visit_ident_expr(node)
        except ClrCompileError:
            for param_name, param_type, param_index in self.params:
                if param_name == node.name.lexeme:
                    node.resolved_name = ResolvedName(
                        value_type=param_type, index=param_index, is_param=True
                    )
                    break
            else:
                emit_error(f"Reference to undefined identifier! {node.get_info()}")()
        node.value_type = node.resolved_name.value_type
        node.is_assignable = node.resolved_name.is_mutable
