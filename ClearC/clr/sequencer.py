"""
Module for sequencing visitors / functions.
"""

from typing import List, Union, Iterator

import contextlib

import clr.ast as ast


AstNameDecl = Union[ast.AstValueDecl, ast.AstFuncDecl]


class SequenceBuilder(ast.FunctionVisitor):
    """
    Ast visitor to annotate the execution order of declarations.
    """

    def __init__(self) -> None:
        super().__init__()
        self.started: List[AstNameDecl] = []
        self.completed: List[AstNameDecl] = []

    def _decl(self, node: ast.AstDecl) -> None:
        if node.scope and isinstance(node.scope, (ast.Ast, ast.AstBlockStmt)):
            node.scope.sequence.append(node)

    def _start(self, node: AstNameDecl) -> bool:
        if node in self.completed:
            return False
        if node in self.started:
            self.errors.add(
                message="circular dependency for value", regions=[node.region]
            )
            return False
        return True

    @contextlib.contextmanager
    def _name_decl(self, node: AstNameDecl) -> Iterator[None]:
        self.started.append(node)
        yield
        self.completed.append(node)

    def value_decl(self, node: ast.AstValueDecl) -> None:
        if self._start(node):
            with self._name_decl(node):
                super().value_decl(node)

    def func_decl(self, node: ast.AstFuncDecl) -> None:
        if self._start(node):
            with self._name_decl(node):
                super().func_decl(node)

    def ident_expr(self, node: ast.AstIdentExpr) -> None:
        if node.ref:
            # Special case for recursive function calls
            if self._functions and node.ref == self._functions[-1]:
                pass
            else:
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
