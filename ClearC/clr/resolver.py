"""
Module for name resolution visitors / functions.
"""

from typing import List, Union

import clr.ast as ast


class NameTracker(ast.BlockVisitor):
    """
    Ast visitor to annotate what names are in scope.
    """

    def __init__(self, tree: ast.Ast):
        self.tree = tree
        self.scopes: List[ast.AstBlockStmt] = []

    def _get_scope(self) -> Union[ast.AstBlockStmt, ast.Ast]:
        if not self.scopes:
            return self.tree
        return self.scopes[-1]

    def _push_scope(self, node: ast.AstBlockStmt) -> None:
        self.scopes.append(node)

    def _pop_scope(self) -> None:
        self.scopes.pop()

    def value_decl(self, node: ast.AstValueDecl) -> None:
        self._get_scope().names[node.ident] = node

    def func_decl(self, node: ast.AstFuncDecl) -> None:
        self._get_scope().names[node.ident] = node
        super().func_decl(node)

    def block_stmt(self, node: ast.AstBlockStmt) -> None:
        self._push_scope(node)
        super().block_stmt(node)
        self._pop_scope()

    def print_stmt(self, node: ast.AstPrintStmt) -> None:
        pass

    def return_stmt(self, node: ast.AstReturnStmt) -> None:
        pass

    def expr_stmt(self, node: ast.AstExprStmt) -> None:
        pass

    def unary_expr(self, node: ast.AstUnaryExpr) -> None:
        pass

    def binary_expr(self, node: ast.AstBinaryExpr) -> None:
        pass

    def int_expr(self, node: ast.AstIntExpr) -> None:
        pass

    def num_expr(self, node: ast.AstNumExpr) -> None:
        pass

    def str_expr(self, node: ast.AstStrExpr) -> None:
        pass

    def ident_expr(self, node: ast.AstIdentExpr) -> None:
        pass

    def call_expr(self, node: ast.AstCallExpr) -> None:
        pass

    def atom_type(self, node: ast.AstAtomType) -> None:
        pass

    def func_type(self, node: ast.AstFuncType) -> None:
        pass

    def optional_type(self, node: ast.AstOptionalType) -> None:
        pass


def resolve_names(tree: ast.Ast) -> None:
    tree.accept(NameTracker(tree))
