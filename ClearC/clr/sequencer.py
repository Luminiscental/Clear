"""
Module for sequencing visitors / functions.
"""

from typing import List, Union

import clr.ast as ast


def _sequence(node: ast.AstDecl) -> None:
    if node.scope:
        node.scope.sequence.append(node)


class SequenceBuilder(ast.ScopeVisitor):
    """
    Ast visitor to annotate the execution order of declarations.
    """

    def __init__(self) -> None:
        super().__init__()
        self.started: List[Union[ast.AstValueDecl, ast.AstFuncDecl]] = []
        self.completed: List[Union[ast.AstValueDecl, ast.AstFuncDecl]] = []

    def value_decl(self, node: ast.AstValueDecl) -> None:
        if node in self.completed:
            return
        if node in self.started:
            # TODO: Show the loop somehow.
            self.errors.add(
                message=f"circular dependency for {node.ident}", regions=[node.region]
            )
            return
        self.started.append(node)
        super().value_decl(node)
        self.completed.append(node)
        _sequence(node)

    def func_decl(self, node: ast.AstFuncDecl) -> None:
        if node in self.completed:
            return
        if node in self.started:
            self.errors.add(
                message=f"circular dependency for {node.ident}", regions=[node.region]
            )
            return
        # The function body isn't executed to create the function
        self.completed.append(node)
        super().func_decl(node)
        _sequence(node)

    def print_stmt(self, node: ast.AstPrintStmt) -> None:
        super().print_stmt(node)
        _sequence(node)

    def block_stmt(self, node: ast.AstBlockStmt) -> None:
        super().block_stmt(node)
        _sequence(node)

    def if_stmt(self, node: ast.AstIfStmt) -> None:
        super().if_stmt(node)
        _sequence(node)

    def while_stmt(self, node: ast.AstWhileStmt) -> None:
        super().while_stmt(node)
        _sequence(node)

    def return_stmt(self, node: ast.AstReturnStmt) -> None:
        super().return_stmt(node)
        _sequence(node)

    def expr_stmt(self, node: ast.AstExprStmt) -> None:
        super().expr_stmt(node)
        _sequence(node)

    def ident_expr(self, node: ast.AstIdentExpr) -> None:
        super().ident_expr(node)
        # If the ref is None there was already an error
        if node.ref:
            node.ref.accept(self)


class SequenceWriter(ast.DeepVisitor):
    """
    Ast visitor to put declarations in execution order from annotations.
    """

    def start(self, node: ast.Ast) -> None:
        super().start(node)
        node.decls = node.sequence

    def block_stmt(self, node: ast.AstBlockStmt) -> None:
        super().block_stmt(node)
        node.decls = node.sequence
