"""
Module for name resolution visitors / functions.
"""

from typing import List, Union, Optional

import clr.errors as er
import clr.ast as ast


def resolve_names(tree: ast.Ast) -> List[er.CompileError]:
    """
    Annotates scopes, declarations and identifiers:
    - Scopes are annotated with a dict for the named values they contain.
    - Declarations are annotated with their enclosing scope.
    - Identifiers are annotated with the declaration they reference.
    """
    errs: List[er.CompileError] = []

    def run_subpass(visitor: Union[NameTracker, ScopeTracker, NameResolver]) -> bool:
        tree.accept(visitor)
        errs.extend(visitor.errors.get())
        if any(error.severity == er.Severity.ERROR for error in visitor.errors.get()):
            return False
        return True

    if not run_subpass(NameTracker(tree)):
        return errs
    if not run_subpass(ScopeTracker(tree)):
        return errs
    run_subpass(NameResolver(tree))
    return errs


class ScopeVisitor(ast.DeepVisitor):
    """
    Ast visitor to keep track of the current scope.
    """

    def __init__(self, tree: ast.Ast):
        self._scopes: List[Union[ast.AstBlockStmt, ast.Ast]] = [tree]

    def _get_scope(self) -> Union[ast.AstBlockStmt, ast.Ast]:
        return self._scopes[-1]

    def _push_scope(self, node: ast.AstBlockStmt) -> None:
        self._scopes.append(node)

    def _pop_scope(self) -> None:
        self._scopes.pop()

    def block_stmt(self, node: ast.AstBlockStmt) -> None:
        self._push_scope(node)
        super().block_stmt(node)
        self._pop_scope()


class NameTracker(ScopeVisitor):
    """
    Ast visitor to annotate what names are in scope.
    """

    def __init__(self, tree: ast.Ast):
        super().__init__(tree)
        self.errors = er.ErrorTracker()

    def _set_name(self, name: str, node: ast.AstIdentRef) -> None:
        names = self._get_scope().names
        if name in names:
            self.errors.add(
                message=f"redefinition of name {name}",
                regions=[node.region, names[name].region],
            )
        names[name] = node

    def value_decl(self, node: ast.AstValueDecl) -> None:
        self._set_name(node.ident, node)

    def func_decl(self, node: ast.AstFuncDecl) -> None:
        self._set_name(node.ident, node)
        # Manually handle scopes so that the parameters are in the right scope
        self._push_scope(node.block)
        for param in node.params:
            self._set_name(param.param_name, param)
        for decl in node.block.decls:
            decl.accept(self)
        self._pop_scope()


class ScopeTracker(ScopeVisitor):
    """
    Ast visitor to annotate what scope declarations are in.
    """

    def __init__(self, tree: ast.Ast) -> None:
        super().__init__(tree)
        self.errors = er.ErrorTracker()

    def value_decl(self, node: ast.AstValueDecl) -> None:
        super().value_decl(node)
        node.scope = self._get_scope()

    def func_decl(self, node: ast.AstFuncDecl) -> None:
        super().func_decl(node)
        # The body isn't part of this scope
        node.block.scope = None
        node.scope = self._get_scope()

    def print_stmt(self, node: ast.AstPrintStmt) -> None:
        super().print_stmt(node)
        node.scope = self._get_scope()

    def block_stmt(self, node: ast.AstBlockStmt) -> None:
        super().block_stmt(node)
        node.scope = self._get_scope()

    def if_stmt(self, node: ast.AstIfStmt) -> None:
        super().if_stmt(node)
        # The blocks aren't part of this scope
        node.if_part[1].scope = None
        for _, block in node.elif_parts:
            block.scope = None
        if node.else_part:
            node.else_part.scope = None
        node.scope = self._get_scope()

    def while_stmt(self, node: ast.AstWhileStmt) -> None:
        super().while_stmt(node)
        # The block isn't part of this scope
        node.block.scope = None
        node.scope = self._get_scope()

    def return_stmt(self, node: ast.AstReturnStmt) -> None:
        super().return_stmt(node)
        node.scope = self._get_scope()

    def expr_stmt(self, node: ast.AstExprStmt) -> None:
        super().expr_stmt(node)
        node.scope = self._get_scope()


class NameResolver(ScopeVisitor):
    """
    Ast visitor to annotate what declarations identifiers reference.
    """

    def __init__(self, tree: ast.Ast) -> None:
        super().__init__(tree)
        self.errors = er.ErrorTracker()

    def _get_name(self, name: str) -> Optional[ast.AstIdentRef]:
        for scope in reversed(self._scopes):
            if name in scope.names:
                return scope.names[name]
        return None

    def _resolve_name(
        self, name: str, node: Union[ast.AstIdentExpr, ast.AstAtomType]
    ) -> None:
        ref = self._get_name(name)
        if ref is None:
            self.errors.add(
                message=f"reference to undeclared name {name}", regions=[node.region]
            )
        else:
            node.ref = ref

    def ident_expr(self, node: ast.AstIdentExpr) -> None:
        self._resolve_name(node.name, node)

    def atom_type(self, node: ast.AstAtomType) -> None:
        # TODO: Handle builtin types more cleanly
        if node.name not in ["void", "int", "str", "num", "bool"]:
            self._resolve_name(node.name, node)
