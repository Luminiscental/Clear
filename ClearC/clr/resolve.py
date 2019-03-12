"""
This module provides a Resolver class to visit AST nodes resolving
identifiers to find their types and variable indices.
"""
from enum import Enum
from collections import namedtuple, defaultdict
from clr.tokens import TokenType, token_info
from clr.errors import emit_error
from clr.visitor import AstVisitor


class ValueType(Enum):
    """
    This class enumerates the possible types of Clear variables,
    including an unresolved option.
    """

    INT = "int"
    NUM = "num"
    STR = "str"
    BOOL = "bool"
    UNRESOLVED = "<unresolved>"

    def __str__(self):
        return self.value


ResolvedName = namedtuple(
    "ResolvedName",
    ("value_type", "index", "is_global", "is_mutable"),
    defaults=(ValueType.UNRESOLVED, -1, False, False),
)


class Resolver(AstVisitor):
    """
    This class provides functionality for visiting AST nodes to resolve
    the type and variable index of identifiers / declarations thereof.
    """

    def __init__(self):
        self.scopes = [defaultdict(ResolvedName)]
        self.level = 0
        self.local_index = 0
        self.global_index = 0

    def _current_scope(self):
        return self.scopes[self.level]

    def _global_scope(self):
        return self.scopes[0]

    def _get_scope(self, lookback):
        return self.scopes[self.level - lookback]

    def _lookup_name(self, name):
        """
        This function resolves the given name to a previously resolved
        declaration, returning the resolved information set as unresolved
        if no such declaration was found.
        """
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
        """
        This function pushes a new scope to resolve within.
        """
        super().start_block_stmt(node)
        self.scopes.append(defaultdict(ResolvedName))
        self.level += 1

    def end_block_stmt(self, node):
        """
        This function pops the current resolution scope.
        """
        super().end_block_stmt(node)
        if self.level > 0:
            popped = self._current_scope()
            if popped:
                self.local_index = min(
                    [r.index for r in popped.values() if r.index != -1]
                )
        del self.scopes[self.level]
        self.level -= 1

    def visit_val_decl(self, node):
        super().visit_val_decl(node)
        prev = self._lookup_name(node.name.lexeme)
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
            node.value.value_type, idx, self.level == 0, node.resolved_name.is_mutable
        )
        self._current_scope()[node.name.lexeme] = result
        node.resolved_name = result

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
                f"Incompatible type {str(node.target.value_type)} for unary operator {token_info(node.operator)}!"
            )()
        node.value_type = node.target.value_type

    def visit_binary_expr(self, node):
        super().visit_binary_expr(node)
        if node.left.value_type != node.right.value_type:
            emit_error(
                f"Incompatible operand types {str(node.left.value_type)} and {str(node.right.value_type)} for binary operator {token_info(node.operator)}!"
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
                f"Incompatible type {str(node.left.value_type)} for binary operator {token_info(node.operator)}!"
            )()
        if node.operator.token_type == TokenType.EQUAL and not node.left.is_assignable:
            emit_error(
                f"Unassignable expression {str(node.left)}! Attempt to assign at {token_info(node.operator)}"
            )()
        node.value_type = node.left.value_type

    def visit_ident_expr(self, node):
        super().visit_ident_expr(node)
        node.resolved_name = self._lookup_name(node.name.lexeme)
        if node.resolved_name.value_type == ValueType.UNRESOLVED:
            emit_error(f"Reference to undefined identifier! {token_info(node.name)}")()
        node.value_type = node.resolved_name.value_type
        node.is_assignable = node.resolved_name.is_mutable

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
                f"Incompatible parameter type {str(node.target.value_type)} for built-in function {token_info(node.function)}!"
            )()

    def visit_and_expr(self, node):
        super().visit_and_expr(node)
        if node.left.value_type != ValueType.BOOL:
            emit_error(
                f"Incompatible type {str(node.left.value_type)} for left operand to logic operator {token_info(node.operator)}!"
            )()
        if node.right.value_type != ValueType.BOOL:
            emit_error(
                f"Incompatible type {str(node.right.value_type)} for right operand to logic operator {token_info(node.operator)}!"
            )()

    def visit_or_expr(self, node):
        super().visit_or_expr(node)
        if node.left.value_type != ValueType.BOOL:
            emit_error(
                f"Incompatible type {str(node.left.value_type)} for left operand to logic operator {token_info(node.operator)}!"
            )()
        if node.right.value_type != ValueType.BOOL:
            emit_error(
                f"Incompatible type {str(node.right.value_type)} for right operand to logic operator {token_info(node.operator)}!"
            )()
