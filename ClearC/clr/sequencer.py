"""
Module for sequencing visitors / functions.
"""

from typing import List, Union, Iterator

import contextlib as cx

import clr.ast as ast


# TODO: Track dependencies to give better error messages


class SequenceBuilder(ast.DeepVisitor):
    """
    Ast visitor to annotate the execution order of declarations.
    """

    def __init__(self) -> None:
        super().__init__()
        self.started: List[Union[ast.AstNameDecl, ast.AstStructDecl]] = []
        self.completed: List[Union[ast.AstNameDecl, ast.AstStructDecl]] = []

    def _decl(self, node: ast.AstDecl) -> None:
        if isinstance(node.context, (ast.AstBlockStmt, ast.Ast)):
            node.context.sequence.append(node)
        if isinstance(node.context, ast.AstFuncDecl):
            node.context.block.sequence.append(node)
        if isinstance(node.context, ast.AstStructDecl):
            # Should always be true
            if isinstance(node, ast.AstFuncDecl):
                node.context.sequence.append(node)

    @cx.contextmanager
    def _name_decl(
        self, node: Union[ast.AstNameDecl, ast.AstStructDecl]
    ) -> Iterator[None]:
        self.started.append(node)
        yield
        self.completed.append(node)

    def struct_decl(self, node: ast.AstStructDecl) -> None:
        if node in self.completed:
            return
        if node in self.started:
            self.errors.add(
                message="circular dependency for struct declaration",
                regions=[node.region],
            )
            return
        with self._name_decl(node):
            super().struct_decl(node)

    def value_decl(self, node: ast.AstValueDecl) -> None:
        if node in self.completed:
            return
        if node in self.started:
            self.errors.add(
                message="circular dependency for value declaration",
                regions=[node.region],
            )
            return
        with self._name_decl(node):
            super().value_decl(node)

    def func_decl(self, node: ast.AstFuncDecl) -> None:
        if node in self.completed:
            return
        if node in self.started:
            self.errors.add(
                message="circular dependency for function declaration",
                regions=[node.region],
            )
            return
        with self._name_decl(node):
            super().func_decl(node)

    def ident_expr(self, node: ast.AstIdentExpr) -> None:
        if node.ref and node.ref.dependency:
            node.ref.dependency.accept(self)

    def construct_expr(self, node: ast.AstConstructExpr) -> None:
        if node.ref and not node.inside:
            node.ref.accept(self)

    def _access_generator(self, generator: ast.AstFuncDecl) -> None:
        if generator in self.completed:
            return
        if generator in self.started:
            self.errors.add(
                message="circular dependency for field declaration",
                regions=[generator.block.decls[0].region],
            )
            return
        generator.accept(self)

    def _access_this(self, node: ast.AstIdentExpr, field: str) -> None:
        if node.struct:
            for generator, bindings in node.struct.generators:
                for binding in bindings:
                    if binding.name == field:
                        self._access_generator(generator)

    def access_expr(self, node: ast.AstAccessExpr) -> None:
        if isinstance(node.target, ast.AstIdentExpr) and node.target.name == "this":
            self._access_this(node.target, node.name)


class SequenceWriter(ast.DeepVisitor):
    """
    Ast visitor to put declarations in execution order from annotations.
    """

    def start(self, node: ast.Ast) -> None:
        super().start(node)
        node.decls = node.sequence

    def struct_decl(self, node: ast.AstStructDecl) -> None:
        super().struct_decl(node)

        def get_bindings(target: ast.AstFuncDecl) -> List[ast.AstBinding]:
            for generator, bindings in node.generators:
                if generator == target:
                    return bindings
            return []

        node.generators = [
            (generator, get_bindings(generator)) for generator in node.sequence
        ]

    def block_stmt(self, node: ast.AstBlockStmt) -> None:
        super().block_stmt(node)
        node.decls = node.sequence
