"""
Module for name resolution visitors / functions.
"""

from typing import Union, Optional

import clr.ast as ast
import clr.types as ts


class NameTracker(ast.ScopeVisitor):
    """
    Ast visitor to annotate what names are in scope.
    """

    def _set_name(self, name: str, node: ast.AstIdentRef) -> None:
        names = self._get_scope().names
        if name in names:
            self.errors.add(
                message=f"redefinition of name {name}",
                regions=[node.region, names[name].region],
            )
        names[name] = node

    def binding(self, node: ast.AstBinding) -> None:
        self._set_name(node.name, node)

    def param(self, node: ast.AstParam) -> None:
        self._set_name(node.param_name, node)

    def func_decl(self, node: ast.AstFuncDecl) -> None:
        self._set_name(node.ident, node)
        super().func_decl(node)


class ScopeTracker(ast.ScopeVisitor):
    """
    Ast visitor to annotate what scope declarations are sequenced in.
    """

    def _decl(self, node: ast.AstDecl) -> None:
        node.scope = self._get_scope()

    def if_stmt(self, node: ast.AstIfStmt) -> None:
        super().if_stmt(node)
        # The sub-blocks aren't sequenced separately
        node.if_part[1].scope = None
        for _, block in node.elif_parts:
            block.scope = None
        if node.else_part:
            node.else_part.scope = None

    def while_stmt(self, node: ast.AstWhileStmt) -> None:
        super().while_stmt(node)
        # The sub-block isn't sequenced separately
        node.block.scope = None


class NameResolver(ast.ScopeVisitor):
    """
    Ast visitor to annotate what declarations identifiers reference.
    """

    def _get_name(self, name: str) -> Optional[ast.AstIdentRef]:
        for scope in reversed(self._scopes):
            if name in scope.names:
                return scope.names[name]
        return None

    def _resolve_name(
        self, name: str, node: Union[ast.AstIdentExpr, ast.AstIdentType]
    ) -> None:
        ref = self._get_name(name)
        if ref is None:
            self.errors.add(
                message=f"reference to undeclared name {name}", regions=[node.region]
            )
        else:
            node.ref = ref

    def ident_expr(self, node: ast.AstIdentExpr) -> None:
        if node.name not in ts.BUILTINS:
            self._resolve_name(node.name, node)

    def ident_type(self, node: ast.AstIdentType) -> None:
        if node.name not in {annot.value for annot in ts.BuiltinType}:
            self._resolve_name(node.name, node)
