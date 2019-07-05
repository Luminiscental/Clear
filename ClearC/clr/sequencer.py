"""
Module for sequencing visitors / functions.
"""

from typing import List, Union, Iterator

import contextlib

import clr.ast as ast


AstNameDecl = Union[ast.AstValueDecl, ast.AstFuncDecl, ast.AstStructDecl]


class SequenceBuilder(ast.ContextVisitor):
    """
    Ast visitor to annotate the execution order of declarations.
    """

    def __init__(self) -> None:
        super().__init__()
        self.started: List[AstNameDecl] = []
        self.completed: List[AstNameDecl] = []

    def _decl(self, node: ast.AstDecl) -> None:
        context = self._get_context()
        if isinstance(context, (ast.AstBlockStmt, ast.Ast)):
            context.sequence.append(node)
        if isinstance(context, ast.AstFuncDecl):
            context.block.sequence.append(node)
        if isinstance(context, ast.AstStructDecl):
            if node in context.fields and isinstance(
                node, (ast.AstValueDecl, ast.AstFuncDecl)
            ):
                context.sequence.append(node)

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

    def struct_decl(self, node: ast.AstStructDecl) -> None:
        if self._start(node):
            with self._name_decl(node):
                for param in node.iter_params():
                    node.sequence.append(param)
                super().struct_decl(node)

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
            for context in reversed(self._contexts):
                if isinstance(context, ast.AstFuncDecl):
                    if node.ref == context:
                        # If it's the recursion upvalue don't lookup
                        return
                    break
            node.ref.accept(self)

    def construct_expr(self, node: ast.AstConstructExpr) -> None:
        if node.ref:
            node.ref.accept(self)


class SequenceWriter(ast.DeepVisitor):
    """
    Ast visitor to put declarations in execution order from annotations.
    """

    def start(self, node: ast.Ast) -> None:
        super().start(node)
        node.decls = node.sequence

    def struct_decl(self, node: ast.AstStructDecl) -> None:
        super().struct_decl(node)
        node.fields = node.sequence

    def block_stmt(self, node: ast.AstBlockStmt) -> None:
        super().block_stmt(node)
        node.decls = node.sequence
