"""
Module for name resolution visitors / functions.
"""

from typing import Union, Optional

import clr.ast as ast
import clr.types as ts

# TODO: Warn on unused declarations


class NameTracker(ast.ContextVisitor):
    """
    Ast visitor to annotate what names are in scope.
    """

    def _set_name(self, name: str, node: ast.AstName) -> None:
        for context in reversed(self._contexts):
            if isinstance(context, ast.AstScope):
                names = context.names
                break
            if isinstance(context, ast.AstFuncDecl):
                names = context.block.names
                break
        if name in names:
            self.errors.add(
                message=f"redefinition of name {name}",
                regions=[node.region, names[name].region],
            )
        names[name] = node

    def struct_decl(self, node: ast.AstStructDecl) -> None:
        self._set_name(node.name, node)

    def binding(self, node: ast.AstBinding) -> None:
        self._set_name(node.name, node)


class ScopeTracker(ast.ContextVisitor):
    """
    Ast visitor to annotate what scope declarations are sequenced in.
    """

    def _decl(self, node: ast.AstDecl) -> None:
        for context in reversed(self._contexts):
            if isinstance(context, ast.AstScope):
                node.scope = context
                break
            if isinstance(context, ast.AstFuncDecl):
                node.scope = context.block
                break

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


class NameResolver(ast.ContextVisitor):
    """
    Ast visitor to annotate what declarations identifiers reference.
    """

    def _get_name(self, name: str) -> Optional[ast.AstName]:
        for context in reversed(self._contexts):
            if isinstance(context, ast.AstScope):
                if name in context.names:
                    return context.names[name]
            if isinstance(context, ast.AstFuncDecl):
                if name in context.block.names:
                    return context.block.names[name]
        return None

    def _resolve_name(
        self,
        name: str,
        node: Union[ast.AstIdentExpr, ast.AstIdentType, ast.AstConstructExpr],
    ) -> None:
        ref = self._get_name(name)
        if ref is None:
            self.errors.add(
                message=f"reference to undeclared name {name}", regions=[node.region]
            )
            return
        if isinstance(node, ast.AstConstructExpr):
            if not isinstance(ref, ast.AstStructDecl):
                self.errors.add(
                    message=f"invalid reference to value {node.name}, expected struct",
                    regions=[node.region],
                )
            else:
                node.ref = ref
        else:
            if isinstance(ref, ast.AstStructDecl):
                self.errors.add(
                    message=f"invalid reference to struct {node.name}, expected value",
                    regions=[node.region],
                )
            else:
                node.ref = ref

    def construct_expr(self, node: ast.AstConstructExpr) -> None:
        self._resolve_name(node.name, node)

    def ident_expr(self, node: ast.AstIdentExpr) -> None:
        if node.name not in ts.BUILTINS:
            self._resolve_name(node.name, node)

    def ident_type(self, node: ast.AstIdentType) -> None:
        if node.name not in {annot.value for annot in ts.BuiltinType}:
            self._resolve_name(node.name, node)
