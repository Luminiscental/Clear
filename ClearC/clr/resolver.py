"""
Module for name resolution visitors / functions.
"""

from typing import List, Union

import clr.ast as ast

# TODO: Shadowing / scope popping not working


class ScopeVisitor(ast.BlockVisitor):
    """
    Ast visitor to keep track of the current scope.
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

    def block_stmt(self, node: ast.AstBlockStmt) -> None:
        self._push_scope(node)
        super().block_stmt(node)
        self._pop_scope()


class NameTracker(ScopeVisitor):
    """
    Ast visitor to annotate what names are in scope.
    """

    def _push_scope(self, node: ast.AstBlockStmt) -> None:
        parent = self._get_scope()
        super()._push_scope(node)
        self._get_scope().names = parent.names

    def value_decl(self, node: ast.AstValueDecl) -> None:
        self._get_scope().names[node.ident] = node

    def func_decl(self, node: ast.AstFuncDecl) -> None:
        self._get_scope().names[node.ident] = node
        for param in node.params:
            self._get_scope().names[param.param_name] = param
        super().func_decl(node)


class NameResolver(ScopeVisitor, ast.DeepVisitor):
    """
    Ast visitor to annotate what declarations identifiers reference.
    """

    def __init__(self, tree: ast.Ast) -> None:
        super().__init__(tree)
        self.errors: List[str] = []

    def _resolve_name(
        self, name: str, node: Union[ast.AstIdentExpr, ast.AstAtomType]
    ) -> None:
        if name not in self._get_scope().names:
            # TODO: store regions so these errors can be more friendly
            self.errors.append(f"reference to undeclared name {name}")
        else:
            node.ref = self._get_scope().names[name]

    def ident_expr(self, node: ast.AstIdentExpr) -> None:
        self._resolve_name(node.name, node)

    def atom_type(self, node: ast.AstAtomType) -> None:
        if node.token not in ["void", "int", "str", "num", "bool"]:
            self._resolve_name(node.token, node)


def resolve_names(tree: ast.Ast) -> List[str]:
    """
    Annotates scope nodes with the names they contain, and identifier nodes with the declarations
    they reference, returning a list of any resolve errors.
    """
    tracker = NameTracker(tree)
    tree.accept(tracker)
    resolver = NameResolver(tree)
    tree.accept(resolver)
    return resolver.errors
